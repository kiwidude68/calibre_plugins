# Search The Internet Change Log

## [1.10.0] - 2022-10-16
_All kiwidude plugins updated/migrated to: https://github.com/kiwidude68/calibre_plugins_
### Added
- Add Help to menu.
- Add full translation support.
- Spanish translation (Darío Hereñú)
- Russian translation (Caarmi)
- Ukranian translation (@yurchor)
### Changed
- **Breaking:** Drop PyQt4 support, require calibre 2.x or later.
- Refactoring of common code
- Any custom website menu images must now be in /resources/images/Search The Internet/
- Removed help file, point to [GitHub Wiki](https://github.com/kiwidude68/calibre_plugins/wiki/Search-The-Internet)
### Fixed
- Deleting menu rows could have wrong selected items. (@capink)

## [1.9.0] - 2022-07-14
### Changed
- Changes for QT6 support in calibre (@Terisa de morgan)
 
## [1.8.1] - 2020-12-26
### Fixed
- Python 3 string related error when building post request. (@davidfor)
 
## [1.8.0] - 2020-09-02
### Added
- Enable translations. (@davidfor)
### Changed
- Use different formatter so templates can be used. This was specifically to allow use of identifiers.
- Changes for Python 3 support in calibre.
 
## [1.7.6] - 2016-03-09
### Fixed
- Missing ) in help formula
 
## [1.7.2] - 2014=07-11
### Changed
- QT5 support work

## [1.7.1] - 2011-09-24
### Changed
- When doing HTTP POST queries (like Fiction DB) do not encode the passed query values, just escape them instead.

## [1.7.0] - 2011-09-11
### Changed
- Switch the formatter used for resolving foreign names as the "new" SafeFormat is broken for this plugin's purposes.
- Support the centralised keyboard shortcut management in Calibre

## [1.6.6] - 2011-08-10
### Changed
- Change the location of SafeFormat class which was removed from Calibre for release 0.8.14

## [1.6.5] - 2011-05-08
### Changed
- Change webbrowser launching to use Calibre's wrapper for the default browser for better Linux support

## [1.6.4] - 2011-04-09
### Added
- Support skinning of icons by putting them in a plugin name subfolder of local resources/images

## [1.6.3] - 2011-04-05
### Fixed
- Ensure non-valid characters are removed when encoding

## [1.6.2] - 2011-04-04
### Changed
- Correct version number to reflect 1.6.1

## [1.6.1] - 2011-04-04
### Fixed
- Open group menu having incorrect icon_name argument

## [1.6.0] - 2011-04-03
### Changed
- Rewritten for new plugin infrastructure in Calibre 0.7.53

## [1.5.1] - 2011-01-28
### Changed
- Display clickable button on HTTP POST page if javascript disabled
### Fixed
- Swapping rows after addition of GET/POST column

## [1.5.0] - 2011-01-28
### Added
- Support HTTP POST websites like FictFact
- Use the Calibre template processor to support other metadata fields
- Archive import export use standard zip extension for ease of uploading to forums
### Fixed
- Ensure config window is parented to prevent multiple Calibre windows in taskbar

## [1.4.0] - 2011-01-24
### Added
- Add a configuration dialog to replace tweaks file
- Build in library of websites for users to choose from
### Changed
- Split into separate code files with proxy architecture
- Make menus dynamically recreated without restarts
- Ensure author always passed in FN LN format

## [1.3.0] - 2010-12-31
### Added
- Support Calibre 0.7.34 feature of plugin images retained within the zip file

## [1.2.0] - 2010-12-31
### Added
- Support for encoding for passing foreign language names to Amazon etc

## [1.1.0] - 2010-12-04
### Added
- Support for multiple row selections to launching multiple searches

## [1.0.0] - 2010-11-28
_Initial release of Search The Internet plugin_
