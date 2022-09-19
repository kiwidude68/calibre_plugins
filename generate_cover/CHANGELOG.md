## Release History

**Version 1.7.0** - xx Sep 2022
- New: All kiwidude plugins updated/migrated to: https://github.com/kiwidude68/calibre_plugins
- Update: Move user images from ``/resources/images/generate_cover`` to ``/plugins/generate_cover`` to prevent loss if user has not yet migrated to Calibre 6.
- Update: Drop PyQt4 support.
- Update: Refactoring of common code

**Version** 2.2.0 - 02 Aug 2022
- Update: Use cal6 icon theme system to allow plugin icon customization

**Version 2.1.1** - 14 Jul 2022
- Fix: Settings export in Calibre6/Qt6

**Version 2.1.0** - 21 Jan 2022
- Update: Changes for upcoming Qt6 Calibre

**Version 2.0.2** - 06 Feb 2021
- Fix for a py2/py3 difference in import zip

**Version 2.0.1** - 04 Dec 2020
- Fix image centering again

**Version 2.0.0** - 07 Nov 2020
- Update: Remove draw_old.py, not needed in Cal v2+
- Update: French translation - thanks un-pogaz!
- Update: Spanish translation - thanks dunhill!
- Fix: Border causing image to move horizontally.

**Version 1.5.25** - 12 Jun 2020
- Update: Custom text setText() instead of setHtml()

**Version 1.5.24** - 21 May 2020
- Update: Explicitly enforces the image size limits when read from the file, not just on the spin box in the dialog (and outputs a little debug data).

**Version 1.5.22** - 16 Jan 2020
- Update: Compatibility with Python 3

**Version 1.5.21** - 31 Jul 2016
- Fix: Regression in the previous release that broke integration with the FanFicFare plugin

**Version 1.5.20** - 29 Jul 2016
- Update: Also use the correct calibre APIs to read the cover from the database.
- Fix: Incorrect handling of book with multiple authors (extra spaces inserted around &)

**Version 1.5.19** - 21 May 2016
- Fix: Inability to use first font in the list of fonts for rendering text

**Version 1.5.18** - 20 May 2016
- Update: Compatibility for calibre 2.57+

**Version 1.5.16** - 11 Oct 2014
- Update: Compatibility for calibre 2.4+

**Version 1.5.15** - 15 Jul 2014
- Update: Compatibility for the upcoming calibre 2.0

**Version 1.5.14** - 29 Sep 2013
- Fix: User typing \n or or <br> or <br/> as part of the author to control split across multiple lines

**Version 1.5.13** - 24 Sep 2013
- New: Add a checkbox option to allow scaling up the cover image to fit the available area if it is too small.
- Update: Support the user typing \n or or <br> or <br/> as part of the title or series to control split across multiple lines

**Version 1.5.12** - 03 May 2013
- Fix: Change made to calibre API in 0.9.29

**Version 1.5.11** - 17 Mar 2013
- Fix: Import saved cover settings not working

**Version 1.5.10** - 06 Mar 2013
- Fix: Re-release of 1.5.9 due to problem with zip file

**Version 1.5.9** - 06 Mar 2013
- New: Add a "Metadata" section to the "Content" tab allowing the user to override title/author/series for one-off covers
- New: Add ability to configure a custom column (or tags column) to contain a value any time a cover is generated for a book

**Version 1.5.8** - 09 Dec 2012
- Update: Automatically "correct" any corrupted json files when users upgrade to this version
- Update: Check for corruption every time Generate Cover is opened. If found, show error dialog and autofix.
- Update: Prevent plugin being used in Device View or on Device View context menu

**Version 1.5.7** - 14 Nov 2012
- Fix: Stretch cover/resize option not finding full path to image.

**Version 1.5.6** - 03 Nov 2012
- New: Add support for calibre 0.9.5 which changed how Fonts are loaded.

**Version 1.5.5** - 14 Aug 2012
- Update: No longer use a calibre ImageView to preview cover as it has right-click menu and drag/drop not relevant to this plugin
- Update: Add protection against failed upgrades of the seriesText field.

**Version 1.5.4** - 01 Jun 2012
- Update: Make the series text an option so foreign language users can change it
- Update: No longer respect the calibre preferences Roman Numerals setting - series index will always be displayed numerically.

**Version 1.5.3** - 31 May 2012
- Update: Ensure paths to images used by this plugin are stored as relative paths for portability
- Update: Change the calibre library image to appear as {Default Image} in the images list
- Update: Reorder the images list so {Default Image} and {Current Cover} appear at the top
- Update: Allow renaming images changing only their casing

**Version 1.5.2** - 20 May 2012
- New: Add a 'Resize cover dimensions to match background image' suboption for if you have stretch image to use as cover background enabled.
- Update: Ensure code is more command line friendly via the API for external script usage

**Version 1.5.1** - 03 May 2012
- Fix: Issue of version number not incremented for 1.5.0

**Version 1.5.0** - 02 May 2012
- New: Add a separate right margin option, rather than using left margin for both
- New: On the Fonts tab allow specifying the alignment for each text item of left, centre, right rather than always centre
- New: Add export and import capability for sharing settings/images with other users
- New: Add an 'Autosave setting' option to Settings tab. When checked, any changes to settings are always saved (except when Cancel pressed)
- Update: Set maximum font size to 999 instead of 99
- Update: Expose API methods to allow more conveniently calling from other plugins
- Update: When clicking OK (or Import or Export) prompt user to save settings if changed before continuing.
- Update: If font assigned to a setting (whether existing or imported) is not found, use the default font rather than erroring
- Update: If user renames image just by stripping extension, treat this same as if user cancelled rename operation
- Update: Allow importing of multiple images at once.
- Update: Allow importing of multiple setting zips at once.
- Fix: Selection changes and corrupted multiple cover settings

**Version 1.4.0** - 11 Sep 2011
- Update: Upgrade to support the centralised keyboard shortcut management in Calibre

**Version 1.3.8** - 03 Jul 2011
- Update: Replace the deprecated composite_formatter with SafeFormat()

**Version 1.3.7** - 04 Jun 2011
- Update: Use a progress dialog while generating covers

**Version 1.3.6** - 03 Jun 2011
- Fix: Fonts being set to "Default" resulting in null in config file causing an error

**Version 1.3.5** - 01 Jun 2011
- New: Add a special token to the list of images representing the current cover for the book to allow embedding
- Fix: Abort autosize logic with replaced text when text is too large to fit so plugin does not lockup

**Version 1.3.4** - 27 Apr 2011
- Update: Allow custom text field to be formatted using Calibre template engine
- Update: Change custom text field so it is a multiline field for more space and complex content

**Version 1.3.3** - 23 Apr 2011
- Fix: Ensure that margins are set to zero if set to too high a value to prevent crash

**Version 1.3.2** - 09 Apr 2011
- Update: Support skinning of icons by putting them in a plugin name subfolder of local resources/images

**Version 1.3.1** - 04 Apr 2011
- Fix: Error for users migrating from particular previous versions

**Version 1.3** - 03 Apr 2011
- Update: Rewritten for new plugin infrastructure in Calibre 0.7.53

**Version 1.2.1** - 26 Mar 2011
- Update: Ensure version number put in config file for first-time user

**Version 1.2** - 26 Mar 2011
- New: Support freeform text added to cover.
- New: Add option to autosize text to fit on one line.
- Update: Add a timer to ensure GUI does not redraw preview as every UI change made.

**Version 1.1** - 16 Mar 2011
- New: Support drag/drop images.
- New: Support text colors.
- New: Support image as background.
- New: Support linking single font.
- New: Support named saved settings.
- New: Copy image files to resources directory.
- New: Support renaming image files.
- Update: Redesign GUI.

**Version 1.0.2** - 05 Mar 2011
- Fix: Error appearing if trying to customize through preferences

**Version 1.0.1** - 05 Mar 2011
- Update: Remove fixed widths for users with large fonts

**Version 1.0** - 05 Mar 2011
- Initial release of Generate Cover plugin
