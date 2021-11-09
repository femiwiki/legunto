import legunto
from collections import OrderedDict


def test_sort_lock_file() -> None:
    lock = {'modules': {
        '@en/Foo': {
            'dependencies': [
                'b', 'a', 'c'
            ]
        },
        '@en/Bar': {
            'dependencies': ['a']
        },
    }}

    sorted_lock = legunto.sort_lock_file(lock)
    assert type(sorted_lock['modules']) is OrderedDict
    assert sorted_lock['modules'].keys() == sorted(sorted_lock['modules'].keys())
    d = sorted_lock['modules']['@en/Foo']['dependencies']
    assert d == sorted(d)


def test_to_filename() -> None:
    assert legunto.to_filename('Module:foo') == \
        'foo'

    assert legunto.to_filename('Module:foo bar') == \
        'foo%20bar'

    assert legunto.to_filename('Module:foo/bar') == \
        'foo%2Fbar'

    assert legunto.to_filename('모듈:foo/bar') == \
        'foo%2Fbar'
