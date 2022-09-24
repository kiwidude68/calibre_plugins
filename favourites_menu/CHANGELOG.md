# Favourites Menu Change Log

## [1.3.0] - 2022-09-XX
_All kiwidude plugins updated/migrated to: https://github.com/kiwidude68/calibre_plugins_
### Changed
- **Breaking:** Drop PyQt4 support, require calibre 2.x or later.
- Refactoring of common code

## [1.2.0] - 2022-08-02
### Changed
- Use cal6 icon theme system to allow plugin icon customization

## [1.1.0] - 2022-01-20
### Changed
- Bump Minimum Calibre version to 2.85.1
- Changes for upcoming Qt6 Calibre
### Fixed
- Icon scaling in FM config

## [1.0.5] - 2020-01-16
### Changed
- Compatibility with Python 3

## [1.0.4] - 2014-07-24
### Changed
- Compatibility for upcoming calibre 2.0

## [1.0.3] - 2012-11-05
### Changed
- Ensure submenus for plugins can have their states updated by emitting the aboutToShow signal for every plugin that has an associated .menu set for it

## [1.0.2] - 2012-07-30
### Changed
- Support dynamically named menu names if they have a .favourites_menu_unique_name attribute

## [1.0.1] - 2012-06-30
### Changed
- Add a hack to allow menu items from the Reading List plugin that have counts in them still be used in this plugin (without the counts)

## [1.0.0] - 2012-06-27
_Initial release of the Favourites Menu plugin_
