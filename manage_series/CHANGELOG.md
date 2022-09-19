## Release History

**Version 1.5.0** - XX Sep 2022
- New: All kiwidude plugins updated/migrated to: https://github.com/kiwidude68/calibre_plugins
- New: Add translation support.
- Update: Drop PyQt4 support, require calibre 2.x or later.
- Update: Refactoring of common code

**Version 1.4.0** - 02 Aug 2022
- Update: Use cal6 icon theme system to allow plugin icon customization

**Version 1.3.0** - 22 Jan 2022
- Update: Bump Minimum Calibre version to 2.85.1
- Update: Changes for upcoming Qt6 Calibre

**Version 1.2.10** - 27 Sep 2020
- Update: More compatibility with Python 3

**Version 1.2.9** - 16 Jan 2020
- Update: Compatibility with Python 3

**Version 1.2.8** - 24 Jul 2013
- Update: Compatibility for the upcoming calibre 2.0

**Version 1.2.7** - 04 May 2013
- Fix: Issue introduced with changes to calibre in v0.9.29

**Version 1.2.6** - 03 Mar 2013
- Update: Prevent plugin being used in Device View or on Device View context menu
- Fix: Where trying to lock series index for a book without a series

**Version 1.2.5** - 26 Jul 2012
- New: Add a "Sort by Original Series Name" feature for users who are appending series together that overlap indexes
- Update: Rename "Sort by Original Series" to "Sort by Original Series Index"

**Version 1.2.4** - 05 Jul 2012
- Fix: For empty book where the pubdate column would error from a null date.

**Version 1.2.3** - 23 Jun 2012
- Update: Ensure lock series index maximum value is far higher.
- Update: Ensure the lock series index text is all selected by default to allow overtyping when dialog displayed.

**Version 1.2.2** - 04 Jun 2012
- New: Put checkbox option on the Lock Index dialog when locking multiple series rows to allow setting all remaining to the specified index value
- New: Add a new context menu option of "Lock old series index" as a fast way to lock series index values to their old values for selected books
- New: Allow editing the pubdate column for books on this dialog.
- Fix: Where column headings for series columns were not correctly displayed on first opening dialog
- Fix: Where context menus not always updating until selection changed

**Version 1.2.1** - 17 Sep 2011
- Update: Only save series indexes for the last selected series column in the dialog
- Fix: If multi-select rows to assign an index, clicking Cancel will cancel asking for any further changes

**Version 1.2.0** - 11 Sep 2011
- Update: Upgrade to support the centralised keyboard shortcut management in Calibre

**Version 1.1.2** - 08 May 2011
- Update: Change webbrowser launching to use Calibre's wrapper for the default browser for better Linux support

**Version 1.1.1** - 09 Apr 2011
- Update: Support skinning of icons by putting them in a plugin name subfolder of local resources/images
- Update: Ensure that encoding for launching website url ignores failures.

**Version 1.1** - 03 Apr 2011
- Update: Rewritten for new plugin infrastructure in Calibre 0.7.53
- Update: Change to use OrderedDict from collections (deprecated code in Calibre)

**Version 1.0** - 16 Mar 2011
- Initial release of Manage Series plugin
