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
""")


def get_interwiki_map() -> hash:
    site = mwclient.Site('meta.wikimedia.org')
    result = site.api('query', meta='siteinfo', siprop='interwikimap')
    result = result["query"]["interwikimap"]

    iw_map = {}
    for wiki in result:
        iw_map[wiki['prefix']] = wiki['url']

    return iw_map


def fetch_module(url: str, module_name: str) -> typing.Union[hash, None]:
    if not module_name.startswith('Module:'):
        module_name = 'Module:'+module_name

    module = {}

    url = urlparse(url)
    site = mwclient.Site(url.netloc, scheme=url.scheme)
    if not site.pages[module_name].exists:
        logging.warning( \
            f'"{module_name}" is not exist on {url.netloc} ... Skip')
        return
    print(f'Fetching "{module_name}" from {url.netloc} ...', end='')

    result = site.api('query', titles=module_name, prop='info', utf8="1")
    result = list(result['query']['pages'].values())[0]
    module['pageid'] = result['pageid']
    module['revid'] = result['lastrevid']
    module['title'] = result['title']
    module['text'] = site.pages[module_name].text()
    print(' Done')

    return module


def to_filename(name: str) -> str:
    return name.split(':')[1] \
        .replace('/', '-')


def install_dependencies() -> None:
    SCRIBUNTO_FILE_PATH = os.getcwd()+"/scribunto.json"
    if not os.path.exists(SCRIBUNTO_FILE_PATH):
        logging.error("Can't find 'scribunto.json' file in this directory")

    dependencies = json.loads(open(SCRIBUNTO_FILE_PATH, "r").read())[
        "dependencies"]

    interwiki = get_interwiki_map()

    lock = {
        'modules': {}
    }

    deps_to_add = dependencies

    print(f'{len(deps_to_add)} dependency(s) found')

    while deps_to_add:
        dep = deps_to_add.pop()
        if dep in lock['modules']:
            continue

        wiki, page = dep.split("/", 1)
        if wiki[0] == "@":
            wiki = wiki[1:]

        if wiki not in interwiki:
            logging.warning(f"'{wiki}' is not a valid interwiki prefix")
            logging.warning(f"skip '{dep}'...")
            continue

        # TODO read lock file and compare revids to skip fetching

        module = fetch_module(interwiki[wiki], page)
        if not module:
            continue
        lock['modules'][dep] = {
            'pageid': module['pageid'],
            'revid': module['revid'],
            'title': module['title'],
        }
        indirect_deps = search_dependencies(module['text'], prefix=wiki)
        if indirect_deps:
            lock['modules'][dep]['dependencies'] = indirect_deps

        path = os.getcwd()+"/lua/"+wiki
        if not os.path.exists(path):
            pathlib.Path(path).mkdir(parents=True)

        f = open(path+"/" + to_filename(module['title']), "w")
        text = module['text']
        text = rewrite_requires(text, prefix=wiki)
        text = prepend_sources(
            text,
            interwiki[wiki].replace('$1', module['title']))
        f.write(text)
        f.close()

        deps_to_add += indirect_deps

    f = open(os.getcwd()+"/scribunto.lock", "w")
    f.write(json.dumps(lock, indent=2))
    f.close()


def console_main() -> None:
    if len(sys.argv) == 1 or \
            (len(sys.argv) == 2 and sys.argv[1] in ['--help', 'help']):
        print_help_massage()
        return
    elif len(sys.argv) == 2 and sys.argv[1] == 'install':
        install_dependencies()
    else:
        logging.error(
            f"legunto: '{sys.argv[1]}' is not a legunto command."
            "See 'legunto --help'")


__all__ = [
    "console_main"
]
