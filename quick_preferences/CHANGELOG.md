# Quick Preferences Change Log

## [1.7.1] - 2024-03-17
### Added
- Latvian translation
- Tamil translation
- Turkish translation

## [1.7.0] - 2022-10-16
_All kiwidude plugins updated/migrated to: https://github.com/kiwidude68/calibre_plugins_
### Added
- Help button to menu and configuration dialog.
- Ukranian translations (@yurchor)
### Changed
- **Breaking:** Drop PyQt4 support, require calibre 2.x or later.
- Refactoring of common code
### Fixed
- Deleting menu rows could have wrong selected items. (@capink)

## [1.6.1] - 2022-09-11
### Fixed
- Keyboard shortcuts dialog

## [1.6.0] - 2022-09-11
### Added
- Include Russian translations
### Fixed
- Qt incompatibility issues

## [1.5.1] - 2022-09-05
### Added
- Include Spanish translations (@dunhill)

## [1.5.0] - 2020-12-26
### Added
- Add function to change enabled Metadata download sources. (@davidfor)
- Make translatable. (@davidfor)

## [1.4.2] - 2020-11-28
### Changed
- Upgrade to Python 3 for calibre 5. (@davidfor)

## [1.4.0] - 2011-09-11
### Changed
- Upgrade to support the centralised keyboard shortcut management in calibre.

## [1.3.1] - 2011-04-09
### Added
- Support skinning of icons by putting them in a plugin name subfolder of local resources/images
### Fixed
- NoneType error when add new row, move it and not specifying a shortcut.

## [1.3.0] - 2011-04-08
### Added
- Rewrite config UI to support any number of regex file patterns, added via a grid.
- Optional pairing of author name swap parameter with a regex pattern

## [1.2.0] - 2011-04-03
### Added
- Add a Customize Plugin menu option
- Add submenu for quickly switching automerge type
### Changed
- Rename menu items and preferences to match new Automerge name
- Rewrite for new plugin infrastructure in calibre 0.7.53

## [1.1.0] - 2011-01-28
### Changed
- Improve tracking of when to rebuild menu actions
### Fixed
- Ensure keyboard shortcuts always hooked on startup

## [1.0.0] - 2011-01-02
_Initial release of Quick Preferences plugin_