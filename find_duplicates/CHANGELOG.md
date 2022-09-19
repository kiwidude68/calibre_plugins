## Release History

**Version 1.10.0** - XX Sep 2022
- New: All kiwidude plugins updated/migrated to: https://github.com/kiwidude68/calibre_plugins
- Update: Add calibre 2.x backwards compatibility
- Update: Refactoring of common code

**Version 1.9.7** - 9 August 2022 - by capink
- Update: update to calibre6 icon fetching. Code from @JimmXinu.

**Version 1.9.6** - 16 July 2022 - by capink
- Update: Advanced mode add data dict to algorithms.
- Fix: PyQt6 migration bug.

**Version 1.9.5** - 27 April 2022 - by capink
- Fix: Advanced mode minor bug.

**Version 1.9.4** - 10 February 2022 - by capink
- Fix: PyQt6 migration bug.

**Version 1.9.3** - 9 February 2022 - by capink
- Fix: PyQt6 migration bug.
- Fix: Bug in rules widget dialog.

**Version 1.9.2** - 13 January 2022 - by capink
- Fix: PyQt6 migration bug.

**Version 1.9.1** - 7 January 2022 - by capink
- Fix: Bug with a QButtonGroup signal(s).

**Version 1.9.0** - 6 January 2022 - by capink
- Update: Changes for the upcoming PyQt6.

**Version 1.8.10** - 8 September 2021 - by capink
- Fix: Advanced Mode: Metadata Variations: Regression with custom columns variations.

**Version 1.8.9** - 12 July 2021 - by capink
- Fix: Advanced Mode: Bug with algorithms names not translated as in old versions.

**Version 1.8.8** - 28 June 2021 - by capink
- Update: Advanced Mode: Add formats to list of fields.
- Fix: Advanced Mode: Bug when searching for duplicate using fields with multiple values that are empty.

**Version 1.8.7** - 15 June 2021 - by capink
- Update: Restore the whole sort order instead of just one column (bound by maximum_resort_levels tweak).
- Update: Advanced mode: misc improvements.
- Update: Schema version bumped to 1.7

**Version 1.8.6** - 15 March 2021 - by capink
- Update: Advanced Mode: Add the ability to add custom algorithms through action chains module editor.
- Fix: Advanced Mode: Bug when adding custom algorithms that has no facotry.

**Version 1.8.5** - 12 February 2021 - by capink
- Fix: bug when exporting duplicates to json file in Windows.
- Fix: bug with calibre 2.x failing to import missing class. https://www.mobileread.com/forums/showpost.php?p=4090981&postcount=820

**Version 1.8.4** - 7 January 2021 - by capink
- Fix: update the plugin to use calibre.library.db for target database instead of the deprecated LibraryDatabase2. Also update to - use db.new_api.get_proxy_metadata to improve performance when using templates in advanced mode.

**Version 1.8.3** - 21 October 2020 - by capink
- Update: When changing libraries in library compare, restore the last used match rules from previous library if possible (all columns in match rules present in the newly selected library).
- Fix: Remove invalid locations from saved location list in library compare dialog before restoring.

**Version 1.8.2** - 17 October 2020 - by capink
- Update: Restore last used match rules (and sort filters).
- Fix: Allow dialog size to be reduced.

**Version 1.8.1** - 15 October 2020 - by capink
- Fix: Minor fixes.

**Version 1.8.0** - 11 October 2020 - by capink
- Update: Add advanced mode. It allows the user to match books without restrictions on the type nor the number of columns used. It also allows for user defined algorithms by using templates. It comes with a sort dialog allowing you to sort books based on columns and templates. To complement the sort feature, it adds extra marks to first and last books in each duplicate group: "first_duplicate", "last_duplicate".
- Update: Mark records with deleted formats in binary search as "deleted_binary_duplicate"
- Update: Option to export duplicate groups to json file. For advanced mode, the sorting of books is retained in the json file.
- Update: Update Spanish translation. Thanks to @dunhill.
- Update: Code refactoring.
- Update: Calibre minimum version bumped to 2.0.0
- Update: Schema version bumped to 1.6
- Fix: Mark exemptions only when showing them and remove the marks afterwards.
- Fix: Restore state if the user exits calibre with the duplicates restriction still on. Thanks to @chaley
- Fix: Remember last sort in library view and revert back to it.

**Version 1.7.2** - 25 June 2020 - by davidfor
- Fix: A couple of errors with translations.

**Version 1.7.0** - 21 June 2020 - by davidfor
- New: Make translatable.
- New: Add Spanish translation. Thanks to @dunhill.
- Update: Use delete key to remove entry from library list in cross library search options.
- Update: Changes for Python 3 support in calibre.

**Version 1.6.3** - 12 Jun 2017
- Fix: Compatibility with Calibre 2.99b11+

**Version 1.6.1** - 03 Jan 2013
- Fix: For when comparing library duplicates to ensure saved searches are not corrupted.

**Version 1.6.0** - 29 Oct 2012
- New: Add a context menu to the metadata variations list to allow choosing the selected name on the right side.
- Update: Change "ISBN Compare" to "Identifier" with a dropdown allowing comparison of any identifier field.

**Version 1.5.3** - 14 Aug 2012
- Update: When using "Find library duplicates" display all duplicate matches for the current library as marked:duplicate (except for author duplicates)

**Version 1.5.2** - 21 Jul 2012
- Update: When using "Find library duplicates" clear the current search in order to compare the entire restricted library
- Update: When using "Find metadata variations" and showing books, fire the search again to ensure results reflect the search

**Version 1.5.1** - 21 Jul 2012
- New: Add a "Save log" button for the "Find library duplicates" result screen.

**Version 1.5.0** - 20 Jul 2012
- New: Add a "Find library duplicates" option for cross-library duplicate comparisons into a log report
- Update: If currently running a duplicate book search and execute a metadata variation search, clear search first

**Version 1.4.0** - 17 Jul 2012
- New: Add a Find metadata variations option to search for author, series, publisher and tag variations, and allow renaming them from the dialog.
- Update: Now requires calibre 0.8.59
- Fix: Fuzzy author comparisons which will no longer compute a reverse hash to reduce the false positives it generated

**Version 1.3.0** - 22 Jun 2012
- New: Add a support option to the configuration dialog allowing viewing the plugin data stored in the database
- New: Add an option to allow automatic removal of binary duplicates (does not delete books records, only the newest copies of that format).
- Update: Now requires calibre 0.8.57
- Update: Store configuration in the calibre database rather than a json file, to allow reuse from different computers (not simultaneously!)

**Version 1.2.3** - 02 Dec 2011
- Update: Make the languages comparison optional (default false) via a checkbox on the Find Duplicates dialog

**Version 1.2.2** - 25 Nov 2011
- Update: Take the languages field into account when doing title based duplicate comparisons

**Version 1.2.1** - 12 Nov 2011
- Update: When selecting ISBN or Binary compare, hide the Title/Author groupbox options
- Update: Some cosmetic additions to the text for ISBN/Binary options

**Version 1.2.0** - 11 Sep 2011
- Update: Remove customisation of shortcuts on tab, to use Calibre's centrally managed shortcuts instead.
- Fix: For when switching to an ignore title search where author search was previously set to ignore.

**Version 1.1.4** - 04 Jul 2011
- Fix: Stuff broken by Calibre 0.8.8 in the tag view
- Fix: For removing an author exemption

**Version 1.1.3** - 03 Jul 2011
- Update: Preparation for deprecation of db.format_abspath() for networked backend

**Version 1.1.2** - 03 Jul 2011
- Fix: Issue with Calibre 0.8.8 tag browser search_restriction refactoring

**Version 1.1.1** - 12 Jun 2011
- Update: Add van to list of ignored author words
- Fix: Error dialog not referenced correctly

**Version 1.1** - 3 May 2011
- New: Add support for binary comparison searches to find book formats with exactly the same content
- New: Disable the Ignore title, identical author combination as will not a valid one (never duplicates)
- New: Allow the remove, mark current and mark all group exemption dialogs able to be hidden from showing again.
- New: Allow various count of result and no result information dialogs able to be hidden from showing again.
- New: Allow user to reset confirmation dialogs related to find duplicates from the configuration dialog
- Update: Include swapping author name order in all but identical author checks. So A B / B A or A,B / B,A will match.
- Update: Compare multiple authors for most author algorithms to increase duplicate coverage.
- Update: No longer calculate exemption preview detailed messages for the confirmation dialog for performance
- Update: Replace how exemptions are stored in the config file to make more scalable
- Update: Change Manage exemptions dialog to have tab for each author with exemptions and show section only if have exemptions

**Version 1.0** - 26 Apr 2011
- Initial release of Find Duplicates plugin
