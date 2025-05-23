# Modify ePub Change Log

## [1.8.6] - 2025-03-24
### Changed
- Change the Remove non-DC metadata to exclude the `dcterms:modified` meta tag property which is mandatory for ePub3.

## [1.8.5] - 2024-09-29
### Changed
- Replaced the Smarten Punctuation implementation with a direct call to the calibre implementation. This might break for older versions of calibre if that function was not present in that version in which case I will need to bump up the minim version for this plugin.

## [1.8.4] - 2024-07-08
### Fixed
- Remove unused images now also checks inline css and opf cover.
- Fix libpng warning: icCCP: known incorrect sRGB profile using `magick mogrify *.png`

## [1.8.3] - 2024-03-17
### Added
- Tamil translation

## [1.8.2] - 2023-10-07
### Added
- Polish, Russian, Turkish translations
### Fixed
- Remove unmanifested files not correctly handling encoded spaces/brackets in names (@val-vin)

## [1.8.1] - 2022-10-31
### Changed
- Inserting jacket at front of book always skips 1 or sometimes 2 pages trying to detect cover/titlepage.

## [1.8.0] - 2022-10-16
_All kiwidude plugins updated/migrated to: https://github.com/kiwidude68/calibre_plugins_
### Added
- Add keyboard shortcuts access and help to configuration dialog.
- Spanish translation (Jellby)
- Ukranian translation (@yurchor)
### Changed
- **Breaking:** Drop PyQt4 support, require calibre 2.85.1 or later.
- Refactoring of common code
- Removed help file, point to [GitHub Wiki](https://github.com/kiwidude68/calibre_plugins/wiki/Modify-ePub)

## [1.7.3m] - 2022-04-25
### Fixed
- Remove some python 3 code inadvertently left in after debugging. (@chaley)

## [1.7.2] - 2022-04-23
### Fixed
- "Remove broken TOC entries in NCX file" on Linux. Improvement of error message when no epubs were changed. (@chaley)

## [1.7.0] - 2022-01-19
### Changed
- Support for calibre 6. (@chaley)

## [1.6.3] - 2021-07-27
### Fixed
- More 'fix exception in rare cases when replacing the cover'. (@chaley)

## [1.6.2] - 2020-12-18
### Fixed
- Exception in rare cases when replacing the cover. (@chaley)

## [1.6.1] - 2020-10-05
### Fixed
- Crash caused by presence of DRM. (@chaley)

## [1.6.0] - 2020-09-30
### Changed
- Make plugin compatible with calibre 5 (Python 3).  (@chaley)

## [1.4.0] - 2019-10-17
### Added
- Added option to only remove pagemaps and related artifacts generated by Google Play, leaving pagemaps from other sources intact. (Note that removing all pagemaps will override this option.)
- Incorporated Terisa de morgan's option to move metadata jackets to the end of the book.
### Changed
- Minor adjustments to the "unpretty" option, including consideration of EPUB3 elements (section/nav) and removal of EMPTY "display: none" elements.
- Incorporated JimmXinu's fix to the list-based file removal logic.
### Fixed
- Expanded .xpgt link removal for better detection.
- Resequenced modules so that deep parsing would not undo "unpretty" function's work.
- Enhanced pagemap removal function to work regardless of the filename.
- Note: Neither pagemap removal routine affects pagelists incorporated into NCX files.

## [1.3.14] - 2017-11-29
### Added
- Added option to remove page-map.xml files.

## [1.3.13] - 2015-07-05
### Added
- Added option to disable the confirmation prompt each time to update the epub. Use at your own risk - if you make simultaneous other changes to the book record they may get lost.
### Fixed
- Cancel on the progress dialog

## [1.3.12] - 2014-10-02
### Changed
- Enhancement to "stripkobo", "stripspans", and "unpretty" options: All three now remove `</br>` and `</hr>` tags and always make BR and HR self-closing elements. (This fixes invalid `</br>` and `</hr>` markup, if such is present.)
- Moved "stripkobo", "stripspans", and "unpretty" into the "Known artifacts" category to balance the dialog box better.
- Added some code to dialogs.py to make the dialog box scrollable on smaller screens.
- Help file filled in how one can detect the need to smarten punctuation (was previously blank.)
### Fixed
- Minor bug in "stripkobo" option that missed some Kobo artifacts inside the HEAD element.
- Minor spacing bugs in "unpretty" option.

## [1.3.11] - 2014-08-13
### Added
- Add an "unpretty" option to de-indent and otherwise reformat HTML elements in markup. This should have no effect on the rendered content; it only cleans the source code up a bit.
- Add a "stripspans" option to allow removal of attributeless `<span>` elements from markup, as well as normalizing empty `<x></x>` elements to the `<x/>` form.
- Add a "stripkobo" option to allow removal of the Kobo-specific code from kepub books, transforming them into standard EPUB books. This does NOT remove Kobo's DRM.
- Note: Both of the above will also completely remove `<a>`, `<b>`, `<i>`, `<u>`, `<big>`, `<small>`, `<em>`, `<span>`, and `<strong>` elements from the markup when those elements have neither attributes nor content.
### Fixed
- "Remove Adobe resource DRM meta tags" option to remove leading spaces and/or newlines, so these meta tags are completely removed instead of leaving blank lines.

## [1.3.10] - 2014-07-28
### Changed
- For Calibre 2.0 compliance.

## [1.3.9] - 2013-09-01
### Fixed
- Users who do not have any Extra CSS in their defaults trying to use the Append Extra CSS option.

## [1.3.8] - 2013-08-30
### Added
- Add a "Append extra CSS" option to allow appending any css style information from Preferences->Common Options->Look & Feel->Extra CSS to each .css file in the ePub.
### Changed
- Respect the tweak "save_original_format_when_polishing" if set to make a .ORIGINAL_EPUB copy of the book before making modifications if no such copy exists.
- After running Modify ePub ensure the book details panel is updated in case an ORIGINAL_EPUB was added
### Fixed
- Encrypted font ePubs being treated as DRM protected preventing Font removal

## [1.3.7] - 2013-02-15
### Fixed
- Dependency on calibre code removed in 0.9.19

## [1.3.6] - 2012-12-09
### Fixed
- For "Rewrite CSS margins" to ensure it only processes manifest xhtml files when replacing inline styles.

## [1.3.5] - 2012-11-22
### Added
- Add a separate `me.py` script to allow Modify ePub to be run from the command line. Unzip it and refer to the script for help on how to use it.
### Changed
- Change to ensure when running via command line the lack of an opf file allows plugin to still run.

## [1.3.4] - 2012-11-16
### Fixed
- For calibre "bug" to ensure that if user has both remove javascript and smarten punctuation checked, that remove javascript runs first which ensures smarten punctuation will actually work correctly for quotes.

## [1.3.3] - 2012-11-08
### Fixed
- For when Update metadata is "not" selected

## [1.3.2] - 2012-11-08
### Fixed
- Regression from last release where only selecting the "Update metadata" option would not apply changes.

## [1.3.1] - 2012-11-06
### Changed
- Ensure than the "Remove non dc: metadata" option will always run after "Update metadata" if both are selected.
- Reorganise some of the layout and groups.

## [1.3.0] - 2012-11-04
### Added
- Add a "Encode HTML in UTF-8" option strip charset meta tags and re-encode in UTF-8 for books that do not display correctly in calibre viewer
### Changed
- Change the UI appearance to look more balanced.

## [1.2.10] - 2012-08-31
### Changed
- Rewrite the playOrder to make sure it is an incremental sequence after actions that delete from the TOC.
- Change indenting from mucking up self-closing tags in NCX.

## [1.2.9] - 2012-07-04
### Changed
- Alter the "Proceed" message text to hopefully make it clearer to new users.
- Change "Rewrite CSS margins" so that if default margins are zero it writes out margin attributes with a value of zero, rather than removing them
- Change "Rewrite CSS margins" so that if default margins are negative then it omits the margin attribute from the style
- Enhance "Rewrite CSS margins" so that if CSS file has no content it is deleted from the epub
- Rename "Rewrite CSS margins" to "Modify @page and body style margins"
### Fixed
- Fix "Rewrite CSS margins" bug where if default margins are set to zero and an epub has margins specified it would error
- Fix "Rewrite CSS margins" bug where if default margins are set to zero it should not add an empty `@page` directive
- "Remove unused images" not detecting svg images in an svg section containing sibling tags
- "Remove Adobe xpgt links" so that it includes removal of links using the `@import` format.

## [1.2.7] - 2012-06-29
### Changed
- When inserting covers, if guide points to a non-existent cover href, make sure the log does not error.
- In the CSS margin updating, if adding page declaration at it to start rather than end of CSS file to workaround Sigil bug

## [1.2.6] - 2012-06-24
### Added
- Add buttons to save and restore the current settings, to allow setting your own easily switched to defaults

## [1.2.5] - 2012-06-15
- When using the Add/replace jacket and Insert/replace cover options together if book has no jacket currently

## [1.2.4] - 2012-06-05
### Added
- Add some non-standard guide types of "coverimagestandard" and "thumbimagestandard" to increase cover replacement coverage
### Changed
- If the guide has incorrect casing of an image href, auto-correct it

## [1.2.3] - 2012-06-05
### Changed
- Further optimise the CSS margins feature to minimise which files get changed

## [1.2.2] - 2012-06-05
### Added
- Add a "Remove inline javascript and files" option to remove any javascript leftover from html conversions
### Fixed
- Fix for CSS margins feature which was not always updating the css file in the epub after resetting margins

## [1.2.1] - 2012-06-01
### Fixed
- Fix for remove Adobe xpgt links so it no longer is dependent on link attribute ordering to find them

## [1.2.0] - 2012-06-01
### Added
- Add a "Insert or replace cover" option to attempt to insert or replace a cover without doing a conversion
- Add a "Remove cover" option to attempt to completely remove an identified cover from the ePub.
- Add protection for numerous options against trying to apply them to a DRM encrypted book
### Changed
- Change to require minimum calibre version 0.8.53 in order to utilise some calibre bug fixes/changes
- Change to calibre API for deprecated dialog in 0.8.49 which caused issues that intermittently crashed calibre on Mac OS
- Rewrite "Removed unused image files" and "Remove broken cover images" features to use lxml rather than regex for better accuracy
- Better handle ebooks where the ncx file is not in same directory as opf manifest
### Fixed
- If user chooses redundant options (e.g. "Remove all jackets" makes "Remove legacy jackets" redundant) do not run the redundant option

## [1.1.7] - 2012-05-17
- Re-release of 1.1.6 to cater for missing file

## [1.1.6] - 2012-05-17
### Added
- Add a "Remove broken cover images" option to remove html pages which contain only an image tag to a broken image.
- Add a "Remove broken TOC entries in NCX" option to remove ncx entries that point to non-existent html pages
### Fixed
- The last_modified column not being updated if multiple books modified
- Remove unused images to include svg and bmp files as possible image extensions

## [1.1.5] - 2012-05-09
### Changed
- When performing any Modify action, update the `last_modified` column in calibre for the book.
### Fixed
- Remove xpgt files and links to remove the xpgt file from the manifest

## [1.1.4] - 2012-05-07
### Changed
- When using the Remove xpgt files and links option, remove trailing whitespace after the removed `<link>`
### Fixed
- When no epubs are modified, ensure the log detail is available to review
- Remove unused images to check encrypted and unencrypted names, skip DRM ebooks

## [1.1.3] - 2012-05-07
### Fixed
- Remove unused images to better handle image paths with other characters like commas

## [1.1.2] - 2012-05-07
### Fixed
- Remove unused images to better handle image paths with spaces

## [1.1.1] - 2012-05-05
### Fixed
- Remove unused images to url encode image paths with spaces in them, and handle namespaced images

## [1.1.0] - 2012-05-05
### Added
- Add a "Remove Adobe .xpgt files and links" option for complete clean xpgt file removal
- Add a "Remove Adobe resource DRM meta tags" option for stripping DRM `<meta>` resource identifiers from xhtml content.
- Add a "Remove unused image files" option to remove orphaned images not referenced from the html content to save space.
- Add a "Flatten TOC hierarchy in NCX file" option to move all the navPoints to a single level if they are nested.
### Changed
- Extend "Remove embedded fonts" to also remove `@font-face` declarations from the CSS and html files
- Move the "Remove margins from Adobe .xpgt files" into a new Adobe section on the UI

## [1.0.2] - 2012-02-12
### Added
- Add ability to smarten punctuation of HTML files

## [1.0.1] - 2011-11-23
### Changed
- When updating metadata, ensure that if calibre has no tags any `dc:subject` elements are removed
- Improve the logging output when removing non dc: metadata elements

## [1.0.0] - 2011-10-22
### Changed
- Preparation for deprecation for `db.format_abspath()` function in future Calibre for network backends
- Merge in remaining CSS/margin changes from Idolse for initial release
- Support keyboard shortcut for opening dialog

## [0.3.5] - 2011-06-26
### Fixed
- Issue with css margin rewriting that used property names using `'_'` instead of `'-'`

## [0.3.4] - 2011-06-21
### Changed
- Remove dependency on the Calibre epub-fix Container class to allow plugin to develop independently
- Incorporate ldolse's rewrite CSS margin code to reset page/body margins
### Fixed
- Issue with some NCX files not parsing correctly causing error with OS artifact removal

## [0.3.1] - 2011-06-12
### Changed
- No longer look in manifest for NCX file, look for physical file instead to get around media-type variant issues
- Additional mime type for xpgt files as supplied by Idolse
### Fixed
- If cancel updating the ePubs, remove the temp directory

## [0.3.0] - 2011-06-06
### Added
- Add ability to remove embedded fonts
- Add ability to update the metadata (including cover)
- Add an error dialog if the user clicks ok with no options selected
### Changed
- Ensure rebuilding the ePub uses the Calibre zip code as per change to Tweak ePub

## [0.2.2] - 2011-06-03
### Added
- Add an option to remove OS artifacts of .DS_Store and thumbs.db files
### Changed
- Treat iTunesArtwork the same as iTunes plist files
- When adding items to manifest, if a `.htm*` file check for xmlns indicating mimetype of `xhtml+xml`
### Fixed
- Ensure that any xml elements inserted in the manifest are "tailed" correctly for indenting

## [0.2.1] - 2011-05-30
### Added
- Ensure Calibre bookmarks and iTunes files are removed from the manifest if present there

## [0.2.0] - 2011-05-30
### Added
- Add option to remove iTunesArtwork files
- Add option to remove non `dc:` metadata elements
- Add option to add/update calibre jackets
### Changed
- Rename Select none to Clear all on dialog

## [0.1.0] - 2011-05-26
_Initial release of Modify ePub plugin_
