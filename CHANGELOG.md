# Changelog

Versions and bullets are arranged chronologically from latest to oldest.

## [1.0.5](https://github.com/femiwiki/legunto/compare/v1.0.4...v1.0.5) (2026-10-17)


### Bug Fixes

* omit self references from module dependencies ([#130](https://github.com/femiwiki/legunto/issues/130)) ([44b34e6](https://github.com/femiwiki/legunto/commit/44b34e66ebade928ce823b61e0b8fe5c6882cb4c))


### Documentation

* fix install command in README ([#131](https://github.com/femiwiki/legunto/issues/131)) ([31f47cf](https://github.com/femiwiki/legunto/commit/31f47cf263600c355f13e7abffa9a565ca646a13))

## [1.0.4](https://github.com/femiwiki/legunto/compare/v1.0.3...v1.0.4) (2026-10-04)


### Bug Fixes

* raise Python floor to 3.10 to close urllib3/requests/pytest CVEs ([#96](https://github.com/femiwiki/legunto/issues/96)) ([f4d6107](https://github.com/femiwiki/legunto/commit/f4d61079f85870a46b7f87dc4d6bd589d8818d7b))
* update with 15 requests instead of 205, named and retrying 429 ([#118](https://github.com/femiwiki/legunto/issues/118)) ([61f0be2](https://github.com/femiwiki/legunto/commit/61f0be2f1a71f5aef30e09addad1e1f09762aca3))

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
