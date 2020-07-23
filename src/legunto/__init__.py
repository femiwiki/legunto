from scribunto import search_dependencies, rewrite_requires, prepend_sources
from urllib.parse import urlparse
import json
import logging
import mwclient
import os
import pathlib
import sys
import typing


def print_help_massage() -> None:
    print("""
Usage:  legunto COMMAND

Commands:
  install     fetch lua modules based on 'scribunto.json'
  upgrade     upgrade dependencies of lua modules
""")


def get_interwiki_map() -> hash:
    site = mwclient.Site('meta.wikimedia.org')
    result = site.api('query', meta='siteinfo', siprop='interwikimap')
    result = result["query"]["interwikimap"]

    iw_map = {}
    for wiki in result:
        iw_map[wiki['prefix']] = wiki['url']

    return iw_map


def query_module_info(site: mwclient.Site, module: str) -> hash:
    title = module if module.startswith('Module:') else 'Module:' + module

    if not site.pages[title].exists:
        return None

    result = site.api('query', titles=title, prop='info', utf8="1")
    result = list(result['query']['pages'].values())[0]
    if 'pageid' not in result:
        logging.debug(result)

    return result


def fetch_module(
    url: str, module_name: str, site: mwclient.Site = None
) -> typing.Union[hash, None]:
    if not module_name.startswith('Module:'):
        module_name = 'Module:'+module_name

    url = urlparse(url)
    if not site:
        site = mwclient.Site(url.netloc, scheme=url.scheme)
    if not site.pages[module_name].exists:
        logging.warning(
            f'"{module_name}" does not exist on {url.netloc} ... Skip')
        return
    print(f'Fetching "{module_name}" from {url.netloc} ...', end='')

    info = query_module_info(site, module_name)
    module = {
        'pageid': info['pageid'],
        'revid': info['lastrevid'],
        'title': info['title'],
        'text': site.pages[module_name].text(),
    }
    print(' Done')

    return module


def to_filename(name: str) -> str:
    return name.split(':')[1] \
        .replace('/', '-')


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
    return getcwd()+"/scribunto.json"


def get_scribunto_lock_path() -> str:
    return getcwd()+"/scribunto.lock"


def parse_module_name(name: str, interwiki: hash) -> tuple:
    wiki, page = name.split("/", 1)
    if wiki[0] == "@":
        wiki = wiki[1:]

    if wiki not in interwiki:
        print(f"'{wiki}' is not a valid interwiki prefix")
        return None

    return wiki, page


def write_lua_file(wiki: str, title: str, text: str, wiki_url: str):
    path = os.getcwd()+"/lua/"+wiki
    if not os.path.exists(path):
        pathlib.Path(path).mkdir(parents=True)

    f = open(path+"/" + to_filename(title), "w")
    text = text
    text = rewrite_requires(text, prefix=wiki)
    text = prepend_sources(
        text,
        wiki_url.replace('$1', title))
    f.write(text)
    f.close()


def write_lock_file(lock: hash, path: str):
    print("Writing 'scribunto.lock' ...", end='')
    if not path:
        path = get_scribunto_lock_path()

    f = open(path, "w")
    f.write(json.dumps(lock, indent=2))
    f.close()
    print(' Done')


def install_dependencies() -> None:
    SCRIBUNTO_FILE_PATH = get_scribunto_file_path()

    exit_if_no_scribunto_file(SCRIBUNTO_FILE_PATH)

    LOCK_FILE_PATH = get_scribunto_lock_path()
    if os.path.exists(LOCK_FILE_PATH):
        print("'scribunto.lock' file already exists.")
        print("Trying to upgrade...")
        upgrade_dependencies(
            scribunto=SCRIBUNTO_FILE_PATH, lock=LOCK_FILE_PATH)
        return

    dependencies = json.loads(open(SCRIBUNTO_FILE_PATH, "r").read())[
        "dependencies"]
    interwiki = get_interwiki_map()

    lock = {
        'modules': {}
    }

    dps_to_add = dependencies

    print(
        len(dps_to_add) + ' ' +
        ('dependencies' if len(dps_to_add) > 1 else 'dependency') + ' found')

    while dps_to_add:
        dep = dps_to_add.pop()
        if dep in lock['modules']:
            continue

        wiki, page_name = parse_module_name(dep, interwiki)

        if not page_name:
            logging.warning(f"skip '{dep}'...")
            continue

        # TODO read lock file and compare revids to skip fetching

        module = fetch_module(interwiki[wiki], page_name)
        if not module:
            continue
        lock['modules'][dep] = {
            'pageid': module['pageid'],
            'revid': module['revid'],
            'title': module['title'],
        }
        indirect_dps = search_dependencies(module['text'], prefix=wiki)
        if indirect_dps:
            lock['modules'][dep]['dependencies'] = indirect_dps

        write_lua_file(
            wiki=wiki,
            title=module['title'],
            text=module['text'],
            wiki_url=interwiki[wiki]
        )

        dps_to_add += indirect_dps

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
    interwiki = get_interwiki_map()

    old_lock = json.loads(open(lock_path, "r").read())
    lock = {
        'modules': {}
    }

    dps_to_check = dependencies

    while dps_to_check:
        dep = dps_to_check.pop()
        if dep in lock['modules']:
            continue

        wiki, module_name = parse_module_name(dep, interwiki)

        if not module_name:
            logging.warning(f"skip '{dep}'...")
            continue

        url = urlparse(interwiki[wiki])
        site = mwclient.Site(url.netloc, scheme=url.scheme)
        info = query_module_info(site, module_name)

        if not info:
            logging.warning(
                f'"{module_name}" is not exist on {url.netloc} ... Skip')
            continue

        lock['modules'][dep] = {
            'pageid': info['pageid'],
            'revid': info['lastrevid'],
            'title': info['title'],
        }

        if dep in old_lock['modules'] and \
                old_lock['modules'][dep]['revid'] == info['lastrevid']:
            print(f'{dep} is already up-to-date')
            lock['modules'][dep] = old_lock['modules'][dep]
            if 'dependencies' in old_lock['modules'][dep]:
                dps_to_check += old_lock['modules'][dep]['dependencies']
            continue

        print(f'Fetching "{module_name}" from {url.netloc} ...', end='')
        page_name = 'Module:'+module_name
        page = site.pages[page_name]
        text = page.text()
        indirect_dps = search_dependencies(text, prefix=wiki)
        if indirect_dps:
            lock['modules'][dep]['dependencies'] = indirect_dps
        print(' Done')
        write_lua_file(
            wiki=wiki,
            title=page_name,
            text=text,
            wiki_url=interwiki[wiki]
        )

        dps_to_check += indirect_dps

        # TODO delete not required files anymore

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
