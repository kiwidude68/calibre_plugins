# Walk Search History Change Log

## [1.5.0] - 2022-10-XX
_All kiwidude plugins updated/migrated to: https://github.com/kiwidude68/calibre_plugins_
### Added
- Add Help to menu and configuration dialog.
- Translations for Spanish, French, Russian, Ukranian - thanks to all!
### Changed
- **Breaking:** Drop PyQt4 support, require calibre 2.x or later.
- Refactoring of common code

## [1.4.0] - 2022-09-09
### Added
- Add option to keep a separate history per library. Not retained when calibre is closed.
- Add translation support.
### Fixed
- Tag browser searches not showing in menu history list after it has been cleared.
- Keyboard shortcuts stop working after plugin menu gets rebuilt.

## [1.3.2] - 2020-01-17
### Changed
- Changes for Python 3 support in calibre.

## [1.3.0] - 2011-09-11
### Changed
- Support the centralised keyboard shortcut management in Calibre

## [1.2.2] - 2011-05-20
### Changed
- Support refactoring by Kovid of gui.tool_bar to gui.bars_manager in Calibre 0.8.2
### Fixed
- Config screen getting wrong preferences

## [1.2.1] - 2011-04-09
### Added
- Support skinning of icons by putting them in a plugin name subfolder of local resources/images

## [1.2.0] - 2011-04-03
### Changed
- Rewritten for new plugin infrastructure in Calibre 0.7.53

## [1.1.0] - 2011-01-31
### Added
- Search history displayed in the toolbar dropdown menu
- Ability to clear the search history in the dropdown
- Additional customisation options in the configure dialog
### Changed
- Rewritten to maintain search histories independent of that displayed in the search dropdown.
- Can now go forward/backward to "empty" searches in the history

## [1.0.0] - 2010-12-31

_First release of Walk Search History plugin._
