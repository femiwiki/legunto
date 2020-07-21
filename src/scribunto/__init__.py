import re
from typing import List


def search_dependencies(text: str, prefix=None) -> List[str]:
    regex = \
        r'''(?:require|mw\.loadData)\s*\(\s*['"](?:[Mm]odule|모듈):(.+)['"]\s*'''

    find = re.findall(regex, text)
    find = list(set(find))
    if prefix:
        find = [
            f"@{prefix}/{name}"
            for name in find
        ]

    return find


def rewrite_requires(text: str, prefix: str) -> str:
    # Module:foo/bar -> Module:foo-bar
    regex = \
        r'''(?:require|mw\.loadData)\s*\(\s*['"](?:[Mm]odule|모듈):.+['"]\s*'''

    module_names = re.findall(regex, text)
    for name in module_names:
        text = text.replace(name, name.replace("/", "-"))

    # Module:foo -> Module:@en/foo
    regex = (
        r"""((?:require|mw\.loadData)\s*\(\s*['"](?:[Mm]odule|모듈):)"""
        r"""(.+)(['"]\s*)"""
    )

    text = re.sub(regex, fr'\1@{prefix}/\2\3', text)

    return text


__all__ = [
    'search_dependencies',
    'rewrite_requires',
]
