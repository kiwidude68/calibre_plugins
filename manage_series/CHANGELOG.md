# Manage Series Change Log

## [1.5.3] - 2026-02-09
### Added
- Arabic translation
- 
## [1.5.2] - 2024-02-14
### Added
- Finnish translation
- Tamil translation
### Fixed
- Move rows up/down could error in certain circumstances.

## [1.5.1] - 2023-04-02
### Added
- Russian translation (ashed)
### Fixed
- Search websites context menu items were broken (@creeperwithrabies)

## [1.5.0] - 2022-10-16
_All kiwidude plugins updated/migrated to: https://github.com/kiwidude68/calibre_plugins_
### Added
- Add Help button to configuration and main dialog
- Add translation support.
- Spanish translation (dunhill)
- Ukranian translation (@yurchor)
### Changed
- **Breaking:** Drop PyQt4 support, require calibre 2.x or later.
- Refactoring of common code

## [1.4.0] - 2022-08-02
### Changed
- Use cal6 icon theme system to allow plugin icon customization

## [1.3.0] - 2022-01-22
### Changed
- Bump Minimum Calibre version to 2.85.1
- Changes for upcoming Qt6 Calibre

## [1.2.10] - 2020-09-27
### Changed
- More compatibility with Python 3

## [1.2.9] - 2020-01-16
### Changed
- Compatibility with Python 3

## [1.2.8] - 2013-07-24
### Changed
- Compatibility for the upcoming calibre 2.0

## [1.2.7] - 2013-05-04
### Fixed
- Issue introduced with changes to calibre in v0.9.29

## [1.2.6] - 2013-03-03
### Changed
- Prevent plugin being used in Device View or on Device View context menu
### Fixed
- Where trying to lock series index for a book without a series

## [1.2.5] - 2012-07-26
### Added
- Add a "Sort by Original Series Name" feature for users who are appending series together that overlap indexes
### Changed
- Rename "Sort by Original Series" to "Sort by Original Series Index"

## [1.2.4] - 2012-07-05
### Fixed
- For empty book where the pubdate column would error from a null date.

## [1.2.3] - 2012-06-23
### Changed
- Ensure lock series index maximum value is far higher.
- Ensure the lock series index text is all selected by default to allow overtyping when dialog displayed.

## [1.2.2] - 2012-06-04
### Added
- Put checkbox option on the Lock Index dialog when locking multiple series rows to allow setting all remaining to the specified index value
- Add a new context menu option of "Lock old series index" as a fast way to lock series index values to their old values for selected books
- Allow editing the pubdate column for books on this dialog.
### Fixed
- Where column headings for series columns were not correctly displayed on first opening dialog
- Where context menus not always updating until selection changed

## [1.2.1] - 2011-09-17
### Changed
- Only save series indexes for the last selected series column in the dialog
### Fixed
- If multi-select rows to assign an index, clicking Cancel will cancel asking for any further changes

## [1.2.0] - 2011-09-11
### Changed
- Upgrade to support the centralised keyboard shortcut management in Calibre

## [1.1.2] - 2011-05-08
### Changed
- Change webbrowser launching to use Calibre's wrapper for the default browser for better Linux support

## [1.1.1] - 2011-04-09
### Changed
- Support skinning of icons by putting them in a plugin name subfolder of local resources/images
- Ensure that encoding for launching website url ignores failures.

## [1.1.0] - 2011-04-03
### Changed
- Rewritten for new plugin infrastructure in Calibre 0.7.53
- Change to use OrderedDict from collections (deprecated code in Calibre)

## [1.0.0] - 2011-03-16
_Initial release of Manage Series plugin_
