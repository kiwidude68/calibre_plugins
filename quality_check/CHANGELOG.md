## Release History

**Version 1.13.0** - XX Sep 2022
- New: All kiwidude plugins updated/migrated to: https://github.com/kiwidude68/calibre_plugins
- Update: Drop PyQt4 support.
- Update: Refactoring of common code

**Version 1.12.0** - 19 Jan 2022
- Update: Changes needed for calibre 6

**Version 1.11.4** - 27 Sep 2021
- Fix: Exception in "Fix book paths".
- Fix: The search term "marked:" being translated when it shouldn't.

**Version 1.11.2** - 17 Mar 2021
- Fix: Extraneous missing AZW3 errors in log for "Check Twitter/Facebook Disabled"

**Version 1.11.1** - 3 Jan 2021
- Fix "Check and repair book sizes"

**Version 1.11.0 **- 15 Dec 2020
- New: Support for translations, + Spanish translation. Thanks to @dunhill for the changes.

**Version 1.10.1** - 16 Jul 2020
- Update: Support for upcoming calibre 5 (Python 3 support)

**Version 1.9.11** - 28 Jul 2014
- Update: Support for upcoming calibre 2.0

**Version 1.9.9** - 05 Jan 2014
- Update: Make Series Gaps report case insensitive
- Update: Do not include Series with no gaps in the report
- Update: When changing configuration preferences, preserve the search scope

**Version 1.9.8** - 28 Sep 2013
- Fix: For the "Check and rename book paths" function with changes to calibre in 1.x.

**Version 1.9.7** - 24 Sep 2013
- Fix: For the "Check and repair book sizes" function with changes to calibre in 1.x.

**Version 1.9.6** - 09 May 2013
- Update: Change for correct support of calibre 0.9.29 virtual libraries feature

**Version 1.9.5** - 04 Mar 2013
- Update: When using the "Fix ASIN for Kindle Fire" feature, check for mobi-asin as a possible identifier prefix

**Version 1.9.4** - 15 Feb 2013
- Update: Display how many matches while running, and when cancelling display the matches found at that point rather than aborting completely.
- Fix: For dependency on calibre code removed in 0.9.19

**Version 1.9.3** - 17 Jul 2012
- New: In the config screen put a separate option groupbox in for the author initials setting
- New: Add a "Reformat author initials" option to the "Fix" menu to reformat initials to your preference for authors on the selected books
- New: Add a "Rename author to ascii" option to the "Fix" menu to rename author names to remove diatrics and accents
- New: For "Check author initials" support more permutations of special cases to include trailing period - i.e. Jr. as well as Jr
- Update: Tidy up the help file for some redundant/missing/renamed menu items
- Update@ Enhance the "Repeat last action" tooltip to display what that last action was (in status bar)

**Version 1.9.2** - 06 Jul 2012
- New: Add a "Check authors non alphabetic" option to Check ePub Metadata menu to find authors with invalid separators or other cruft
- New: Add a "Check authors non ascii" option to Check ePub Metadata menu to find authors with accents/diatrics in their names
- New: Add a "Check authors initials" option to Check ePub Metadata menu to find authors with initials that do not match your preferred style.
- New: Add to plugin configuration screen an author initials dropdown for configuring preferred author initials format
- New: Add a "Check smarten punctuation" option to Check ePub Style menu to search for ePubs with " or ' in body
- New: Add a "Show all occurrences" option to "Search ePub" as a slower running alternative to just displaying the first match
- New: Add a "Plain text content" option to "Search ePub" to search html body content for sentences without any tags
- Update: Now requires calibre 0.8.59
- Update: In the log for "Search ePub" display the preceding and following 25 characters around the match in the log
- Update: Change the log viewer to a custom implementation that preserves formatting rather than calibre's <pre> approach.
- Update: Change to use a new calibre API function for "Check & fix file size" rather than direct database manipulation
- Fix: For "Search ePub" to not allow user to search if they have no scope checkboxes set
- Fix: For "Check javascript" to display marked:epub_javascript in the search bar
- Fix: For "Check epub css margins" feature to fix various bugs and updates to match the latest Modify ePub v1.2.8 release
- Fix: "Check Adobe inline .xpgt links" to also look for @import style statements
- Fix: "Check manifest files missing" to correctly handle nested relative paths

**Version 1.9.1** - 23 Jun 2012
- Fix: Bug for check tags count.

**Version 1.9.0** - 22 Jun 2012
- Update: Now requires calibre 0.8.57
- Update: Store configuration in the calibre database rather than a json file, to allow reuse from different computers (not simultaneously!)
- Update: Change all the "Check Mobi" checks to now work with MOBI, AZW or AZW3 formats
- Update: Rename "Fix MOBI ASIN for Kindle Fire" to "Fix ASIN for Kindle Fire"
- Update: Enhance "Fix MOBI ASIN for Kindle Fire" to now handles MOBI, AZW and AZW3 formats, iterating all if multiple for a book
- Fix bug which intimated it was possible to exclude books from "Check missing" type checks
- Fix: Add a support option to the configuration dialog allowing viewing the plugin data stored in the database
- Fix "Fix ASIN for Kindle Fire" so in scenario of not having an ASIN uses calibre's uuid for the book rather than generating a random one

**Version 1.8.5** - 09 Jun 2012
- New: Add a "Check calibre SVG cover" and "Check no calibre SVG cover" options to Check ePub Structure menu
- New: Add a "Zip filenames" scope to the "Search ePub" dialog to allow searching for files of a specific name
- New: Add a "Check javascript <script>" to Check ePub Style menu
- New: Add a "Check Twitter/Facebook disabled" option to Check Mobi menu to look for an equal ASIN in EXTH 113/504
- New: Add a "Fix MOBI ASIN for Kindle Fire" option to the "Fix" menu to set the EXTH 113/504 fields to your ASIN/amazon identifier, or a random identifier if not present, plus set cdetype to EBOK
- Update: Rename the various epub "TOC" checks to include the word "NCX" to reflect that TOC they refer to
- Fix: Ensure the various NCX TOC checks do not attempt to run on DRM encrypted books
- Fix: Do not show error message if unable to parse metadata/ncx files due to incorrect encoding
- Fix bug in "Check Adobe inline .xpgt links" due to ordering of attributes dependency

**Version 1.8.4** - 20 May 2012
- Update: Subtle enhancements to increase performance of a few checks to not scan irrelevant files.
- Update: Put an icon next to the Search scope submenu to show what scope is currently selected.

**Version 1.8.3** - 17 May 2012
- New: Add a "Check unused CSS files" option to find .css or .xpgt files that are in the manifest but not referenced from html pages
- New: Add a "Check <guide> broken links" option to find entries in the guide section of the manifest file which do not exist
- Fix: For numerous checks to ensure uppercase file extensions in epub resources are handled correctly

**Version 1.8.2** - 16 May 2012
- New: Add a "Check clipping limit" option to the Check Mobi menu for files that are limited in the % of book that can be clipped on a Kindle
- Update: Change the handling of exclusions to ensure that ordering of the books is preserved
- Fix: Some casing of various menu items for consistency
- Fix: For "Check unused image files" to include svg and bmp files as a possible image type

**Version 1.8.1** - 14 May 2012
- New: Add "Check replaceable cover" and "Check non-replaceable cover" checks to indicate whether a cover can be replaced when exported/using Modify ePub to update metadata
- Update: Remove the "Check inline Calibre cover" and "Check not inline Calibre cover" checks since replaceable cover checks are more useful
- Update: Improve the exception messages for invalid epubs to include the reason

**Version 1.8.0** - 12 May 2012
- New: Add a "Search ePub" dialog allowing the user to perform a search for any content matching a regular expression
- New: Add a "Check Mobi" submenu with "Check missing EBOK cdetype" and "Check missing ASIN" options
- New: Add a "Check broken image links" option to the Check ePub Structure menu, to find epubs with html pages that have broken image links
- New: Add a "Check TOC with broken links" option to the Check ePub Structure menu, to find epubs with NCX links to pages that do not exist
- Fix: Cosmetic issue of marked text incorrect for search results of "Check inline xpgt" links

**Version 1.7.8** - 07 May 2012
- New: Add a "Search scope" submenu to allow searching selected books rather than all books.
- Update: Change Check unused image files to look for both encoded and non encoded versions of the image names and ignore DRM ebooks

**Version 1.7.7** - 07 May 2012
- Fix: Yet another tweak to Check unused image files to cope with characters like commas

**Version 1.7.6** - 07 May 2012
- Fix: The spaces encoding when using Check unused image files

**Version 1.7.5** - 05 May 2012
- Update: Ensure a better error is displayed for books where the EPUB format has been deleted outside of calibre
- Fix: For Check unused image files to look for spaces in the file name, and handle namespaced images

**Version 1.7.4** - 04 May 2012
- New: Split the Check ePub submenu into two submenus for ease of usage and future expansion
- New: Add a "Check unused image files" option to the Check ePub Structure menu, to find books with jpeg/png image files that are not referenced and can be removed to save space
- New: Add a "Check TOC hierarchical" option to the Check ePub Structure menu, to find books with hierarchical TOC that need flattening for certain devices
- New: Add a "Check Adobe DRM meta tag" option to the Check ePub Structure menu, to find books with html files that contain Adobe <meta /> DRM identifiers
- New: Add a "Check Adobe inline .xpgt links" option to the Check ePub Style menu, to find books with html files that <link /> to a .xpgt file
- New: Add a "Check @font-face" option to the Check ePub Style menu, to find books with CSS or html files that contain @font-face declarations
- New: Add more information into the Help file for newcomers explaining some of the options.
- Fix: Protect against a blank author field caused by a bug in the Manage Authors dialog in calibre

**Version 1.7.3** - 09 Apr 2012
- New: Add a "Check series pubdate order" menu option, which will report series where the published date is not in order with the series.
- New: Add a "Check authors for case" option to look for author names that are all uppercase or lowercase
- New: Add a "Check missing" submenu, with options to perform searches for books missing title, authors, isbn, pubdate, publisher, tags, rating, comments, languages, cover, formats
- Update: Rename "Check titlecase" to "Check title for titlecase"

**Version 1.7.2** - 13 Feb 2012
- New: Add a "Check and rename book paths" menu option to the Fix submenu, for consolidating author paths after commas change made in calibre 0.8.35.
- Fix icons broken from 1.7.1 change on new Fix menu

**Version 1.7.1** - 04 Feb 2012
- New: Add a "Fix..." menu moving the Check & fix file sizes and Cleanup OPF folders options into.
- New: Add a "Swap author FN LN <-> LN,FN" menu item for working with selected book(s)
- Change the "Check authors with commas" check so requires only one of a multi-author book to have commas

**Version 1.7.0** - 03 Dec 2011
- New: Move all the metadata based checks under a submenu, and reorder menus
- New: Add a "Repeat last check" menu item to allow simply running the last check again
- New: Add "Exclude from check..." menu item, to allow excluding books from repeatedly showing you want exempt
- New: Add "View exclusions..." menu item, to allow viewing all excluded books per check and deleting if desired.
- Fix missing images from menu for CSS based items
- Remove configuration of the Author commas/no commas and titles with series menu items

**Version 1.6.4** - 25 Nov 2011
- When performing a title sort, take the first ebook language into account if any
- When checking for TOC < 3 items, display the title and authors rather than the path

**Version 1.6.3** - 22 Oct 2011
- New: Add ePub checks for various types of body/@page margins (Idolse)
- New: Add ePub check for having <address> smart-tags within their content
- For the Series gap check, fix the handling of duplicates

**Version 1.6.2** - 19 Sep 2011
- Tune the check for series with gaps to exclude series with indexes >= 1000 and handle duplicates

**Version 1.6.1** - 17 Sep 2011
- New: Add check for series with gaps (checks missing integer values between 1 and max in series)

**Version 1.6.0** - 11 Sep 2011
- Update: Upgrade to support the centralised keyboard shortcut management in Calibre

**Version 1.5.8** - 13 Jun 2011
- Update: Ensure search restrictions are respected after change in 1.5.7

**Version 1.5.7** - 12 Jun 2011
- New: Add ePub check for css missing "text-align: justify"
- Update: Change the ePub zero margin check to only look at manifested APNX files
- Fix: Change way books are searched for so if highlighting is turned on correct subset is searched

**Version 1.5.6** - 08 Jun 2011
- Update: No longer look in manifest for NCX file, look for physical file instead to get around media-type variant issues

**Version 1.5.5** - 08 Jun 2011
- Update: Improve the logging for the ePub TOC check to display when no NCX found
- Update: Be more flexible when identifying NCX file to allow for incorrect media type

**Version 1.5.4** - 05 Jun 2011
- New: Add ePub check for iTunesArtwork to the existing iTunes check
- New: Add ePub check for OS artifacts of .DS_Store and Thumbs.db
- New: Add ePub check for non dc elements in opf manifest (from editing in Sigil or Calibre)
- New: Add ePub check for html files larger than 260KB which may not work on some devices
- Update: Increase the amount and formatting quality of the logging for more ePub checks
- Fix: Check for missing manifest files to fix for href names containing # in filenames

**Version 1.5.3** - 25 May 2011
- New: Add ePub check for invalid namespaces
- New: Add a viewable log for the checks to allow user to see details of errors, missing files etc
- New: Add a Help file describing all of the checks and how to solve them

**Version 1.5.2** - 17 May 2011
- Update: Rename Abort to Cancel on the progress dialog
- Fix: Prevent ePubs with encrypted fonts from showing as being books with DRM

**Version 1.5.1** - 16 May 2011
- New: Quality checks are run with a progress dialog that can be aborted
- New: Add ePub check for embedded fonts in an ePub
- New: Add check for pubdate, testing for equality with date timestamp
- New: Add ePub check for DRM
- Update: The ePub check for unmanifested files to exclude iTunes plist and Calibre bookmark files

**Version 1.5** - 05 May 2011
- New: Move all the ePub checks onto a Check ePub submenu
- New: Add ePub check for legacy jackets only
- New: Add ePub check for missing container.xml files
- New: Add ePub check for files listed in manifest missing from epub
- New: Add ePub check for unmanifested files
- New: Add ePub check for iTunes plist files
- New: Add ePub check for Calibre bookmarks files
- New: Add ePub check for .xpgt margins
- New: Add ePub check for TOC with < 3 entries
- New: Add ePub check for inline Calibre cover
- New: Add ePub check for no inline Calibre cover
- New: Add ePub check for Calibre conversion
- New: Add ePub check for not Calibre converted
- New: Add check for duplicate series index
- Update: Improve having jacket and multiple jacket checks to include legacy jackets
- Update: Restructure code internally for ease of future expansion

**Version 1.4.1** - 13 Apr 2011
- New: Add check for multiple jackets
- Fix: Check for missing jacket which would incorrectly handle books with two jackets

**Version 1.4** - 13 Apr 2011
- New: Add ability to customise the menu to allowing hiding menu items not of interest
- Update: If an error retrieving the format path for a book, dump to debug output
- Update: For the EPUB jackets check, look for numbered jacket files from legacy Calibre conversions
- Fix: For very small libraries ensure not divide by zero error from displaying status
- Fix: Bug in check no html comments which had incorrect logic after 1.3 rewrite

**Version 1.3.5** - 11 Apr 2011
- New: Add check duplicate ISBN option

**Version 1.3.4** - 10 Apr 2011
- Fix: Error dialog bug when try to cleanup opf files in own Calibre directory

**Version 1.3.3** - 09 Apr 2011
- New: Support skinning of icons by putting them in a plugin name subfolder of local resources/images

**Version 1.3.2** - 06 Apr 2011
- Fix: Int is not iterable error when no matches found in check and update file sizes

**Version 1.3.1** - 05 Apr 2011
- New: Add check title case option
- Fix: Bug in Check & fix file sizes from rewrite

**Version 1.3** - 03 Apr 2011
- New: Add check for EPUB with/without jacket
- New: Add cleanup opf folders option to cleanup after save to disk/remove actions leaving orphaned files
- Update: Rewritten for new plugin infrastructure in Calibre 0.7.53

**Version 1.2** - 28 Mar 2011
- New: Add check & fix file format size

**Version 1.1** - 20 Mar 2011
- New: Add check for no html in comments
- New: Add check for authors with/without commas
- New: Add check for titles with series

**Version 1.0** - 13 Mar 2011
- Initial release of Quality Check plugin
