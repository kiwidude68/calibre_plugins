## Release History

**Version 1.10.0** - XX Sep 2022
- New: All kiwidude plugins updated/migrated to: https://github.com/kiwidude68/calibre_plugins
- New: Add full translation support
- New: Translations for Spanish, Russian, Ukranian
- Update: Drop PyQt4 support, require calibre 2.x or later.
- Update: Refactoring of common code
- Update: Any custom website menu images must now be in /resources/images/Search The Internet/

**Version 1.9.0** - 14 Jul 2022 - made by Terisa de morgan
- Update: Changes for QT6 support in calibre
 
**Version 1.8.1** - 26 Dec 2020 - made by davidfor
- Fix: Python 3 string related error when building post request.
 
**Version 1.8.0** - 02 Sep 2020 - made by davidfor
- New: Enable translations.
- Update: Use different formatter so templates can be used. This was specifically to allow use of identifiers.
- Update: Changes for Python 3 support in calibre.
 
**Version 1.7.6** - 09 Mar 2016
- Fix: Missing ) in help formula
 
**Version 1.7.2** - 11 Jul 2014
- Update: QT5 support work

**Version 1.7.1** - 24 Sep 2011
- Update: When doing HTTP POST queries (like Fiction DB) do not encode the passed query values, just escape them instead.

**Version 1.7.0** - 11 Sep 2011
- Update: Switch the formatter used for resolving foreign names as the "new" SafeFormat is broken for this plugin's purposes.
- Update: Support the centralised keyboard shortcut management in Calibre

**Version 1.6.6** - 10 Aug 2011
- Update: Change the location of SafeFormat class which was removed from Calibre for release 0.8.14

**Version 1.6.5** - 08 May 2011
- Update: Change webbrowser launching to use Calibre's wrapper for the default browser for better Linux support

**Version 1.6.4** - 09 Apr 2011
- New: Support skinning of icons by putting them in a plugin name subfolder of local resources/images

**Version 1.6.3** - 05 Apr 2011
- Fix: Ensure non-valid characters are removed when encoding

**Version 1.6.2** - 04 Apr 2011
- Update: Correct version number to reflect 1.6.1

**Version 1.6.1** - 04 Apr 2011
- Fix: Open group menu having incorrect icon_name argument

**Version 1.6** - 03 Apr 2011
- Update: Rewritten for new plugin infrastructure in Calibre 0.7.53

**Version 1.5.1** - 28 Jan 2011
- Update: Display clickable button on HTTP POST page if javascript disabled
- Fix: Swapping rows after addition of GET/POST column

**Version 1.5** - 28 Jan 2011
- New: Support HTTP POST websites like FictFact
- Update: Use the Calibre template processor to support other metadata fields
- Update: Archive import export use standard zip extension for ease of uploading to forums
- Fix: Ensure config window is parented to prevent multiple Calibre windows in taskbar

**Version 1.4** - 24 Jan 2011
- New: Add a configuration dialog to replace tweaks file
- New: Build in library of websites for users to choose from
- Update: Split into separate code files with proxy architecture
- Update: Make menus dynamically recreated without restarts
- Update: Ensure author always passed in FN LN format

**Version 1.3** - 31 Dec 2010
- New: Support Calibre 0.7.34 feature of plugin images retained within the zip file

**Version 1.2** - 31 Dec 2010
- New: Support for encoding for passing foreign language names to Amazon etc

**Version 1.1** - 04 Dec 2010
- New: Support for multiple row selections to launching multiple searches

**Version 1.0** - 28 Nov 2010
- Initial release of Search The Internet plugin
