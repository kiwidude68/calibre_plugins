# View Manager Change Log

## [1.10.0] - 2022-10-16
_All kiwidude plugins updated/migrated to: https://github.com/kiwidude68/calibre_plugins_
### Added
- Add Help button to menu and configuration dialog.
- Add translation support.
- French translation (lentrad)
- Polish translation (moje konto)
- Russian translation (Caarmi)
- Spanish translation (dunhill)
- Ukranian translation (@yurchor)
### Changed
- Support qt.core import syntax for future Qt compatibility
- Refactoring of common code

## [1.9.0] - 2022-08-02
### Changed
- Use cal6 icon theme system to allow plugin icon customization

## [1.8.0] - 2021-03-23
### Added
- Add Previous View action.
### Changed
- Performance tweak, apply_state(save_state=False)

## [1.7.0] - 2021-01-19
### Changed
- Changes for upcoming Qt6 Calibre

## [1.6.0] - 2020-11-04
### Added
- Add 'Re-Apply Current View' action. Only available when a view has been previously applied.
### Changed
- Change how saved searches are retrieved to newer API.
- Apply persist_shortcut to view actions when Calibre >= v5.4 so view shortcuts aren't discarded as easily. Calibre PR #1246

## [1.5.6] - 2020-06-15
### Added
- Add 'Next View' feature

## [1.5.5] - 2020-03-07
### Fixed
- Allow for a View named empty string.

## [1.5.4] - 2020-01-16
### Changed
- Compatibility with Python 3

## [1.4.3] - 2017-06-24
### Changed
- Disambiguation of settings.

## [1.3.2] - 2014-11-22
### Fixed
- Keyboard shortcuts not working on calibre >= 2.10

## [1.3.1] - 2014-07-24
### Added
- Create new Views and update Views with current columns, column widths and sorts.
- Can switch Virtual libraries on View activation.
### Changed
- Compatibility for upcoming calibre 2.0
- Make settings for Virtual library, Saved search and VL additional restriction search clearer.

## [1.3.0] - 2012-06-22
### Added
- Store views in the calibre database rather than a json file, to allow reuse from different computers (not simultaneously!)
- Add a support option to the "Other" tab allowing viewing the plugin data stored in the database
### Changed
- Now requires calibre 0.8.57
- No longer support upgrading from plugin versions older than 1.2.0

## [1.2.1] - 2011-09-11
### Fixed
- When switching libraries, ensure no issues with old menu items causing a crash

## [1.2.0] - 2011-09-11
### Changed
- Support the centralised keyboard shortcut management in Calibre
- When opening the configuration dialog, default to the last selected view

## [1.1.2] - 2011-07-16
### Fixed
- Config error introduced with 1.1.1

## [1.1.1] - 2011-07-16
### Fixed
- Error issue for first time users

## [1.1.0] - 2011-07-11
### Added
- Add ability to store column widths as part of the view information

## [1.0.6] - 2011-06-15
### Added
- Indicate the last selected view with a checkbox in the menu

## [1.0.5] - 2011-04-23
### Added
- Enhance configuration options to allow specifying a view to apply at startup
### Changed
- Ensure any auto applying of views is a per library setting
### Fixed
- Not always remembering the last applied view when restarting/switching libraries

## [1.0.4] - 2011-04-14
### Fixed
- Applying a blank saved search not working

## [1.0.3] - 2011-04-12
### Changed
- Add text to config dialog advising of behaviour if enable automatic apply view
### Fixed
- Plugin not working for first time users

## [1.0.2] - 2011-04-11
### Added
- Offer configuration option to apply last selected view at startup or switching libraries
### Changed
- Change configuration file format to offer more flexibility

## [1.0.1] - 2011-04-10
### Fixed
- key error when creating new views

## [1.0.0] - 2011-04-10
_Initial release of View Manager plugin._
