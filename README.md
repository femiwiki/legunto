# legunto

[![Github checks status]][github checks link]
[![codecov.io status]][codecov.io link]

Fetch MediaWiki [Scribunto] modules from wikis and save as files

## Install

Requirements:

- [Python] 3
- [pip]

1. Download a wheel file from [Releases].
2. Execute `pip install legunto-*.whl`.

## Usage

```sh
# Print help message
python -m legunto

# Prepare scribunto.json
touch scribunto.json
vim scribunto.json

# Fetch lua modules based on the scribunto.json
python -m legunto install
```

Each dependency names a wiki by its prefix in the [interwiki map] of Meta-Wiki,
such as `@en/Arguments` for `Module:Arguments` on English Wikipedia. For a wiki
missing from the map, give its article URL and api.php URL under `wikis`:

```json
{
  "wikis": {
    "dev": {
      "url": "https://dev.fandom.com/wiki/$1",
      "api": "https://dev.fandom.com/api.php"
    }
  },
  "dependencies": ["@dev/Arguments"]
}
```

A prefix under `wikis` overrides the same prefix in the interwiki map.

## Build

```sh
uv sync
uv build
```

[github checks status]: https://badgen.net/github/checks/femiwiki/legunto/main
[github checks link]: https://github.com/femiwiki/legunto/actions
[codecov.io status]: https://badgen.net/codecov/c/github/femiwiki/legunto
[codecov.io link]: https://codecov.io/gh/femiwiki/legunto
[scribunto]: https://www.mediawiki.org/wiki/Special:MyLanguage/Extension:Scribunto
[python]: https://www.python.org/
[pip]: https://pip.pypa.io/en/stable/
[releases]: https://github.com/femiwiki/legunto/releases
[interwiki map]: https://meta.wikimedia.org/wiki/Interwiki_map
