# Open With Change Log

## [1.8.0] - 2022-09-XX
_All kiwidude plugins updated/migrated to: https://github.com/kiwidude68/calibre_plugins_
### Added
- Add translation support.
### Changed
**Breaking:** Drop PyQt4 support, require calibre 2.x or later.
- Refactoring of common code
- Any custom website menu images must now be in `/resources/images/Open With/`

## [1.7.2] - 2022-08-09
### Changed
- Update to calibre6 icon fetching. (@JimmXinu, @capink)

## [1.7.1] - 2022-06-29
### Fixed
- Export settings not working in PyQt6. (@capink)

## [1.7.0] - 2022-01-07
### Changed
- Changes for the upcoming PyQt6. (@capink)

## [1.5.13] - 2020-10-30
### Fixed
- Update for new calibre changes breaking the plugin for windows users. (@capink)

## [1.5.12] - 2020-02-01
### Fixed
- Remove menu rebuild when library changes. (@davidfor)

## [1.5.11] - 2020-01-23
### Changed
- Changes for Python 3 support in calibre. (@davidfor)

## [1.5.7] - 2013-04-15
### Added
- Add detached process flag for when launching on Windows.

## [1.5.6] - 2012-12-01
### Changed
- Prevent Open With being used in Device View or on Device View context menu
### Fixed
- When switching libraries, ensure keyboard shortcuts are reactivated

## [1.5.5] - 2012-10-01
### Fixed
- Put a special case in for loading Sigil, to workaround issues found with 0.5.9 release and conflicting C runtime paths

## [1.5.4] - 2012-08-14
### Added
- For Mac users support running shell scripts (contribution by Griker)

## [1.5.3] - 2012-07-20
- For Windows users use Win32 API rather than subprocess due to Python bug causing issues for users with non-ascii library paths

## [1.5.2] - 2012-01-28
### Added
- Support environment variables in paths to Unix applications
- Add an Edit... right-click for the path to an application to allow manual editing of the path.

## [1.5.1] - 2011-09-17
### Changed
- On Windows ensure the opened file is added to the MRU list, to support jump lists and recent documents

## [1.5.0] - 2011-09-11
### Changed
- Upgrade to support the centralised keyboard shortcut management in Calibre
### Fixed
- Bug in Import and Export menu items which were broken
- Bug of double click on the application path should not be allowed when no menu name

## [1.4.2] - 2011-08-31
### Fixed
- Change default path for Sigil for Linux users to use correct path separators
- Ensure `LD_LIBRARY_PATH` environment variable is cleared for Linux users to ensure no library conflict with Calibre

## [1.4.1] - 2011-04-09
### Added
- Support skinning of icons by putting them in a plugin name subfolder of local resources/images

## [1.4.0] - 2011-04-03
### Added
- Add Bliss application for Windows
### Changed
- Rewritten for new plugin infrastructure in Calibre 0.7.53

## [1.3.0] - 2011-01-29
### Added
- Support for OSX (Windows/Linux already available)
- Added more applications for Windows - Adobe Digital Editions, EPUBReader (Firefox plugin)
- Added default applications for OSX (Sigil, ADE, EPUBReader, Photoshop CS5, Pixelmator, Preview, Acrobat, Adobe Reader, Skim)
- Added default applications for Linux (Sigil, EPUBReader, Gimp)
### Changed
- Default applications list is now platform specific - don't display Windows applications to Linux/OSX users etc.
### Fixed
- For keyboard shortcuts not working if switch rows without reopening context menu

## [1.2.0] - 2011-01-25
### Added
- Include predefined application list
### Changed
- Rewrite with a configuration dialog to replace tweaks file

## [1.1.0] - 2011-01-23
### Added
- Renamed to 'Open with' plugin
- Add support for opening covers

## [1.0.0] - 2010-12-05
_Initial release as 'Open EPUB in editor' and 'Open format externally' plugins_
