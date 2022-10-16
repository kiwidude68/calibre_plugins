# Count Pages Change Log

## [1.12.0] - 2022-10-16
_All kiwidude plugins updated/migrated to: https://github.com/kiwidude68/calibre_plugins_
### Added
- Support for .webp page counts in CBR/CBZ.
- Add a Help button to the menu and configuration dialog in the Other tab.
- Russian translation (Caarmi)
- Ukranian translation (@yurchor)
### Changed
- **Breaking:** Drop PyQt4 support, require calibre 2.x or later.
- Refactoring of common code.
- Include author(s) with the title in the logging output to make it easier to identify which book that related to.

## [1.11.2] - 2022-08-02
### Fixed
- Qt6 compatiblility - Prefs viewer tab stops. (@davidfor)

## [1.11.2] - 2022-01-26
### Changed
- To be compatible with Calibre v6/Qt6. (@davidfor)

## [1.11.1] - 2021-07-01
### Changed
- Changes to download page count for lubimyczytac.pl (@BeckyEbook)

## [1.11.0] - 2020-10-31
### Added
- Czech translation (@seeder)
- Add download page count from databazeknih.cz and cbdb.cz (@seeder)
### Fixed
- Errors parsing non-English pages when downloading page count. (@davidfor)

## [1.10.0] - 2020-06-21
### Changed
- Updates for Python 3. (@davidfor)

## [1.9.0] - 2019-11-10
### Added
- Add download page count from Skoob. (@davidfor)
- Allow a regex for extracting the page count when downloading from a web site.
### Changed
- Changes to download page count for lubimyczytac.pl - thanks to BeckyEbook.
- Don't error if downloading page count and calculation is set to ADE algorithm.
### Fixed
- Warning when formats missing was repeating.
- Ignore error for books that have been removed since count job was started.

## [1.8.2] - 2018-07-01
### Changed
- Changes due to refactoring of conversion for calibre 3.27.0. Handling so it is backwardly compatible. (@davidfor)
- Updates to translations. Missed these with the last updated.

## [1.8.0] - 2017-05-28
### Added
- Add function to allow downloading page count from multiple sites. (@davidfor)
- Add download page count from lubimyczytac.pl (@BeckyEbook)
- Redesign configuration dialog into two tabs.
- French translation thanks to Nicolas F.
### Changed
- Change way menu/active site is indicated.
### Fixed
- Update book details pane after updating counts.

## [1.7.0] - 2017-01-22
### Added
- Add callback for other plugins calling the count pages. See method call_plugin_callback in `common_utils.py`. (@davidfor)
- Add option to choose between ICU word count and the old one. The default is ICU word count.
- Add language awareness for ICU word count. Uses the language in the book, otherwise defaults to English 
- Added German version of Flesch Reading Ease.
- Add option to use Preferred Input Format if it is available. 
- Added localization support for dialogs.
- Spanish translation thanks to Terisa de morgan.
- Polish translation thanks to BeckyEbook.
- German  translation thanks to Dirk-71.
### Changed
- Changed tooltip in configuration dialog to show on field as well as label. 
- Change way statistics were written to the metadata to reduce side effects.
- Only write changes if they are different to the current values.
### Fixed
- Adobe Page count on Mac machines with calibre 2.76 or later.
- For word count, text from all files was appended together without a space in between.
- "Fog", not "Fox".

## [1.6.10] - 2016-01-08
### Changed
- Changed word count to use ICU BreakIterator. This accepts the book language, so it should be more accurate for non-English as well. Will fall back to old method if the ICU BreakIterator method cannot be loaded. (@davidfor)

## [1.6.9] - 2015-07-05
### Added
- Added option to disable the confirmation prompt each time to update the page/word counts. Use at your own risk - if you make simultaneous other changes to the book record they may get lost.
### Fixed
- For Cancel on the progress dialog (submitted by Ra�l)

## [1.6.8] - 2014-07-28
### Changed
- Support upcoming calibre 2.0

## [1.6.7] - 2013-09-01
### Changed
- Plugin now requires calibre 1.0
### Fixed
- For calibre changing location of unrar library affecting CBR page counts.

## [1.6.6] - 2013-05-09
### Fixed
- For Mac users using the ADE algorithm fix an issue with paths (as submitted by SimpleText)

## [1.6.5] - 2012-12-06
### Fixed
- If user chooses Adobe page count algorithm, do not attempt it on any formats other than EPUB.

## [1.6.4] - 2012-12-05
### Added
- Add a "Custom" algorithm option for page count, for users who want to specify the number of characters per page.
### Fixed
- When switching libraries, ensure keyboard shortcuts are reactivated
- Prevent plugin being used in Device View or on Device View context menu

## [1.6.3] - 2012-07-26
### Fixed
- If no page count downloaded from goodreads, prevent wrong error appearing in log
- If book configured for page count only and has no formats, prevent error in log (if downloading from Goodreads)

## [1.6.2] - 2012-07-19
### Fixed
- Make the html tag removal for body tag data case insensitive to fix issue with PDF conversions from 1.6.0

## [1.6.1] - 2012-07-17
### Fixed
- If a book has zero words, just display an error in log rather than storing zero in the column

## [1.6.0] - 2012-07-14
### Added
- Add three new statistics for calculating readability - Flesch Reading Ease, Flesch-Kincaid Grade Level and Gunning Fog.
### Changed
- Remove the redundant Words algorithm combo since only one algorithm offered.
- Make page algorithm a per library setting rather than a plugin level setting
- For CBR and CBZ book formats, calculate the number of pages as being the number of image files rather than converting to ePub
- For CBR and CBZ book formats, only allow the Count Pages statistic and ignore all other statistics
### Fixed
- Tooltip missing line breaks in configuration dialog

## [1.5.0] - 2012-06-22
### Added
- Add a support option to the configuration dialog allowing viewing the plugin data stored in the database
### Changed
- Now requires calibre 0.8.57
- Store configuration in the calibre database rather than a json file, to allow reuse from different computers (not simultaneously!)
- Remove the additional menu items for individual word/page counts added in v1.4.0 as cluttered the interface

## [1.4.3] - 2012-06-02
### Added
- Add another page count algorithm of "Adobe Digital Editions (ADE)", which matches that used by the ADE software and some devices like Nook.
### Changed
- Rename the "Calibre Viewer (Adobe)" option to "E-book Viewer (calibre)" as it was misleading, calibre uses its own calculation not the Adobe one.

## [1.4.2] - 2012-05-31
### Changed
- Optimisation for counting pages for PDFs to read the page count from the PDF info rather than estimating it
### Fixed
- Revert the performance optimisation from 1.4.0 which affected the character count statistics

## [1.4.1] - 2012-05-30
### Fixed
- Problem with new overwrite existing behaviour not counting pages in some circumstances

## [1.4.0] - 2012-05-30
### Added
- Additional items for menu to allow doing page/word counts in isolation
- Add an 'Always overwrite existing value' checkbox (default is True), to allow users to turn off overwriting manually populated page/word counts without choosing the isolated menu option
### Changed
- Minimum version set to calibre 0.8.51
- Performance optimisation for epubs for calibre 0.8.51 to reduce unneeded computation
- Change to calibre API for deprecated dialog which caused issues that intermittently crashed calibre

## [1.3.3] - 2012-04-13
### Fixed
- Support change to Goodreads website for scraping page count

## [1.3.2] - 2012-04-07
### Fixed
- Preferred input order not being correctly applied (was alphabetical instead!)
- LIT formats would cause file in use errors

## [1.3.1] - 2012-03-03
### Changed
- Support count page/word estimates for any book format by converting to ePub, using preferred input format order

## [1.3.0] - 2012-02-12
### Added
- Add a Download from Goodreads option to allow retrieving book count from books that have a Goodreads identifier
### Changed
- If word count is disabled (i.e. only page count) allow download of page count for any book regardless of formats
### Fixed
- Attempted workaround for Qt issue on Mac where some books would crash calibre.

## [1.2.0] - 2011-09-11
### Changed
- Upgrade to support the centralised keyboard shortcut management in Calibre

## [1.1.3] - 2011-07-03
### Changed
- Preparation for deprecation for db.format_abspath() function in future Calibre for network backends

## [1.1.2] - 2011-06-15
### Changed
- No longer allow text custom columns
### Fixed
- Address issue of unicode character conversion with some MOBI books for count words

## [1.1.1] - 2011-06-12
### Changed
- Display log and no results dialog if no statistics were gathered
- Change Mobi word count to not require a conversion
### Fixed
- If an unexpected error thrown while counting, include in log
- If user chooses to retrieve only word count

## [1.1.0] - 2011-06-09
### Added
- Add option to generate a word count instead of or in addition to page count

## [1.0.3] - 2011-05-26
### Added
- Offer choice of algorithms to match eBook viewer or APNX generation (default)
### Fixed
- Ensure DRM encrypted books do not cause errors

## [1.0.2] - 2011-05-23
### Changed
- Dialog and plugin descriptions updated to indicate Mobi support available/considered

## [1.0.1] - 2011-05-23
### Added
- Support option to prioritise either Mobi formats (using APNX algorithm) or ePub files
### Changed
- Change ePub page count algorithm to be similar to the Mobi APNX algorithm

## [1.0.0] - 2011-05-21
_Initial release of Count Pages plugin_
