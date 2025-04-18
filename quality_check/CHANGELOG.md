# Quality Check Change Log

## [1.14.2] - 2025-04-18
### Changed
- The 'Swap author names' fix now applies a consistent swap when multiple author names.

## [1.14.1] - 2025-03-24
### Changed
- The non DC: metadata check now ignores the mandatory epub3 `dcterms:modified` meta element.

## [1.14.0] - 2025-01-25
### Added
- Added a 'Fix title sort' option for users as an alternative to the bulk metadata edit dialog.

## [1.13.16] - 2024-11-09
### Added
- Cover search dialog now allows searching for books with covers based on their aspect ratios.

## [1.13.15] - 2024-08-05
### Added
- Display the count of matches in a book when finding all occurrences using 'Search ePubs'.

## [1.13.14] - 2024-08-05
### Added
- Added a 'Suppress Fix summary dialogs' option to prevent a summary dialog showing the success/failure of the operation.
### Fixed
- Some of the icon sizes in the Configure dialog had larger icons.

## [1.13.13] - 2024-08-02
### Fixed
- The 'Check unused image files' feature for ePUB now also checks inline style elements.

## [1.13.12] - 2024-07-07
### Fixed
- The 'Check unused image files' feature for ePUB now includes CSS files and OPF files.

## [1.13.11] - 2024-06-29
### Fixed
- The 'Check missing EBOK cdetype' feature for MOBI not correctly identifying EBOK.

## [1.13.10] - 2024-03-23
### Fixed
- The 'Check corrupt zip' feature included some false-positives (#un-pogaz)
- Fix libpng warning: icCCP: known incorrect sRGB profile using `magick mogrify *.png`

## [1.13.9] - 2024-03-17
### Changed
- The 'Check corrupt zip' feature also considers individual file corruption issues (#un-pogaz)
- Updated Spanish and Tamil translations

## [1.13.8] - 2024-01-25
### Added
- New 'Check corrupt zip' feature looks for non-standard zip files (conversion may fix) ([#49][i49])
- Tamil translation (anishprabu.t)

[i49]: https://github.com/kiwidude68/calibre_plugins/issues/49

## [1.13.7] - 2023-09-12
### Added
- Search epub dialog now has a clear history button to remove all previous searches.
### Changed
- Search epub dialog now has a fixed width to prevent long searches over-sizing the dialog. ([#36][i36])

[i36]: https://github.com/kiwidude68/calibre_plugins/issues/36

## [1.13.6] - 2023-08-06
### Added
- New 'Check ePub inside' ePub feature (@un-pogaz)

## [1.13.5] - 2023-08-06
### Added
- Latvian translation (ciepina)
- Russian translation (ashed)
### Fixed
- Truncate long book titles in progress dialog to ensure does not get oversized. (ownedbycats)

## [1.13.4] - 2023-04-02
### Fixed
- EPubCheck had typo when trying to log out missing book format (isarl)

## [1.13.3] - 2022-11-26
### Fixed
- Polish translation missing special substitution character for Fix Asin

## [1.13.2] - 2022-11-09
### Fixed
- Smarten punctuation now only checks files in the spine, ensuring excludes nav.xhtml

## [1.13.1] - 2022-11-06
### Added
- Polish translation (silatiw)
### Fixed
- Translated cover checks not working. (silatiw)

## [1.13.0] - 2022-10-16
_All kiwidude plugins updated/migrated to: https://github.com/kiwidude68/calibre_plugins_
### Added
- Added Help button to configuration dialog.
- Ukranian translation (@yurchor)
### Changed
- **Breaking:** Drop PyQt4 support.
- Refactoring of common code
- Removed help file, point to [GitHub Wiki](https://github.com/kiwidude68/calibre_plugins/wiki/Quality-Check)

## [1.12.0] - 2022-01-19
### Changed
- Changes needed for calibre 6

## [1.11.4] - 2021-09-27
### Fixed
- Exception in "Fix book paths".
- The search term "marked:" being translated when it shouldn't.

## [1.11.2] - 2021-03-17
### Fixed
- Extraneous missing AZW3 errors in log for "Check Twitter/Facebook Disabled"

## [1.11.1] - 2021-01-03
### Fixed
- Fix for "Check and repair book sizes"

## [1.11.0] - 2020-12-15
### Added
- Support for translations
- Spanish translation (@dunhill)

## [1.10.1] - 2020-07-16
### Changed
- Support for upcoming calibre 5 (Python 3 support)

## [1.9.11] - 2014-07-28
### Changed
- Support for upcoming calibre 2.0

## [1.9.9] - 2014-01-05
### Changed
- Make Series Gaps report case insensitive
- Do not include Series with no gaps in the report
- When changing configuration preferences, preserve the search scope

## [1.9.8] - 2013-09-28
### Fixed
- For the "Check and rename book paths" function with changes to calibre in 1.x.

## [1.9.7] - 2013-09-24
### Fixed
- For the "Check and repair book sizes" function with changes to calibre in 1.x.

## [1.9.6] - 2013-05-09
### Changed
- Change for correct support of calibre 0.9.29 virtual libraries feature

## [1.9.5] - 2013-03-04
### Changed
- When using the "Fix ASIN for Kindle Fire" feature, check for mobi-asin as a possible identifier prefix

## [1.9.4] - 2013-02-15
### Changed
- Display how many matches while running, and when cancelling display the matches found at that point rather than aborting completely.
### Fixed
- For dependency on calibre code removed in 0.9.19

## [1.9.3] - 2012-07-17
### Added
- In the config screen put a separate option groupbox in for the author initials setting
- Add a "Reformat author initials" option to the "Fix" menu to reformat initials to your preference for authors on the selected books
- Add a "Rename author to ascii" option to the "Fix" menu to rename author names to remove diacritics and accents
- For "Check author initials" support more permutations of special cases to include trailing period - i.e. Jr. as well as Jr
### Changed
- Tidy up the help file for some redundant/missing/renamed menu items
- Enhance the "Repeat last action" tooltip to display what that last action was (in status bar)

## [1.9.2] - 2012-07-06
### Added
- Add a "Check authors non alphabetic" option to Check ePub Metadata menu to find authors with invalid separators or other cruft
- Add a "Check authors non ascii" option to Check ePub Metadata menu to find authors with accents/diacritics in their names
- Add a "Check authors initials" option to Check ePub Metadata menu to find authors with initials that do not match your preferred style.
- Add to plugin configuration screen an author initials dropdown for configuring preferred author initials format
- Add a "Check smarten punctuation" option to Check ePub Style menu to search for ePubs with `"` or `'` in body
- Add a "Show all occurrences" option to "Search ePub" as a slower running alternative to just displaying the first match
- Add a "Plain text content" option to "Search ePub" to search html body content for sentences without any tags
### Changed
- Now requires calibre 0.8.59
- In the log for "Search ePub" display the preceding and following 25 characters around the match in the log
- Change the log viewer to a custom implementation that preserves formatting rather than calibre's `<pre>` approach.
- Change to use a new calibre API function for "Check & fix file size" rather than direct database manipulation
### Fixed
- For "Search ePub" to not allow user to search if they have no scope checkboxes set
- For "Check javascript" to display marked:epub_javascript in the search bar
- For "Check epub css margins" feature to fix various bugs and updates to match the latest Modify ePub v1.2.8 release
- "Check Adobe inline .xpgt links" to also look for @import style statements
- "Check manifest files missing" to correctly handle nested relative paths

## [1.9.1] 2012-06-23
### Fixed
- Bug for check tags count.

## [1.9.0] - 2012-06-22
### Changed
- Now requires calibre 0.8.57
- Store configuration in the calibre database rather than a json file, to allow reuse from different computers (not simultaneously!)
- Change all the "Check Mobi" checks to now work with MOBI, AZW or AZW3 formats
- Rename "Fix MOBI ASIN for Kindle Fire" to "Fix ASIN for Kindle Fire"
- Enhance "Fix MOBI ASIN for Kindle Fire" to now handles MOBI, AZW and AZW3 formats, iterating all if multiple for a book
### Fixed
- Fix bug which intimated it was possible to exclude books from "Check missing" type checks
- Add a support option to the configuration dialog allowing viewing the plugin data stored in the database
- Fix "Fix ASIN for Kindle Fire" so in scenario of not having an ASIN uses calibre's uuid for the book rather than generating a random one

## [1.8.5] - 2012-06-09
### Added
- Add a "Check calibre SVG cover" and "Check no calibre SVG cover" options to Check ePub Structure menu
- Add a "Zip filenames" scope to the "Search ePub" dialog to allow searching for files of a specific name
- Add a "Check javascript &lt;script&gt;" to Check ePub Style menu
- Add a "Check Twitter/Facebook disabled" option to Check Mobi menu to look for an equal ASIN in EXTH 113/504
- Add a "Fix MOBI ASIN for Kindle Fire" option to the "Fix" menu to set the EXTH 113/504 fields to your ASIN/amazon identifier, or a random identifier if not present, plus set cdetype to EBOK
### Changed
- Rename the various epub "TOC" checks to include the word "NCX" to reflect that TOC they refer to
### Fixed
- Ensure the various NCX TOC checks do not attempt to run on DRM encrypted books
- Do not show error message if unable to parse metadata/ncx files due to incorrect encoding
- Fix bug in "Check Adobe inline .xpgt links" due to ordering of attributes dependency

## [1.8.4] - 2012-05-20
### Changed
- Subtle enhancements to increase performance of a few checks to not scan irrelevant files.
- Put an icon next to the Search scope submenu to show what scope is currently selected.

## [1.8.3] - 2012-05-17
### Added
- Add a "Check unused CSS files" option to find .css or .xpgt files that are in the manifest but not referenced from html pages
- Add a "Check &lt;guide&gt; broken links" option to find entries in the guide section of the manifest file which do not exist
### Fixed
- For numerous checks to ensure uppercase file extensions in epub resources are handled correctly

## [1.8.2] - 2012-05-16
### Added
- Add a "Check clipping limit" option to the Check Mobi menu for files that are limited in the % of book that can be clipped on a Kindle
### Changed
- Change the handling of exclusions to ensure that ordering of the books is preserved
### Fixed
- Some casing of various menu items for consistency
- For "Check unused image files" to include svg and bmp files as a possible image type

## [1.8.1] - 2012-05-14
### Added
- Add "Check replaceable cover" and "Check non-replaceable cover" checks to indicate whether a cover can be replaced when exported/using Modify ePub to update metadata
### Changed
- Remove the "Check inline Calibre cover" and "Check not inline Calibre cover" checks since replaceable cover checks are more useful
- Improve the exception messages for invalid epubs to include the reason

## [1.8.0] - 2012-05-12
### Added
- Add a "Search ePub" dialog allowing the user to perform a search for any content matching a regular expression
- Add a "Check Mobi" submenu with "Check missing EBOK cdetype" and "Check missing ASIN" options
- Add a "Check broken image links" option to the Check ePub Structure menu, to find epubs with html pages that have broken image links
- Add a "Check TOC with broken links" option to the Check ePub Structure menu, to find epubs with NCX links to pages that do not exist
### Fixed
- Cosmetic issue of marked text incorrect for search results of "Check inline xpgt" links

## [1.7.8] - 2012-05-07
### Added
- Add a "Search scope" submenu to allow searching selected books rather than all books.
### Changed
- Change Check unused image files to look for both encoded and non encoded versions of the image names and ignore DRM ebooks

## [1.7.7] - 2012-05-07
### Fixed
- Yet another tweak to Check unused image files to cope with characters like commas

## [1.7.6] - 2012-05-07
### Fixed
- The spaces encoding when using Check unused image files

## [1.7.5] - 2012-05-05
### Changed
- Ensure a better error is displayed for books where the EPUB format has been deleted outside of calibre
### Fixed
- For Check unused image files to look for spaces in the file name, and handle namespaced images

## [1.7.4] - 2012-05-04
### Added
- Split the Check ePub submenu into two submenus for ease of usage and future expansion
- Add a "Check unused image files" option to the Check ePub Structure menu, to find books with jpeg/png image files that are not referenced and can be removed to save space
- Add a "Check TOC hierarchical" option to the Check ePub Structure menu, to find books with hierarchical TOC that need flattening for certain devices
- Add a "Check Adobe DRM meta tag" option to the Check ePub Structure menu, to find books with html files that contain Adobe `<meta />` DRM identifiers
- Add a "Check Adobe inline .xpgt links" option to the Check ePub Style menu, to find books with html files that `<link />` to a .xpgt file
- Add a "Check @font-face" option to the Check ePub Style menu, to find books with CSS or html files that contain `@font-face` declarations
- Add more information into the Help file for newcomers explaining some of the options.
### Fixed
- Protect against a blank author field caused by a bug in the Manage Authors dialog in calibre

## [1.7.3] - 2012-04-09
### Added
- Add a "Check series pubdate order" menu option, which will report series where the published date is not in order with the series.
- Add a "Check authors for case" option to look for author names that are all uppercase or lowercase
- Add a "Check missing" submenu, with options to perform searches for books missing title, authors, isbn, pubdate, publisher, tags, rating, comments, languages, cover, formats
### Changed
- Rename "Check titlecase" to "Check title for titlecase"

## [1.7.2] - 2012-02-13
### Added
- Add a "Check and rename book paths" menu option to the Fix submenu, for consolidating author paths after commas change made in calibre 0.8.35.
### Fixed
- Icons broken from 1.7.1 change on new Fix menu

## [1.7.1] - 2012-02-04
### Added
- Add a "Fix..." menu moving the Check & fix file sizes and Cleanup OPF folders options into.
- Add a "Swap author FN LN <-> LN,FN" menu item for working with selected book(s)
### Changed
- Change the "Check authors with commas" check so requires only one of a multi-author book to have commas

## [1.7.0] - 2011-12-03
### Added
- Move all the metadata based checks under a submenu, and reorder menus
- Add a "Repeat last check" menu item to allow simply running the last check again
- Add "Exclude from check..." menu item, to allow excluding books from repeatedly showing you want exempt
- Add "View exclusions..." menu item, to allow viewing all excluded books per check and deleting if desired.
### Changed
- Remove configuration of the Author commas/no commas and titles with series menu items
### Fixed
- Fix missing images from menu for CSS based items

## [1.6.4] - 2011-11-25
### Changed
- When performing a title sort, take the first ebook language into account if any
- When checking for TOC < 3 items, display the title and authors rather than the path

## [1.6.3] - 2011-10-22
### Added
- Add ePub checks for various types of `body` and `@page` margins (Idolse)
- Add ePub check for having `<address>` smart-tags within their content
### Fixed
- For the Series gap check, fix the handling of duplicates

## [1.6.2] - 2011-09-19
### Changed
- Tune the check for series with gaps to exclude series with indexes >= 1000 and handle duplicates

## [1.6.1] - 2011-09-17
### Added
- Add check for series with gaps (checks missing integer values between 1 and max in series)

## [1.6.0] - 2011-09-11
### Changed
- Upgrade to support the centralised keyboard shortcut management in Calibre

## [1.5.8] - 2011-06-13
### Changed
- Ensure search restrictions are respected after change in 1.5.7

## [1.5.7] - 2011-06-12
### Added
- Add ePub check for css missing `text-align: justify`
### Changed
- Change the ePub zero margin check to only look at manifested APNX files
### Fixed
- Change way books are searched for so if highlighting is turned on correct subset is searched

## [1.5.6] - 2011-06-08
### Changed
- No longer look in manifest for NCX file, look for physical file instead to get around media-type variant issues

## [1.5.5] - 2011-06-08
### Changed
- Improve the logging for the ePub TOC check to display when no NCX found
- Be more flexible when identifying NCX file to allow for incorrect media type

## [1.5.4] - 2011-06-05
### Added
- Add ePub check for iTunesArtwork to the existing iTunes check
- Add ePub check for OS artifacts of .DS_Store and Thumbs.db
- Add ePub check for non dc elements in opf manifest (from editing in Sigil or Calibre)
- Add ePub check for html files larger than 260KB which may not work on some devices
### Changed
- Increase the amount and formatting quality of the logging for more ePub checks
### Fixed
- Check for missing manifest files to fix for href names containing # in filenames

## [1.5.3] - 2011-05-25
### Added
- Add ePub check for invalid namespaces
- Add a viewable log for the checks to allow user to see details of errors, missing files etc
- Add a Help file describing all of the checks and how to solve them

## [1.5.2] - 2011-05-17
### Changed
- Rename Abort to Cancel on the progress dialog
### Fixed
- Prevent ePubs with encrypted fonts from showing as being books with DRM

## [1.5.1] - 2011-05-16
### Added
- Quality checks are run with a progress dialog that can be aborted
- Add ePub check for embedded fonts in an ePub
- Add check for pubdate, testing for equality with date timestamp
- Add ePub check for DRM
### Changed
- The ePub check for unmanifested files to exclude iTunes plist and Calibre bookmark files

## [1.5.0] - 2011-05-05
### Added
- Move all the ePub checks onto a Check ePub submenu
- Add ePub check for legacy jackets only
- Add ePub check for missing container.xml files
- Add ePub check for files listed in manifest missing from epub
- Add ePub check for unmanifested files
- Add ePub check for iTunes plist files
- Add ePub check for Calibre bookmarks files
- Add ePub check for .xpgt margins
- Add ePub check for TOC with < 3 entries
- Add ePub check for inline Calibre cover
- Add ePub check for no inline Calibre cover
- Add ePub check for Calibre conversion
- Add ePub check for not Calibre converted
- Add check for duplicate series index
### Changed
- Improve having jacket and multiple jacket checks to include legacy jackets
- Restructure code internally for ease of future expansion

## [1.4.1] - 2011-04-13
### Added
- Add check for multiple jackets
### Fixed
- Check for missing jacket which would incorrectly handle books with two jackets

## [1.4.0] - 2011-04-13
### Added
- Add ability to customise the menu to allowing hiding menu items not of interest
### Changed
- If an error retrieving the format path for a book, dump to debug output
- For the EPUB jackets check, look for numbered jacket files from legacy Calibre conversions
### Fixed
- For very small libraries ensure not divide by zero error from displaying status
- Bug in check no html comments which had incorrect logic after 1.3 rewrite

## [1.3.5] - 2011-04-11
### Added
- Add check duplicate ISBN option

## [1.3.4] - 2011-04-10
### Fixed
- Error dialog bug when try to cleanup opf files in own Calibre directory

## [1.3.3] - 2011-04-09
### Added
- Support skinning of icons by putting them in a plugin name subfolder of local resources/images

## [1.3.2] - 2011-04-06
### Fixed
- Int is not iterable error when no matches found in check and update file sizes

## [1.3.1] - 2011-04-5
### Added
- Add check title case option
### Fixed
- Bug in Check & fix file sizes from rewrite

## [1.3.0] - 2011-04-03
### Added
- Add check for EPUB with/without jacket
- Add cleanup opf folders option to cleanup after save to disk/remove actions leaving orphaned files
### Changed
- Rewritten for new plugin infrastructure in Calibre 0.7.53

## [1.2.0] - 2011-03-28
### Added
- Add check & fix file format size

## [1.1.0] - 2011-03-20
### Added
- Add check for no html in comments
- Add check for authors with/without commas
- Add check for titles with series

## [1.0.0] - 2011-03-13
_Initial release of Quality Check plugin_
