import json
import time

import mwclient
import pytest
import requests

import legunto


class FakeWiki:
    """Answers the api.php queries legunto sends, and records each request."""

    def __init__(self, pages: dict = None):
        # title -> (pageid, revid, content)
        self.pages = pages or {}
        self.requests = []
        # Responses to send before answering normally, as (status, headers, body).
        self.queued = []

    def __call__(self, session, method, url, params=None, data=None, headers=None, **kwargs):
        params = dict(params or data or {})
        self.requests.append({
            'method': method,
            'url': url,
            'params': params,
            'user_agent': session.headers.get('User-Agent'),
        })
        if self.queued:
            return response(*self.queued.pop(0))
        return response(200, {}, self.answer(params))

    def answer(self, params: dict) -> dict:
        if params.get('meta') == 'siteinfo':
            return {'query': {'interwikimap': [
                {'prefix': 'en', 'url': 'https://en.wikipedia.org/wiki/$1'},
                {'prefix': 'ko', 'url': 'https://ko.wikipedia.org/wiki/$1'},
            ]}}

        pages = []
        for title in params['titles'].split('|'):
            if title not in self.pages:
                pages.append({'title': title, 'missing': True})
                continue
            pageid, revid, content = self.pages[title]
            page = {'pageid': pageid, 'title': title}
            if params['prop'] == 'info':
                page['lastrevid'] = revid
            else:
                page['revisions'] = [{'revid': revid, 'slots': {'main': {'content': content}}}]
            pages.append(page)
        return {'query': {'pages': pages}}


def response(status: int, headers: dict, body: dict) -> requests.Response:
    r = requests.Response()
    r.status_code = status
    r.reason = {200: 'OK', 429: 'Too Many Requests'}.get(status, '')
    r.headers.update(headers)
    r.encoding = 'utf-8'
    r._content = json.dumps(body).encode()
    r.url = 'https://en.wikipedia.org/w/api.php'
    return r


@pytest.fixture
def wiki(monkeypatch) -> FakeWiki:
    fake = FakeWiki()
    monkeypatch.setattr(requests.Session, 'request', lambda session, *args, **kwargs: fake(session, *args, **kwargs))
    return fake


@pytest.fixture
def sleeps(monkeypatch) -> list:
    slept = []
    monkeypatch.setattr(time, 'sleep', slept.append)
    return slept


def test_user_agent(wiki: FakeWiki) -> None:
    site = legunto.connect('https://en.wikipedia.org/wiki/$1')
    legunto.query_pages(site, ['Module:A'], prop='info')

    assert len(wiki.requests) == 1
    user_agent = wiki.requests[0]['user_agent']
    assert user_agent.startswith(f'legunto/{legunto.VERSION} (https://github.com/femiwiki/legunto; ')
    assert '@femiwiki.com)' in user_agent


def test_query_sends_maxlag_by_get(wiki: FakeWiki) -> None:
    site = legunto.connect('https://en.wikipedia.org/wiki/$1')
    legunto.query_pages(site, ['Module:A'], prop='info')

    assert wiki.requests[0]['method'] == 'GET'
    assert wiki.requests[0]['params']['maxlag'] == legunto.MAX_LAG


def test_query_pages_batches_titles(wiki: FakeWiki) -> None:
    wiki.pages = {f'Module:{i}': (i, 100 + i, '') for i in range(120)}
    site = legunto.connect('https://en.wikipedia.org/wiki/$1')

    found = legunto.query_pages(site, [f'Module:{i}' for i in range(120)] + ['Module:Missing'], prop='info')

    assert [len(r['params']['titles'].split('|')) for r in wiki.requests] == [50, 50, 21]
    assert len(found) == 120
    assert found['Module:7']['lastrevid'] == 107
    assert 'Module:Missing' not in found


def test_query_pages_follows_normalization_and_continuation(wiki: FakeWiki) -> None:
    site = legunto.connect('https://en.wikipedia.org/wiki/$1')
    wiki.queued = [
        (200, {}, {
            'continue': {'rvcontinue': '2', 'continue': '||'},
            'query': {
                'normalized': [{'from': 'Module:a', 'to': 'Module:A'}],
                'pages': [
                    {'pageid': 1, 'title': 'Module:A', 'revisions': [{'revid': 11, 'slots': {'main': {'content': 'a'}}}]},
                    {'pageid': 2, 'title': 'Module:B'},
                ],
            },
        }),
        (200, {}, {
            'query': {
                'normalized': [{'from': 'Module:a', 'to': 'Module:A'}],
                'pages': [
                    {'pageid': 1, 'title': 'Module:A'},
                    {'pageid': 2, 'title': 'Module:B', 'revisions': [{'revid': 22, 'slots': {'main': {'content': 'b'}}}]},
                ],
            },
        }),
    ]

    found = legunto.query_pages(site, ['Module:a', 'Module:B'], prop='revisions', rvprop='ids|content')

    assert len(wiki.requests) == 2
    assert wiki.requests[1]['params']['rvcontinue'] == '2'
    assert found['Module:a']['revisions'][0]['revid'] == 11
    assert found['Module:B']['revisions'][0]['revid'] == 22


def test_429_is_retried_after_retry_after(wiki: FakeWiki, sleeps: list) -> None:
    wiki.pages = {'Module:A': (1, 11, '')}
    wiki.queued = [(429, {'Retry-After': '7'}, {})]
    site = legunto.connect('https://en.wikipedia.org/wiki/$1')

    found = legunto.query_pages(site, ['Module:A'], prop='info')

    assert sleeps == [7]
    assert len(wiki.requests) == 2
    assert found['Module:A']['lastrevid'] == 11


def test_429_backs_off_then_gives_up(wiki: FakeWiki, sleeps: list) -> None:
    wiki.queued = [(429, {}, {})] * (legunto.MAX_RETRIES + 1)
    site = legunto.connect('https://en.wikipedia.org/wiki/$1')

    with pytest.raises(requests.HTTPError):
        legunto.query_pages(site, ['Module:A'], prop='info')

    assert sleeps == [5, 10, 20, 40, 80]
    assert len(wiki.requests) == legunto.MAX_RETRIES + 1


def test_maxlag_is_retried_after_retry_after(wiki: FakeWiki, sleeps: list) -> None:
    wiki.pages = {'Module:A': (1, 11, '')}
    wiki.queued = [(200, {'X-Database-Lag': '8', 'Retry-After': '8'}, {
        'error': {'code': 'maxlag', 'info': 'Waiting for a database server: 8 seconds lagged.'},
    })]
    site = legunto.connect('https://en.wikipedia.org/wiki/$1')

    found = legunto.query_pages(site, ['Module:A'], prop='info')

    assert sleeps == [8]
    assert found['Module:A']['lastrevid'] == 11


def test_api_error_is_raised(wiki: FakeWiki) -> None:
    wiki.queued = [(200, {}, {'error': {'code': 'badvalue', 'info': 'Bad value.'}})]
    site = legunto.connect('https://en.wikipedia.org/wiki/$1')

    with pytest.raises(mwclient.errors.APIError):
        legunto.query_pages(site, ['Module:A'], prop='info')


def test_resolve_dependencies_batches_each_level(wiki: FakeWiki, tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    wiki.pages = {
        'Module:Top': (1, 11, "local a = require('Module:Mid1')\nlocal b = require('Module:Mid2')"),
        'Module:Mid1': (2, 22, "return require('Module:Leaf')"),
        'Module:Mid2': (3, 33, "return require('Module:Leaf')"),
        'Module:Leaf': (4, 44, 'return {}'),
        'Module:Other': (5, 55, 'return {}'),
    }
    interwiki = {'en': 'https://en.wikipedia.org/wiki/$1'}
    old_lock = {'modules': {
        # Unchanged: its dependencies come from the old lock, its text is not fetched.
        '@en/Mid2': {'pageid': 3, 'revid': 33, 'title': 'Module:Mid2', 'dependencies': ['@en/Leaf']},
        # Changed: fetched again.
        '@en/Leaf': {'pageid': 4, 'revid': 40, 'title': 'Module:Leaf'},
    }}

    lock = legunto.resolve_dependencies(['@en/Top', '@en/Other', '@en/Gone', '@xx/Bad'], old_lock, interwiki)

    assert [(r['params']['prop'], r['params']['titles']) for r in wiki.requests] == [
        ('info', 'Module:Gone|Module:Other|Module:Top'),
        ('revisions', 'Module:Other|Module:Top'),
        ('info', 'Module:Mid1|Module:Mid2'),
        ('revisions', 'Module:Mid1'),
        ('info', 'Module:Leaf'),
        ('revisions', 'Module:Leaf'),
    ]
    assert sorted(lock['modules']) == ['@en/Leaf', '@en/Mid1', '@en/Mid2', '@en/Other', '@en/Top']
    assert lock['modules']['@en/Mid2'] == old_lock['modules']['@en/Mid2']
    assert lock['modules']['@en/Leaf'] == {'pageid': 4, 'revid': 44, 'title': 'Module:Leaf'}
    assert sorted(lock['modules']['@en/Top']['dependencies']) == ['@en/Mid1', '@en/Mid2']
    assert (tmp_path / 'lua/en/Mid1').read_text().endswith("return require('Module:@en/Leaf')")
    assert not (tmp_path / 'lua/en/Mid2').exists()
