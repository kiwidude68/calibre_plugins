## Release History

**Version 1.11.2** - 02 August 2022 - by davidfor
- New: All kiwidude plugins updated/migrated to: https://github.com/kiwidude68/calibre_plugins
- Fix: Qt6 compatiblility - Prefs viewer tab stops.

**Version 1.11.2** - 26 January 2022 - by davidfor
- Update: To be compatible with Calibre v6/Qt6.

**Version 1.11.1** - 01 July 2021 - by davidfor
- Update: Changes to download page count for lubimyczytac.pl - thanks to BeckyEbook.

**Version 1.11.0** - 31 October 2020 - by davidfor
- Fix: Errors parsing non-English pages when downloading page count.
- New: Czech translation - thanks to seeder
- New: Add download page count from databazeknih.cz and cbdb.cz - thanks to seeder.

**Version 1.10.0** - 21 June 2020 - by davidfor
- Update: Updates for Python 3.

**Version 1.9.0** - 10 November 2019 - by davidfor
- New: Add download page count from Skoob.
- New: Allow a regex for extracting the page count when downloading from a web site.
- Update: Changes to download page count for lubimyczytac.pl - thanks to BeckyEbook.
- Update: Don't error if downloading page count and calculation is set to ADE algorithm.
- Fix: Warning when formats missing was repeating.
- Fix: Ignore error for books that have been removed since count job was started.

**Version 1.8.2** - 01 July 2018 - by davidfor
- Update: Changes due to refactoring of conversion for calibre 3.27.0. Handling so it is backwardly compatible.
- Update: Updates to translations. Missed these with the last updated.

**Version 1.8.0** - 28 May 2017 - by davidfor
- New: Add function to allow downloading page count from multiple sites.
- New: Add download page count from lubimyczytac.pl - thanks to BeckyEbook.
- New: Redesign configuration dialog into two tabs.
- New: French translation thanks to Nicolas F.
- Update: Change way menu/active site is indicated.
- Fix: Update book details pane after updating counts.

**Version 1.7.0** - 22 Jan 2017 - by davidfor
- New: Add callback for other plugins calling the count pages. See method call_plugin_callback in common_utils.py.
- New: Add option to choose between ICU word count and the old one. The default is ICU word count.
- New: Add language awareness for ICU word count. Uses the language in the book, otherwise defaults to English 
- New: Added German version of Flesch Reading Ease.
- New: Add option to use Preferred Input Format if it is available. 
- New: Added localization support for dialogs.
- New: Spanish translation thanks to Terisa de morgan.
- New: Polish translation thanks to BeckyEbook.
- New: German  translation thanks to Dirk-71.
- Update: Changed tooltip in configuration dialog to show on field as well as label. 
- Update: Change way statistics were written to the metadata to reduce side effects.
- Update: Only write changes if they are different to the current values.
- Fix: Adobe Page count on Mac machines with calibre 2.76 or later.
- Fix: For word count, text from all files was appended together without a space in between.
- Fix: "Fog", not "Fox".

**Version 1.6.10** - 08 Jan 2016 - by davidfor
- Update: Changed word count to use ICU BreakIterator. This accepts the book language, so it should be more accurate for non-English as well. Will fall back to old method if the ICU BreakIterator method cannot be loaded. 

**Version 1.6.9** - 05 Jul 2015
- New: Added option to disable the confirmation prompt each time to update the page/word counts. Use at your own risk - if you make simultaneous other changes to the book record they may get lost.
- Fix: For Cancel on the progress dialog (submitted by Ra�l)

**Version 1.6.8** - 28 Jul 2014
- Update: Support upcoming calibre 2.0

**Version 1.6.7** - 01 Sep 2013
- Update: Plugin now requires calibre 1.0
- Fix: For calibre changing location of unrar library affecting CBR page counts.

**Version 1.6.6** - 09 May 2013
- Fix: For Mac users using the ADE algorithm fix an issue with paths (as submitted by SimpleText)

**Version 1.6.5** - 06 Dec 2012
- Fix: If user chooses Adobe page count algorithm, do not attempt it on any formats other than EPUB.

**Version 1.6.4** - 05 Dec 2012
- New: Add a "Custom" algorithm option for page count, for users who want to specify the number of characters per page.
- Fix: When switching libraries, ensure keyboard shortcuts are reactivated
- Fix: Prevent plugin being used in Device View or on Device View context menu

**Version 1.6.3** - 26 Jul 2012
- Fix: If no page count downloaded from goodreads, prevent wrong error appearing in log
- Fix: If book configured for page count only and has no formats, prevent error in log (if downloading from Goodreads)

**Version 1.6.2** - 19 Jul 2012
- Fix: Make the html tag removal for body tag data case insensitive to fix issue with PDF conversions from 1.6.0

**Version 1.6.1** - 17 Jul 2012
- Fix: If a book has zero words, just display an error in log rather than storing zero in the column

**Version 1.6.0** - 14 Jul 2012
- New: Add three new statistics for calculating readability - Flesch Reading Ease, Flesch-Kincaid Grade Level and Gunning Fog.
- Update: Remove the redundant Words algorithm combo since only one algorithm offered.
- Update: Make page algorithm a per library setting rather than a plugin level setting
- Update: For CBR and CBZ book formats, calculate the number of pages as being the number of image files rather than converting to ePub
- Update: For CBR and CBZ book formats, only allow the Count Pages statistic and ignore all other statistics
- Fix: Tooltip missing line breaks in configuration dialog

**Version 1.5.0** - 22 Jun 2012
- New: Add a support option to the configuration dialog allowing viewing the plugin data stored in the database
- Update: Now requires calibre 0.8.57
- Update: Store configuration in the calibre database rather than a json file, to allow reuse from different computers (not simultaneously!)
- Update: Remove the additional menu items for individual word/page counts added in v1.4.0 as cluttered the interface

**Version 1.4.3** - 02 Jun 2012
- New: Add another page count algorithm of "Adobe Digital Editions (ADE)", which matches that used by the ADE software and some devices like Nook.
- Update: Rename the "Calibre Viewer (Adobe)" option to "E-book Viewer (calibre)" as it was misleading, calibre uses its own calculation not the Adobe one.

**Version 1.4.2** - 31 May 2012
- Update: Optimisation for counting pages for PDFs to read the page count from the PDF info rather than estimating it
- Fix: Revert the performance optimisation from 1.4.0 which affected the character count statistics

**Version 1.4.1** - 30 May 2012
- Fix: Problem with new overwrite existing behaviour not counting pages in some circumstances

**Version 1.4.0** - 30 May 2012
- New: Additional items for menu to allow doing page/word counts in isolation
- New: Add an 'Always overwrite existing value' checkbox (default is True), to allow users to turn off overwriting manually populated page/word counts without choosing the isolated menu option
- Update: Minimum version set to calibre 0.8.51
- Update: Performance optimisation for epubs for calibre 0.8.51 to reduce unneeded computation
- Update: Change to calibre API for deprecated dialog which caused issues that intermittently crashed calibre

**Version 1.3.3** - 13 Apr 2012
- Fix: Support change to Goodreads website for scraping page count

**Version 1.3.2** - 07 Apr 2012
- Fix: Preferred input order not being correctly applied (was alphabetical instead!)
- Fix: LIT formats would cause file in use errors

**Version 1.3.1** - 03 Mar 2012
- Update: Support count page/word estimates for any book format by converting to ePub, using preferred input format order

**Version 1.3.0** - 12 Feb 2012
- New: Add a Download from Goodreads option to allow retrieving book count from books that have a Goodreads identifier
- Update: If word count is disabled (i.e. only page count) allow download of page count for any book regardless of formats
- Fix: Attempted workaround for Qt issue on Mac where some books would crash calibre.

**Version 1.2.0** - 11 Sep 2011
- Update: Upgrade to support the centralised keyboard shortcut management in Calibre

**Version 1.1.3** - 03 Jul 2011
- Update: Preparation for deprecation for db.format_abspath() function in future Calibre for network backends

**Version 1.1.2** - 15 Jun 2011
- Update: No longer allow text custom columns
- Fix: Address issue of unicode character conversion with some MOBI books for count words

**Version 1.1.1** - 12 Jun 2011
- Update: Display log and no results dialog if no statistics were gathered
- Update: Change Mobi word count to not require a conversion
- Fix: If an unexpected error thrown while counting, include in log
- Fix: If user chooses to retrieve only word count

**Version 1.1** - 09 Jun 2011
- New: Add option to generate a word count instead of or in addition to page count

**Version 1.0.3** - 26 May 2011
- New: Offer choice of algorithms to match eBook viewer or APNX generation (default)
- Fix: Ensure DRM encrypted books do not cause errors

**Version 1.0.2** - 23 May 2011
- Update: Dialog and plugin descriptions updated to indicate Mobi support available/considered

**Version 1.0.1** - 23 May 2011
- New: Support option to prioritise either Mobi formats (using APNX algorithm) or ePub files
- Update: Change ePub page count algorithm to be similar to the Mobi APNX algorithm

**Version 1.0** - 21 May 2011
- Initial release of Count Pages plugin
