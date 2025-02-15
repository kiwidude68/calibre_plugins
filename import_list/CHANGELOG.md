# Import List Change Log

## [1.9.6] - 2025-02-15
### Fixed
- Cailbre 7.26 removed the `set_auto_complete_function` delegate as no longer necessary. (cbhaley)

## [1.9.5] - 2025-02-15
### Fixed
- Cailbre 7.26 removed the `set_database` delegate as no longer necessary. (cbhaley)

## [1.9.4] - 2024-04-01
### Fixed
- Fix for calibre 7 for QFileDialog errors.

## [1.9.3] - 2024-03-24
### Changed
- Do not auto-size columns in the 'matches in library' grid so that for instance a lot of tags would create a super wide column.
- Move the Matched dropdown of algorithms into the radiobutton area to prevent need for dynamic show/hide.
- Add a splitter for resizing between the Books in list / Matches in library grids
- Fix libpng warning: icCCP: known incorrect sRGB profile using `magick mogrify *.png`

## [1.9.2] - 2024-03-17
### Added
- Tamil translation

## [1.9.1] - 2023-08-06
### Added
- Russian translation (various)
### Fixed
- Strip commas from numeric columns when importing and trying to convert to integer. (Rellwood)

## [1.9.0] - 2022-10-16
_All kiwidude plugins updated/migrated to: https://github.com/kiwidude68/calibre_plugins_
### Added
- Add backwards compatiblity to min calibre 3.41.0
- Add Help button to configuration dialog.
- Add translation support.
- Spanish translation (@dunhill)
- Ukranian translation (@yurchor)
### Changed
- Refactoring of common code
- Changed wizard style of appearance, tweaked layouts.
### Fixed
- Predefined Amazon lists were not working

## [1.8.4] - 2022-08-09
### Changed
- Update to calibre6 icon fetching. (@capink, @JimmXinu)

## [1.8.3] - 2022-06-29
### Fixed
- Export settings not working in PyQt6 (@capink)

## [1.8.2] - 2022-02-20
### Fixed
- PyQt6 migration bug. (@capink)

## [1.8.1] - 2022-01-13
### Fixed
- PyQt6 migration bug. (@capink)

## [1.8.0] - 2022-01-06
### Changed
- Changes for the upcoming PyQt6. (@capink)

## [1.5.7] - 2021-06-07
### Changed
- Put Last Modified plugin into hibernation mode during the import process. (@capink)

## [1.5.6] - 2021-06-06
### Changed
- Add option to filter matches by algorithm used. The plugin title/author match keeps escalating to more aggressive matching algorithms if it does not find matches. The new option gives the user the chance to isolate matches from the more aggressive algorithms to examine them before proceeding. (@capink)

## [1.5.5] - 2021-05-15
### Changed
- Webpage Tab: download more than one page per inserting a {first_page-last_page} in the url in place of the page number. e.g. `https://www.goodreads.com/list/show/1.Best_Books_Ever?page={1-3}` (@capink)
### Fixed
- The uuid identifier matching only works if book has other identifier type(s).
- For int fields, accept numbers with zero fractional part e.g. 1.00

## [1.5.4] - 2020-12-05
### Added
- Add ability to run wizard from cmdline using `calibre-debug -r "Import List"`

## [1.5.3] - 2020-11-22
### Changed
- Add uuid to identifiers to be used in matching, this will not be done if the user has a custom identifier named uuid. (@capink)
- Add option to disable tidying titles and author fields for csv import.
- Bump schema version to 1.4
### Fixed
- Separate populating csv table from populating preview table. Now csv table is populated whenever csv file is changed without having to press the preview button.
- Replace KEY_MATCH_BY_IDENTIFIER with KEY_MATCH_SETTINGS.

## [1.5.2] - 2020-10-23
### Fixed
- Bool column set to undefined if cell value is empty, 'undefined' or 'n/a' (@capink)

## [1.5.1] - 2020-09-21
### Changed
- Bump minimum calibre version to 2.0.0 (@capink)
### Fixed
- Python3 compatibility problem when importing saved setting.

## [1.5.0] - 2020-08-10
### Fixed
- Problem with imported dates being one day off. (@capink)

## [1.4.10] - 2020-07-18
### Fixed
- Highlighting and moving between matches in webpage tab not working with python3. (@capink)
- Disable automatic preview when a new file is selected, to allow users to select proper field mappings first.
- Stop the tag view from updating while the progress bar is on.
- Move previous and next buttons in the web tab out of the scrollarea to make them visible again.

## [1.4.9] - 2020-07-15
### Changed
- Add a progress dialog (based on calibre's bulk metadata progress dialog with some modifications). (@capink)
- Add datatype validation to catch datatype errors before proceeding instead of failing in the middle of importing.
- Add context menu for exporting to csv. Useful for exporting rows with validations errors.
### Fixed
- Problem with title/author match not matching books with multiple authors even if identical.
- Update broken predefined sources: Amazon, NY Bestsellers.
- Remove dead predefined sources: BookChart, Amazon Listmania, Play.com, SFFJazz, WHSmith
- Guess form headers now ignores duplicate headers.
- Update universal line mode to use open newline arg.
- Remove unused custom series indices headers.

## [1.4.8] - 2020-07-08
### Fixed
- Error when removing and re-adding encodings. (@capink)
- Buttons in encoding dialog now change their state based on selected item.

## [1.4.7] - 2020-07-01
### Changed
- Support for different encodings in csv tab. (@capink)
- Changes to make the plugin translatable.
- Option to automatically map fields in csv tabs by reading header names if present.
- Add match by identifier to web tab.
- Add a scrollbar to controls in web tab.
- Refactoring the code for match by identifier into one class in tab_common.py.

## [1.4.5] - 2020-06-30
### Fixed
- Problem with tab as a csv delimiter in python3. (@capink)

## [1.4.4] - 2020-06-24
### Fixed
- The match_by_identifier saved settings affects other tabs. (@capink)

## [1.4.3] - 2020-06-17
### Fixed
- Bug when switching between settings with different match method not correctly setting match_by_identifier. (@capink)
- Scroll area in columns to import is now dynamically stretched based on contents.

## [1.4.2] - 2020-06-12
### Changed
- Added option to csv tab to match by identifier. (@capink)
### Fixed
- Accept empty values for numerical fields without raising exceptions.

## [1.4.1] - 2020-06-10
### Changed
- Python3 support. (@capink)

## [1.4.0] - 2019-04-28
### Changed
- Use BeautifulSoup from calibre base. (@davidfor)
### Fixed
- Open CSV in "Universal new-line mode" to handle mismatch of files and OS. 
- Goodreads, SFJazz and Wikipedia predefined sources for page changes.

## [1.3.0] - 2018-01-21
### Changed
- All importing columns of type "Text, but with a fixed set of permitted values". (@davidfor)
- Use calibre author decoding instead of custom code. This uses the tweak.
### Fixed
- Improve handling of languages.

## [1.2.0] - 2017-05-28
### Added
- Add languages to the list of available calibre columns. (@davidfor)
### Changed
- Recipes for "Goodread: Listopia: Best Books Ever", "Fantastic Fiction" 
### Fixed
- Encoding issues to match calibre changes.
- Browser button icons.

## [1.1.5] - 2014-08-19
### Changed
- Support for upcoming calibre 2.0.

## [1.1.4] - 2013-10-13
### Fixed
- Search matched books list right clicks not working correctly

## [1.1.3] - 2013-09-30
### Changed
- Submission from wolf23 to support comma separated values for any type of custom column that supports multiple values.

## [1.1.2] - 2013-09-29
### Added
- Add a predefined setting for the Goodreads search results page
- Remove the select next matched/unmatched etc buttons/menus. Replace with Show All/Matched/Unmatched radio buttons that filter.
### Changed
- Change logic so that if scraped website book data has no title it is not added to the right-hand side preview books list
- If multiple values for a tags field from xpath when scraping off the web, separate the values with a comma and store as a single value.
### Fixed
- Various broken predefined settings from changes to websites being scraped
- Always put a horizontal scroll bar on both lists in the Resolve page of wizard to reduce change of vertical scrolling out of sync

## [1.1.1] - 2012-12-13
### Changed
- Skip blank rows in CSV files when previewing
- Always display headers on CSV tab rather than hiding when Skip first row is checked

## [1.1.0] - 2012-10-25
### Added
- Allow importing into custom columns
- Allow updating metadata of existing books in your library from data off the list (standard or custom columns)
- Allow clipboard, csv and web page import to retrieve into a dynamic set of calibre standard columns including identifier fields
- Dynamically change the Preview, Search and Match columns presented to match what is configured for the import source
- Allow direct editing of plugin configuration data from config dialog (use at your own risk!)
### Changed
- Remove the ability to specify columns to display on the configuration screen
### Fixed
- Matched count on the Resolve step so multiple matches are not counted as matched
- Importing non utf-8 csv files such as for titles from LibraryThing

## [1.0.0] - 2012-08-13
### Added
- Add a "Select all matched" option to the right-click menu

## [0.4.0] - 2012-07-16
### Fixed
- If a book has a series name but no series index, default to a series index of zero

## [0.3.0] - 2012-07-15
### Added
- Add Series and Series Index columns to the csv page, web page tab and preview, change FF to scrape into this column.
- Add pubdate, series and series_index to the Clipboard tab
### Changed
- Additional change to way encodings are handled to simplify into utf-8
- Change the icon size to 24 rather than 16 on the predefined/user settings
### Fixed
- Highlighting involving self-closing tags
- Incorrect XPath for the Goodreads Shelves lists

## [0.2.0] - 2012-07-15
### Added
- Add a Pubdate column to the csv page, web page tab and preview, change FF to scrape the year into this column.
### Changed
- Allow author XPath expressions to not be relative to a row XPath

## [0.1.0] - 2012-07-14
_Initial beta release of Import List plugin_
