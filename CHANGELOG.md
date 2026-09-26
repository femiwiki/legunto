# Changelog

Versions and bullets are arranged chronologically from latest to oldest.

## [1.0.4](https://github.com/femiwiki/legunto/compare/v1.0.3...v1.0.4) (2026-09-26)


### Bug Fixes

* raise Python floor to 3.10 to close urllib3/requests/pytest CVEs ([#96](https://github.com/femiwiki/legunto/issues/96)) ([f4d6107](https://github.com/femiwiki/legunto/commit/f4d61079f85870a46b7f87dc4d6bd589d8818d7b))

## v1.0.3

- Sort entries in scribunto.lock alphabetically.

## v1.0.2

- Do not replace slash(`/`) in lua modules.

## v1.0.1

- Fix "TypeError: upgrade_dependencies() got an unexpected keyword argument"

## v1.0.0

- Percent encode page titles.
- Fix "TypeError: unsupported operand type(s) for +: 'int' and 'str'"

## v0.2.1

- Fix bad module name parsing

## v0.2.0

- Add a new command `upgrade`
- Fix bad handling of URL contains space on scribunto file.

## v0.1.1

- Handle non exist page exception

## v0.1.0

- Prepend original URLs to lua modules
