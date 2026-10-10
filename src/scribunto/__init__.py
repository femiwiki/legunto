import re


def search_dependencies(text: str, prefix=None) -> list[str]:
    regex = r'''(?:require|mw\.loadData)\s*\(\s*['"](?:[Mm]odule|모듈):([^'"]+)['"]'''

    find = re.findall(regex, text)
    find = list(set(find))
    if prefix:
        find = [
            f"@{prefix}/{name}"
            for name in find
        ]

    return find


def rewrite_requires(text: str, prefix: str) -> str:
    # Module:foo -> Module:@en/foo
    regex = r"""((?:require|mw\.loadData)\s*\(\s*['"](?:[Mm]odule|모듈):)([^'"]+)(['"])"""

    text = re.sub(regex, fr'\1@{prefix}/\2\3', text)

    return text


def prepend_sources(text: str, url: str) -> str:
    text = f'''--[[
This module was originally on {url} and forked by Legunto
(https://github.com/femiwiki/legunto).
]]
''' + text

    return text


__all__ = [
    'prepend_sources',
    'rewrite_requires',
    'search_dependencies',
]
