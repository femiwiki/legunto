from scribunto import search_dependencies, rewrite_requires, prepend_sources
from urllib.parse import urlparse, quote
from collections import OrderedDict
from importlib.metadata import PackageNotFoundError, version
import json
import logging
import mwclient
import os
import pathlib
import sys

try:
    VERSION = version('legunto')
except PackageNotFoundError:
    VERSION = 'unknown'

# https://foundation.wikimedia.org/wiki/Policy:Wikimedia_Foundation_User-Agent_Policy
USER_AGENT = f'legunto/{VERSION} (https://github.com/femiwiki/legunto; admin@femiwiki.com)'

# The most titles a query takes from a client without apihighlimits.
BATCH_SIZE = 50


def print_help_massage() -> None:
    print("""
Usage:  legunto COMMAND

Commands:
  install     fetch lua modules based on 'scribunto.json'
  upgrade     upgrade dependencies of lua modules
""")


def connect(url: str) -> mwclient.Site:
    url = urlparse(url)
    return mwclient.Site(url.netloc, scheme=url.scheme, clients_useragent=USER_AGENT, do_init=False)


def query(site: mwclient.Site, **params) -> hash:
    result = site.raw_api('query', http_method='GET', formatversion=2, **params)
    if 'error' in result:
        raise mwclient.errors.APIError(result['error'].get('code'), result['error'].get('info'), params)
    return result


def query_pages(site: mwclient.Site, titles: list, **params) -> hash:
    """Query titles BATCH_SIZE at a time, following continuation.

    Returns a page for each title that exists, keyed by the title as given.
    """
    found = {}
    for i in range(0, len(titles), BATCH_SIZE):
        batch = titles[i:i + BATCH_SIZE]
        batch_params = dict(params, titles='|'.join(batch))
        normalized = {}
        pages = {}
        while True:
            result = query(site, **batch_params)
            for n in result['query'].get('normalized', []):
                normalized[n['from']] = n['to']
            for page in result['query'].get('pages', []):
                pages.setdefault(page['title'], {}).update(page)
            if 'continue' not in result:
                break
            batch_params.update(result['continue'])

        for title in batch:
            page = pages.get(normalized.get(title, title))
            if page and 'missing' not in page and 'invalid' not in page:
                found[title] = page
    return found


def get_interwiki_map() -> hash:
    site = connect('https://meta.wikimedia.org')
    result = query(site, meta='siteinfo', siprop='interwikimap')
    result = result["query"]["interwikimap"]

    iw_map = {}
    for wiki in result:
        iw_map[wiki['prefix']] = wiki['url']

    return iw_map


def to_filename(name: str) -> str:
    name = name.split(':')[1]
    # Percent encoding
    # https://github.com/femiwiki/remote-gadgets/issues/46
    name = quote(name, safe='')
    # Avoid extension confusion
    name = name.replace('.', '%2E')
    return name


def exit_if_no_scribunto_file(path: str = None) -> None:
    if not path:
        path = get_scribunto_file_path()

    if not os.path.exists(path):
        logging.error("Can't find 'scribunto.json' file in this directory.")
        exit(1)


def getcwd() -> str:
    # TODO Use argv when passed
    return os.getcwd()


def get_scribunto_file_path() -> str:
    return getcwd() + "/scribunto.json"


def get_scribunto_lock_path() -> str:
    return getcwd() + "/scribunto.lock"


def parse_module_name(name: str, interwiki: hash) -> tuple:
    wiki, page = name.split("/", 1)
    if wiki[0] == "@":
        wiki = wiki[1:]

    if wiki not in interwiki:
        print(f"'{wiki}' is not a valid interwiki prefix")
        return None

    return wiki, page


def write_lua_file(wiki: str, title: str, text: str, wiki_url: str):
    path = os.getcwd() + "/lua/" + wiki
    if not os.path.exists(path):
        pathlib.Path(path).mkdir(parents=True)

    f = open(path + "/" + to_filename(title), "w")
    text = text
    text = rewrite_requires(text, prefix=wiki)
    text = prepend_sources(
        text,
        wiki_url.replace('$1', title.replace(' ', '_')))
    f.write(text)
    f.close()


def sort_lock_file(lock: hash) -> hash:
    for module in lock['modules']:
        if "dependencies" in lock['modules'][module]:
            lock['modules'][module]['dependencies'].sort()

    lock['modules'] = OrderedDict(sorted(lock['modules'].items()))
    return lock


def write_lock_file(lock: hash, path: str):
    lock = sort_lock_file(lock)

    print("Writing 'scribunto.lock' ...", end='')
    if not path:
        path = get_scribunto_lock_path()

    f = open(path, "w")
    f.write(json.dumps(lock, indent=2))
    f.close()
    print(' Done')


def to_title(module_name: str) -> str:
    return module_name if module_name.startswith('Module:') else 'Module:' + module_name


def resolve_dependencies(dependencies: list, old_lock: hash, interwiki: hash) -> hash:
    lock = {
        'modules': {}
    }

    sites = {}
    seen = set()
    dps_to_check = list(dependencies)

    # Walk the dependency tree one level at a time, so that every module of a
    # level on the same wiki is looked up in one batch.
    while dps_to_check:
        level = {}
        for dep in dps_to_check:
            if dep in seen:
                continue
            seen.add(dep)
            parsed = parse_module_name(dep, interwiki)
            if not parsed:
                logging.warning(f"skip '{dep}'...")
                continue
            level[dep] = parsed
        dps_to_check = []

        by_host = {}
        for dep, (wiki, module_name) in level.items():
            by_host.setdefault(urlparse(interwiki[wiki]).netloc, []).append(dep)

        for host, deps in by_host.items():
            if host not in sites:
                sites[host] = connect(interwiki[level[deps[0]][0]])
            site = sites[host]

            titles = {dep: to_title(level[dep][1]) for dep in deps}
            infos = query_pages(site, sorted(set(titles.values())), prop='info')

            changed = []
            for dep in deps:
                info = infos.get(titles[dep])
                if not info:
                    logging.warning(
                        f'"{level[dep][1]}" is not exist on {host} ... Skip')
                    continue

                old = old_lock['modules'].get(dep)
                if old and old['revid'] == info['lastrevid']:
                    print(f'{dep} is already up-to-date')
                    lock['modules'][dep] = old
                    dps_to_check += old.get('dependencies', [])
                    continue

                lock['modules'][dep] = {
                    'pageid': info['pageid'],
                    'revid': info['lastrevid'],
                    'title': info['title'],
                }
                changed.append(dep)

            if not changed:
                continue

            revisions = query_pages(
                site, sorted({titles[dep] for dep in changed}),
                prop='revisions', rvprop='ids|content', rvslots='main')

            for dep in changed:
                wiki, module_name = level[dep]
                if titles[dep] not in revisions:
                    logging.warning(
                        f'"{module_name}" is not exist on {host} ... Skip')
                    del lock['modules'][dep]
                    continue
                print(f'Fetching "{module_name}" from {host} ...', end='')
                revision = revisions[titles[dep]]['revisions'][0]
                # The page may have been edited since the info lookup.
                lock['modules'][dep]['revid'] = revision['revid']
                text = revision['slots']['main']['content']
                indirect_dps = search_dependencies(text, prefix=wiki)
                if indirect_dps:
                    lock['modules'][dep]['dependencies'] = indirect_dps
                print(' Done')
                write_lua_file(
                    wiki=wiki,
                    title=titles[dep],
                    text=text,
                    wiki_url=interwiki[wiki]
                )

                dps_to_check += indirect_dps

        # TODO delete not required files anymore

    return lock


def install_dependencies() -> None:
    SCRIBUNTO_FILE_PATH = get_scribunto_file_path()

    exit_if_no_scribunto_file(SCRIBUNTO_FILE_PATH)

    LOCK_FILE_PATH = get_scribunto_lock_path()
    if os.path.exists(LOCK_FILE_PATH):
        print("'scribunto.lock' file already exists.")
        print("Trying to upgrade...")
        upgrade_dependencies(
            scribunto_path=SCRIBUNTO_FILE_PATH, lock_path=LOCK_FILE_PATH)
        return

    dependencies = json.loads(open(SCRIBUNTO_FILE_PATH, "r").read())[
        "dependencies"]

    print(
        str(len(dependencies)) + ' ' + ('dependencies' if len(dependencies) > 1 else 'dependency') + ' found')

    lock = resolve_dependencies(dependencies, {'modules': {}}, get_interwiki_map())
    write_lock_file(lock, LOCK_FILE_PATH)


def upgrade_dependencies(
    scribunto_path: str = None,
    lock_path: str = None
) -> None:
    if not scribunto_path:
        scribunto_path = get_scribunto_file_path()

    exit_if_no_scribunto_file(scribunto_path)

    if not lock_path:
        lock_path = get_scribunto_lock_path()

    dependencies = json.loads(open(scribunto_path, "r").read())[
        "dependencies"]
    old_lock = json.loads(open(lock_path, "r").read())

    lock = resolve_dependencies(dependencies, old_lock, get_interwiki_map())
    write_lock_file(lock, lock_path)


def console_main() -> None:
    if len(sys.argv) == 1 or \
            (len(sys.argv) == 2 and sys.argv[1] in ['--help', 'help']):
        print_help_massage()
        return
    elif len(sys.argv) == 2 and sys.argv[1] == 'install':
        install_dependencies()
    elif len(sys.argv) == 2 and sys.argv[1] in ['upgrade', 'update']:
        upgrade_dependencies()
    else:
        logging.error(
            f"legunto: '{sys.argv[1]}' is not a legunto command."
            "See 'legunto --help'")


__all__ = [
    "console_main"
]
