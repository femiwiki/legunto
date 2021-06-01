# legunto [![Github checks status]][github checks link] [![codecov.io status]][codecov.io link]

Fetch MediaWiki [Scribunto] modules from wikis and save as files

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

[github checks status]: https://badgen.net/github/checks/femiwiki/legunto/main
[github checks link]: https://github.com/femiwiki/legunto/actions
[codecov.io status]: https://badgen.net/codecov/c/github/femiwiki/legunto
[codecov.io link]: https://codecov.io/gh/femiwiki/legunto
[scribunto]: https://www.mediawiki.org/wiki/Special:MyLanguage/Extension:Scribunto
[python]: https://www.python.org/
[pip]: https://pip.pypa.io/en/stable/
[releases]: https://github.com/femiwiki/legunto/releases
