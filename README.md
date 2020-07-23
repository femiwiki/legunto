# legunto

Fetch MediaWiki [Scribunto] modules from wikis and save as files

> **Limitations:**
> Wiki pages can have a slash(`/`) in their name, but filenames in unix can't. Slashes is converted to hyphens(`-`) on saving.

## Install

Requirements:

- [Python] 3
- [pip]

1. Download a wheel file from [Releases].
2. Execute `pip install legunto-*.whl`.

## Build

```sh
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
python setup.py bdist_wheel
```

[scribunto]: https://www.mediawiki.org/wiki/Special:MyLanguage/Extension:Scribunto
[python]: https://www.python.org/
[pip]: https://pip.pypa.io/en/stable/
[releases]: https://github.com/femiwiki/legunto/releases
