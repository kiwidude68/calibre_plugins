## Release History

**Version 1.9.0** - XX Sep 2022
- New: All kiwidude plugins updated/migrated to: https://github.com/kiwidude68/calibre_plugins
- New: Add translation support.
- Add backwards compatiblity to min calibre 2.0
- Update: Refactoring of common code
- Fix: Predefined Amazon lists were not working

**Version 1.8.4** - 9 Aug 2022
- Update: update to calibre6 icon fetching. Code from @JimmXinu.

**Version 1.8.3** - 29 Jun 2022 - by capink
- Fix: Export settings not working in PyQt6

**Version 1.8.2** - 20 Feb 2022 - by capink
- Fix: PyQt6 migration bug.

**Version 1.8.1** - 13 Jan 2022 - by capink
- Fix: PyQt6 migration bug.

**Version 1.8.0** - 6 Jan 2022 - by capink
- Changes for the upcoming PyQt6.

**Version 1.5.7** - 7 Jun 2021 - by capink
- Update: Put Last Modified plugin into hibernation mode during the import process.

**Version 1.5.6** - 6 Jun 2021 - by capink
- Update: Add option to filter matches by algorithm used. The plugin title/author match keeps escalating to more aggressive matching algorithms if it does not find matches. The new option gives the user the chance to isolate matches from the more aggressive algorithms to examine them before proceeding.

**Version 1.5.5** - 15 May 2021 - by capink
- Update: Webpage Tab: download more than one page per inserting a {first_page-last_page} in the url in place of the page number. e.g. ``https://www.goodreads.com/list/show/1.Best_Books_Ever?page={1-3}``
- Fix: uuid identifier matching only works if book has other identifier type(s).
- Fix: For int fields, accept numbers with zero fractional part e.g. 1.00

**Version 1.5.4** - 5 Dec 2020 - by capink
- Update: add ability to run wizard from cmdline using calibre-debug -r "Import List"

**Version 1.5.3** - 22 Nov 2020 - by capink
- Update: Add uuid to identifiers to be used in matching, this will not be done if the user has a custom identifier named uuid.
- Update: Add option to disable tidying titles and author fields for csv import.
- Update: Bump schema version to 1.4
- Fix: Separate populating csv table from populating preview table. Now csv table is populated whenever csv file is changed without having to press the preview button.
- Fix: replace KEY_MATCH_BY_IDENTIFIER with KEY_MATCH_SETTINGS.

**Version 1.5.2** - 23 Oct 2020 - by capink
- Fix: bool column set to undefined if cell value is empty, 'undefined' or 'n/a'

**Version 1.5.1** - 21 Sep 2020 - by capink
- Update: Bump minimum calibre version to 2.0.0
- Fix: python3 compatibility problem when importing saved setting.

**Version 1.5.0** - 10 Aug 2020 - by capink
- Fix: Problem with imported dates being one day off.

**Version 1.4.10** - 18 Jul 2020 - by capink
- Fix: Highlighting and moving between matches in webpage tab not working with python3.
- Fix: Disable automatic preview when a new file is selected, to allow users to select proper field mappings first.
- Fix: Stop the tag view from updating while the progress bar is on.
- Fix: Move previous and next buttons in the web tab out of the scrollarea to make them visibile again.

**Version 1.4.9** - 15 Jul 2020 - by capink
- Update: Add a progress dialog (based on calibre's bulk metadata progress dialog with some modifications).
- Update: Add datatype validation to catch datatype errors before proceeding instead of failing in the middle of importing.
- Update: Add context menu for exporting to csv. Useful for exporting rows with validations errors.
- Fix: Problem with title/author match not matching books with multiple authors even if identical.
- Fix: Update broken predefined sources: Amazon, NY Bestsellers.
- Fix: Remove dead predefined sources: BookChart, Amazon Listmania, Play.com, SFFJazz, WHSmith
- Fix: Guess form headers now ignores duplicate headers.
- Fix: Update universal line mode to use open newline arg.
- Fix: Remove unused custom series indices headers.

**Version 1.4.8** - 8 Jul 2020 - by capink
- Fix: Error when removing and re-adding encodings.
- Fix: Buttons in encoding dialog now change their state based on selected item.

**Version 1.4.7** - 1 Jul 2020 - by capink
- Update: Support for different encodings in csv tab.
- Update: Changes to make the plugin translatable.
- Update: Option to automatically map fields in csv tabs by reading header names if present.
- Update: Add match by indentifier to web tab.
- Update: Add a scrollbar to controls in web tab.
- Update: Refactoring the code for match by identifier into one class in tab_common.py.

**Version 1.4.5** - 30 Jun 2020 - by capink
- Fix: problem with tab as a csv delimiter in python3.

**Version 1.4.4** - 24 Jun 2020 - by capink
- Fix: match_by_identifier saved settings affects other tabs.

**Version 1.4.3** - 17 Jun 2020 - by capink
- Fix: Bug when switching between settings with different match method not correctly setting match_by_identifier.
- Fix: scroll area in columns to import is now dynamically stretched based on contents.

**Version 1.4.2** - 12 Jun 2020 - by capink
- Update: Added option to csv tab to match by identifier.
- Fix: Accept empty values for numerical fields without raising exceptions.

**Version 1.4.1** - 10 Jun 2020 - by capink
- Update: Python3 support.

**Version 1.4.0** - 28 Apr 2019 - by davidfor
- Update: Use BeautifulSoup from calibre base.
- Fix: Open CSV in "Universal new-line mode" to handle mismatch of files and OS. 
- Fix: Goodreads, SFJazz and Wikipedia predefined sources for page changes.

**Version 1.3.0** - 21 Jan 2018 - by davidfor
- Update: All importing columns of type "Text, but with a fixed set of permitted values".
- Update: Use calibre author decoding instead of custom code. This uses the tweak.
- Fix: Improve handling of languages.

**Version 1.2.0** - 28 May 2017 - by davidfor
- New: Add languages to the list of available calibre columns.
- Update: Recipes for "Goodread: Listopia: Best Books Ever", "Fantastic Fiction" 
- Fix: Encoding issues to match calibre changes.
- Fix: Browser button icons.

**Version 1.1.5** - 19 Aug 2014
- Update: Support for upcoming calibre 2.0.

**Version 1.1.4** - 13 Oct 2013
- Fix: Search matched books list right clicks not working correctly

**Version 1.1.3** - 30 Sep 2013
- Update: Submission from wolf23 to support comma separated values for any type of custom column that supports multiple values.

**Version 1.1.2** - 29 Sep 2013
- New: Add a predefined setting for the Goodreads search results page
- Update: Remove the select next matched/unmatched etc buttons/menus. Replace with Show All/Matched/Unmatched radio buttons that filter.
- Update: Change logic so that if scraped website book data has no title it is not added to the right-hand side preview books list
- Update: If multiple values for a tags field from xpath when scraping off the web, separate the values with a comma and store as a single value.
- Fix: Various broken predefined settings from changes to websites being scraped
- Fix: Always put a horizontal scroll bar on both lists in the Resolve page of wizard to reduce change of vertical scrolling out of sync

**Version 1.1.1** - 13 Dec 2012
- Update: Skip blank rows in CSV files when previewing
- Update: Always display headers on CSV tab rather than hiding when Skip first row is checked

**Version 1.1** - 25 Oct 2012
- New: Allow importing into custom columns
- New: Allow updating metadata of existing books in your library from data off the list (standard or custom columns)
- New: Allow clipboard, csv and web page import to retrieve into a dynamic set of calibre standard columns including identifier fields
- New: Dynamically change the Preview, Search and Match columns presented to match what is configured for the import source
- New: Allow direct editing of plugin configuration data from config dialog (use at your own risk!)
- Update: Remove the ability to specify columns to display on the configuration screen
- Fix: Matched count on the Resolve step so multiple matches are not counted as matched
- Fix: Importing non utf-8 csv files such as for titles from LibraryThing

**Version 1.0** - 13 Aug 2012
- New: Add a "Select all matched" option to the right-click menu

**Version 0.4** - 16 Jul 2012
- Fix: If a book has a series name but no series index, default to a series index of zero

**Version 0.3** - 15 Jul 2012
- New: Add Series and Series Index columns to the csv page, web page tab and preview, change FF to scrape into this column.
- New: Add pubdate, series and series_index to the Clipboard tab
- Update: Additional change to way encodings are handled to simplify into utf-8
- Update: Change the icon size to 24 rather than 16 on the predefined/user settings
- Fix: Highlighting involving self-closing tags
- Fix: Incorrect XPath for the Goodreads Shelves lists

**Version 0.2** - 15 Jul 2012
- New: Add a Pubdate column to the csv page, web page tab and preview, change FF to scrape the year into this column.
- Update: Allow author XPath expressions to not be relative to a row XPath

**Version 0.1** - 14 Jul 2012
- Initial beta release of Import List plugin
