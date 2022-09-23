# Change Log

## [1.10.0] - 2022-09-XX
_All kiwidude plugins updated/migrated to: https://github.com/kiwidude68/calibre_plugins_
### Changed
- Add calibre 2.x backwards compatibility
- Refactoring of common code

## [1.9.7] - 2022-08-09
### Changed
- Update to calibre6 icon fetching. (@capink,@JimmXinu)

## [1.9.6] - 2022-07-16
### Changed
- Advanced mode add data dict to algorithms. (@capink)
### Fixed
- PyQt6 migration bug.

## [1.9.5] - 2022-04-27
### Fixed
- Advanced mode minor bug. (@capink)

## [1.9.4] - 2022-02-10
### Fixed
- PyQt6 migration bug. (@capink)

## [1.9.3] - 2022-02-09
### Fixed
- PyQt6 migration bug. (@capink)
- Bug in rules widget dialog.

## [1.9.2] - 2022-01-13
### Fixed
- PyQt6 migration bug. (@capink)

## [1.9.1] - 2022-01-07
### Fixed
- Bug with a QButtonGroup signal(s). (@capink)

## [1.9.0] - 2022-01-06
### Changed
- Changes for the upcoming PyQt6. (@capink)

## [1.8.10] - 2021-09-08
### Fixed
- Advanced Mode: Metadata Variations: Regression with custom columns variations. (@capink)

## [1.8.9] - 2021-07-12
### Fixed
- Advanced Mode: Bug with algorithms names not translated as in old versions. (@capink)

## [1.8.8] - 2021-06-28
### Changed
- Advanced Mode: Add formats to list of fields. (@capink)
### Fixed
- Advanced Mode: Bug when searching for duplicate using fields with multiple values that are empty.

## [1.8.7] - 2021-06-15
### Changed
- Restore the whole sort order instead of just one column (bound by maximum_resort_levels tweak). (@capink)
- Advanced mode: misc improvements.
- Schema version bumped to 1.7

## [1.8.6] - 2021-03-15
### Changed
- Advanced Mode: Add the ability to add custom algorithms through action chains module editor. (@capink)
### Fixed
- Advanced Mode: Bug when adding custom algorithms that has no factory.

## [1.8.5] - 2021-02-12
### Fixed
- Bug when exporting duplicates to json file in Windows. (@capink)
- Bug with calibre 2.x failing to import missing class. https://www.mobileread.com/forums/showpost.php?p=4090981&postcount=820

## [1.8.4] - 2021-01-07
### Changed
- Use calibre.library.db for target database instead of the deprecated LibraryDatabase2. (@capink)
- Use db.new_api.get_proxy_metadata to improve performance when using templates in advanced mode.

## [1.8.3] - 2020-10-21
### Changed
- When changing libraries in library compare, restore the last used match rules from previous library if possible (all columns in match rules present in the newly selected library). (@capink)
### Fixed
- Remove invalid locations from saved location list in library compare dialog before restoring.

## [1.8.2] - 2020-10-17
### Changed
- Restore last used match rules (and sort filters). (@capink)
### Fixed
- Allow dialog size to be reduced.

## [1.8.1] - 2020-10-15
### Fixed
- Minor fixes. (@capink)

## [1.8.0] - 2020-10-11
### Changed
- Add advanced mode. It allows the user to match books without restrictions on the type nor the number of columns used. It also allows for user defined algorithms by using templates. It comes with a sort dialog allowing you to sort books based on columns and templates. To complement the sort feature, it adds extra marks to first and last books in each duplicate group: "first_duplicate", "last_duplicate". (@capink)
- Mark records with deleted formats in binary search as "deleted_binary_duplicate"
- Option to export duplicate groups to json file. For advanced mode, the sorting of books is retained in the json file.
- Update Spanish translation. Thanks to @dunhill.
- Code refactoring.
- Calibre minimum version bumped to 2.0.0
- Schema version bumped to 1.6
### Fixed
- Mark exemptions only when showing them and remove the marks afterwards.
- Restore state if the user exits calibre with the duplicates restriction still on. Thanks to @chaley
- Remember last sort in library view and revert back to it.

## [1.7.2] - 2020-06-25
### Fixed
- A couple of errors with translations. (@davidfor)

## [1.7.0] - 2020-06-21
### Added
- Make translatable. (@davidfor)
- Add Spanish translation. (@dunhill)
### Changed
- Use delete key to remove entry from library list in cross library search options.
- Changes for Python 3 support in calibre.

## [1.6.3] - 2017-06-12
### Fixed
- Compatibility with Calibre 2.99b11+

## [1.6.1] - 2013-01-03
### Fixed
- For when comparing library duplicates to ensure saved searches are not corrupted.

## [1.6.0] - 2012-10-29
### Added
- Add a context menu to the metadata variations list to allow choosing the selected name on the right side.
### Changed
- Change "ISBN Compare" to "Identifier" with a dropdown allowing comparison of any identifier field.

## [1.5.3] - 2012-08-14
### Changed
- When using "Find library duplicates" display all duplicate matches for the current library as marked:duplicate (except for author duplicates)

## [1.5.2] - 2012-07-21
### Changed
- When using "Find library duplicates" clear the current search in order to compare the entire restricted library
- When using "Find metadata variations" and showing books, fire the search again to ensure results reflect the search

## [1.5.1] - 2012-07-21
### Added
- Add a "Save log" button for the "Find library duplicates" result screen.

## [1.5.0] - 2012-07-20
### Added
- Add a "Find library duplicates" option for cross-library duplicate comparisons into a log report
### Changed
- If currently running a duplicate book search and execute a metadata variation search, clear search first

## [1.4.0] - 2012-07-17
### Added
- Add a Find metadata variations option to search for author, series, publisher and tag variations, and allow renaming them from the dialog.
### Changed
- Now requires calibre 0.8.59
### Fixed
- Fuzzy author comparisons which will no longer compute a reverse hash to reduce the false positives it generated

## [1.3.0] - 2012-06-22
### Added
- Add a support option to the configuration dialog allowing viewing the plugin data stored in the database
- Add an option to allow automatic removal of binary duplicates (does not delete books records, only the newest copies of that format).
### Changed
- Now requires calibre 0.8.57
- Store configuration in the calibre database rather than a json file, to allow reuse from different computers (not simultaneously!)

## [1.2.3] - 2011-12-02
### Changed
- Make the languages comparison optional (default false) via a checkbox on the Find Duplicates dialog

## [1.2.2] - 2011-11-25
### Changed
- Take the languages field into account when doing title based duplicate comparisons

## [1.2.1] - 2011-11-12
### Changed
- When selecting ISBN or Binary compare, hide the Title/Author groupbox options
- Some cosmetic additions to the text for ISBN/Binary options

## [1.2.0] - 2011-09-11
### Changed
- Remove customisation of shortcuts on tab, to use Calibre's centrally managed shortcuts instead.
### Fixed
- For when switching to an ignore title search where author search was previously set to ignore.

## [1.1.4] - 2011-07-04
### Fixed
- Stuff broken by Calibre 0.8.8 in the tag view
- For removing an author exemption

## [1.1.3] - 2011-07-03
### Changed
- Preparation for deprecation of db.format_abspath() for networked backend

## [1.1.2] - 2011-07-03
### Fixed
- Issue with Calibre 0.8.8 tag browser search_restriction refactoring

## [1.1.1] - 2011-06-12
### Changed
- Add van to list of ignored author words
### Fixed
- Error dialog not referenced correctly

## [1.1.0] - 2011-05-03
### Added
- Add support for binary comparison searches to find book formats with exactly the same content
- Disable the Ignore title, identical author combination as will not a valid one (never duplicates)
- Allow the remove, mark current and mark all group exemption dialogs able to be hidden from showing again.
- Allow various count of result and no result information dialogs able to be hidden from showing again.
- Allow user to reset confirmation dialogs related to find duplicates from the configuration dialog
### Changed
- Include swapping author name order in all but identical author checks. So A B / B A or A,B / B,A will match.
- Compare multiple authors for most author algorithms to increase duplicate coverage.
- No longer calculate exemption preview detailed messages for the confirmation dialog for performance
- Replace how exemptions are stored in the config file to make more scalable
- Change Manage exemptions dialog to have tab for each author with exemptions and show section only if have exemptions

## [1.0.0] - 2011-04-26
_Initial release of Find Duplicates plugin_
