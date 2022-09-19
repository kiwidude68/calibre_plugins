## Release History

**Version 1.8.0** - XX Sep 2022
- New: All kiwidude plugins updated/migrated to: https://github.com/kiwidude68/calibre_plugins
- New: Add translation support.
- Update: Drop PyQt4 support, require calibre 2.x or later.
- Update: Refactoring of common code
- Update: Any custom website menu images must now be in /resources/images/Open With/

**Version 1.7.2** - 9 Aug 2022 - made by capink
- Update: update to calibre6 icon fetching. Code from @JimmXinu.

**Version 1.7.1** - 29 Jun 2022 - made by capink
- Fix: Export settings not working in PyQt6.

**Version 1.7.0** - 7 Jan 2022 - made by capink
- Update: Changes for the upcoming PyQt6.

**Version 1.5.13** - 30 Oct 2020 - made by capink
- Fix: Update for new calibre changes breaking the plugin for windows users.

**Version 1.5.12** - 01 Feb 2020 - made by davidfor
- Fix: Remove menu rebuild when library changes.

**Version 1.5.11** - 23 Jan 2020 - made by davidfor
- Update: Changes for Python 3 support in calibre.

**Version 1.5.7** - 15 Apr 2013
- New: Add detached process flag for when launching on Windows.

**Version 1.5.6** - 01 Dec 2012
- Update: Prevent Open With being used in Device View or on Device View context menu
- Fix: When switching libraries, ensure keyboard shortcuts are reactivated

**Version 1.5.5** - 01 Oct 2012
- Fix: Put a special case in for loading Sigil, to workaround issues found with 0.5.9 release and conflicting C runtime paths

**Version 1.5.4** - 14 Aug 2012
- New: For Mac users support running shell scripts (contribution by Griker)

**Version 1.5.3** - 20 Jul 2012
- Update: For Windows users use Win32 API rather than subprocess due to Python bug causing issues for users with non-ascii library paths

**Version 1.5.2** - 28 Jan 2012
- New: Support environment variables in paths to Unix applications
- New: Add an Edit... right-click for the path to an application to allow manual editing of the path.

**Version 1.5.1** - 17 Sep 2011
- Update: On Windows ensure the opened file is added to the MRU list, to support jump lists and recent documents

**Version 1.5.0** - 11 Sep 2011
- Update: Upgrade to support the centralised keyboard shortcut management in Calibre
- Fix: Bug in Import and Export menu items which were broken
- Fix: Bug of double click on the application path should not be allowed when no menu name

**Version 1.4.2** - 31 Aug 2011
- Fix: Change default path for Sigil for Linux users to use correct path separators
- Fix: Ensure LD_LIBRARY_PATH environment variable is cleared for Linux users to ensure no library conflict with Calibre

**Version 1.4.1** - 09 Apr 2011
- New: Support skinning of icons by putting them in a plugin name subfolder of local resources/images

**Version 1.4** - 03 Apr 2011
- New: Add Bliss application for Windows
- Update: Rewritten for new plugin infrastructure in Calibre 0.7.53

**Version 1.3** - 29 Jan 2011
- New: Support for OSX (Windows/Linux already available)
- New: Added more applications for Windows - Adobe Digital Editions, EPUBReader (Firefox plugin)
- New: Added default applications for OSX (Sigil, ADE, EPUBReader, Photoshop CS5, Pixelmator, Preview, Acrobat, Adobe Reader, Skim)
- New: Added default applications for Linux (Sigil, EPUBReader, Gimp)
- Update: Default applications list is now platform specific - don't display Windows applications to Linux/OSX users etc.
- Fix: For keyboard shortcuts not working if switch rows without reopening context menu

**Version 1.2** - 25 Jan 2011
- New: Include predefined application list
- Update: Rewrite with a configuration dialog to replace tweaks file

**Version 1.1** - 28 Jan 2011
- New: Renamed to 'Open with' plugin
- New: Add support for opening covers

**Version 1.0** - 05 Dec 2010
- Initial release as 'Open EPUB in editor' and 'Open format externally' plugins
