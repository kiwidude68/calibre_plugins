# Goodreads Sync Change Log

## [1.16.8] - 2024-06-06
### Fixed
- One last attempt at fixing key_file issues for linux users. (@bernieke)
- Fix libpng warning: icCCP: known incorrect sRGB profile using `magick mogrify *.png`

## [1.16.6] - 2024-05-15
### Fixed
- Use `SSLContext` object to pass `key_file` and `cert_file` to `HTTPSConnection` constructor making the plugin Python 3.12 capable. (@StegSchreck)

## [1.16.5] - 2024-03-17
### Updated
- Spanish translation

## [1.16.4] - 2023-12-21
### Added
- Display specific friendly error message if available rather than generic response when get goodreads errors.
- Russian translation (@craysy)
- Tamil translation (@anishprabu.t)

## [1.16.3] - 2023-04-16
### Fixed
- Remove books from shelf would only remove first book when there are multiple.

## [1.16.2] - 2022-10-19
### Fixed
- Fix regression from 1.16.1 on update reading progress for date related formatting.

## [1.16.1] - 2022-10-18
### Fixed
- Date format on sync from shelf and reading progress dialogs no longer to show time element.

## [1.16.0] - 2022-10-16
_All kiwidude plugins updated/migrated to: https://github.com/kiwidude68/calibre_plugins_
### Added
- Ukranian translation (@yurchor)
### Changed
- **Breaking:** Drop PyQt4 support, require calibre 2.x or later.
- Refactoring of common code
- Removed help file, point to [GitHub Wiki](https://github.com/kiwidude68/calibre_plugins/wiki/Goodreads-Sync)
- Replace Help link on configuration dialog with a button.
- Attempt to give a more helpful message if Goodreads apply an http request limit when using add/remove books.
- Spanish translation (@dunhill)
### Fixed
- Update reading progress should only apply "read" shelf actions when progress >= 100 ([#2][i2])
- Update reading progress should apply "currently-reading" shelf actions when progress < 100 ([#2][i2])
- Disable the rating/review/date-read checkboxes on the 'currently-reading' shelf. The 'read' shelf actions are used for these instead when you finish a book for reading progress purposes.
- Various other bugs related to the "Update reading progress" feature.
- Deleting menu rows could have wrong selected items. (@capink)

[i2]: https://github.com/kiwidude68/calibre_plugins/issues/2

## [1.15.6] - 2022-08-15
### Fixed
- Error in previous version meant some menu items were not enabled on the "Sync from Goodreads shelf" dialog.

## [1.15.5] - 2022-08-11
### Fixed
- Calibre v6/Qt6 - Drag-and-drop to "Link Goodreads" and "Switch" dialog.
- Calibre v6/Qt6 - Fix selection issues as Qt6 allows deleselecting all entries in the lists.

## [1.15.4] - 2022-07-13
### Fixed
- Calibre v6/Qt6 - Fix date handling in dialogs.

## [1.15.3] - 2022-07-12
### Changed
- Updates for calibre v6/Qt6

## [1.15.2] - 2021-06-11
### Changed
- Allow the list of actions to stretch when the height of the Sync from shelf dialog is changed. (@davidfor)

## [1.15.1] - 2021-03-19
- Sync 100 books per shelf as with 200 it just keeps going.  (@davidfor)

## [1.15.0] - 2020-12-26
### Added
- Added the option "Put books on currently-reading shelf" to the "Update reading progress" dialog.  (@davidfor)
### Fixed
- Progress bar when syncing shelves and updating the library should have been "Books". 
- Errors handling books when updating calibre after a "Sync from shelf". This gave terrible performance and some books would not have been updated correctly. 
- Python 3 incompatibility when opening help. 
- Python 3 incompatibility when opening Goodreads page from dialogs. 
- Python 3 incompatibility when handling from Goodreads. 

## [1.14.3] - 2020-06-30
### Fixed
- Remove a version check in the Oauth2 library. This was lost when the library was updated. This will allow the calibre 3.x versions to use the plugin. (@davidfor)

## [1.14.2] - 2020-02-12
### Fixed
- Decode result from parse_qsl for Python 3. (@davidfor)

## [1.14.1] - 2020-02-03
### Changed
- Missed some strings for translations. (@davidfor)
- Spanish translation (@dunhill)
 
## [1.14.0] - 2020-01-28
### Added
- Make translatable. (@davidfor)
- Spanish translation (@dunhill)
### Changed
- Changes for Python 3 support in calibre.

## [1.13.0] - 2020-01-02
### Added
- Use dropdown for editing tag-like columns when editing shelf add and sync actions. (@davidfor)
- Added progress bars for most actions
### Changed
- Match a change in calibre related to "RECOVER_PARSER".
### Fixed
- Set a default width for the title column in all dialogs.
- Tags in sync/add actions should be comma separated.

## [1.12.1] - 2018-10-04
### Fixed
- Remove load of unneeded import of pin_columns and add pin_view attribute as needed. (@davidfor)

## [1.12.0] - 2018-04-17
### Fixed
- Errors when the series index was not just a number. (@davidfor)
- Edit the rating in the Sync Progress dialog gives an error and the drop down appears in the wrong place.
- Use local timezone when displaying the date read.

## [1.11.0] - 2017-12-20
### Changed
- Change to only use HTTPS due to site changes. (@davidfor)
- Update httplib2 to latest version.

## [1.10.1] - 2017-01-05
### Fixed
- Remove debugging line mistakenly left in. (@davidfor)

## [1.10.0] - 2016-12-30
### Added
- Add option not to display the "View shelf" menu. Causes problems if lots of shelves. (@davidfor)
### Changed
- Encode the URL before opening it.
- Disable sorting on lists when updating values.
- Rating display after change in calibre 2.67

## [1.9.0] - 2016-03-14
### Added
- Add sorting for most of the dialogs. (@davidfor)
- Add option to put finished books on the read shelf from the update progress dialog
### Changed
- Limit comment text to 420 characters when updating the reading progress.
- Don't use the review column for the reading progress comment.

## [1.8.0] - 2015-11-11
### Added
- Add support for proxies. (@davidfor)
### Changed
- Add detail to error message when searching for editions.

## [1.7.7] - 2015-01-11
### Fixed
- Drag/drop into the Goodreads dialog due to change to use of HTTPS url

## [1.7.6] - 2014-12-15
### Changed
- Improved dynamic menu support in line with calibre changes

## [1.7.5] - 2014-08-23
### Fixed
- For changes to support calibre 2.0

## [1.7.4] - 2014-08-12
### Changed
- Support for upcoming calibre 2.0

## [1.7.3] - 2013-11-11
### Fixed
- Drag/drop into the Goodreads dialog due to change to use of HTTPS url

## [1.7.2] - 2013-08-24
### Fixed
- Replace some incorrect legacy code that was looking up the old ISBN field in the database instead of identifiers.
- When Goodreads error is thrown during Add to Shelf to ensure a second error is not displayed to user.

## [1.7.1] - 2012-06-05
### Fixed
- Switching editions throwing error caused by changes in 1.7.0

## [1.7.0] - 2012-06-02
### Added
- Allow synchronising review text to/from goodreads
### Changed
- Change the date handling to (hopefully) correctly handle timezones for issues some users experienced
- Adjust some dialog layouts to ensure buttons are sized better with different styles applied
- Minor performance enhancement for when syncing books from large shelves
- Enable gzip compression for oauth calls to see if improves performance

## [1.6.7] - 2012-05-12
### Fixed
- For book titles containing apostrophes for when searching to link books

## [1.6.6] - 2012-05-03
### Fixed
- Bug when error dialog is to be displayed about missing a custom column

## [1.6.5] - 2012-04-20
### Changed
- Change the url for authentication to not have a trailing slash as recent Goodreads release broke this.
- Add protection for blank author from bug in calibre
### Fixed
- When get an error during authentication, do not throw a misleading second error.

## [1.6.4] - 2012-02-14
### Changed
- For the switch edition feature, ensure that variations of ISBN scraped from web page are handled better
- On Add to shelf dialog, make the Add to shelf button a default one so can just hit enter

## [1.6.3] - 2012-02-12
### Added
- Add a Switch edition dialog for a linked book to allow picking another edition for page count/cover purposes
- Also allow access to the switch edition dialog from the linked book screen.

## [1.6.2] - 2011-12-30
### Fixed
- For missing config value for users upgrading to 1.6 then using sync without configuring shelf first.

## [1.6.1] - 2011-12-21
### Fixed
- For the Download shelves as tags feature, broken in 1.6.0

## [1.6.0] - 2011-12-20
### Changed
- Adding to/removing from shelves changes:
    - support add/remove to multiple shelves (remembers last choice)
    - support uploading your calibre rating and/or date read custom column
    - support performing other actions when adding to shelf such as setting custom column values
- Syncing from shelves changes:
    - support syncing from multiple shelves (intermediate dialog that remembers last choice)
    - support syncing your Goodreads rating and/or date read to custom columns
    - dialog now shows what actions will be applied/columns updated for selected shelves
- Configuration dialogs reworked:
    - tag mappings now edited directly in the shelves grid
    - support multi-select to allow specifying sync rules for multiple shelves at once
    - support configuring actions to take place when adding books to a shelf
    - support uploading rating & date read to goodreads on a per shelf basis
    - support syncing rating & date read from goodreads on a per shelf basis
    - support specifying which columns to sync to for tags, date read and ratings
    - support options for hiding Add to shelf and Sync from shelf menus
    - drop the restriction allowing only one action for a specific column (to allow people to do add/remove tags in a single sync action)
- Menus reworked:
    - add/remove shelf no longer has a shelves submenu forcing a single shelf. Can choose multiple shelves on the new dialog.
    - sync from shelf no longer has a shelves submenu forcing a single shelf. Intermediate dialog to choose instead.
- Change the configuration file to store the tag mappings in the shelves data, and tag mapping column no longer per user
- When matching against a calibre book from the sync dialog, exclude trailing punctuation from title/author
- Add tooltips to the add shelf dialog
- When a Goodreads error occurs, include the xml error response in the error dialog as has reason for error
- Upgrade oauth2 to v1.5.210 and httplib2 to v0.7.2
- Remove support for users upgrading from versions prior to 1.1

## [1.5.2] - 2011-11-02
### Fixed
- For updating boolean columns to use prefs rather than tweaks since changed in Calibre 0.7.55

## [1.5.1] - 2011-09-19
### Fixed
- In new menu building code for when a user has multiple Goodreads user accounts setup.

## [1.5.0] - 2011-09-17
### Changed
- Upgrade to support the centralised keyboard shortcut management in Calibre

## [1.4.15] - 2011-07-11
### Changed
- Ensure the book details pane is updated after adding a Goodreads link to the selected book
### Fixed
- Fix bug of DEBUG not available when error thrown

## [1.4.14] - 2011-06-17
### Added
- Allow enumerated text columns for sync action columns
### Changed
- Ensure the book details pane is updated after removing a Goodreads link to the selected book

## [1.4.13] - 2011-06-02
### Changed
- Upgrade the oauth2 library to 1.5.170
- Ensure the book details pane is updated after shelf changes or linking books

## [1.4.12] - 2011-05-17
### Fixed
- Bug of removing from id cache error when does not exist in cache

## [1.4.11] - 2011-05-09
### Changed
- Do not try to write null ISBN to database after performing a sync

## [1.4.10] - 02011-05-08
### Changed
- Change all webbrowser launching to use Calibre's wrapper for the default browser for better Linux support

## [1.4.9] - 2011-05-07
### Fixed
- For no ISBN causing errors when adding to shelf

## [1.4.8] - 2011-05-04
### Changed
- Remove the add shelves button from the edit shelf tag mappings dialog. Always display all your shelves.
- When adding a shelf to the mapping list, default it to having no Calibre tags instead of a tag of the shelf name.
### Fixed
- For correct error dialog not showing when have an error during Goodreads communication.

## [1.4.7] - 2011-04-23
### Changed
- Force the Goodreads/Calibre id caches to be updated more frequently.

## [1.4.6] - 2011-04-13
### Changed
- Change the URL searched against as Goodreads have changed their website.

## [1.4.5] - 2011-04-09
### Changed
- Support skinning of icons by putting them in a plugin name subfolder of local resources/images

## [1.4.4] - 2011-04-08
### Changed
- Change the Download shelves as tags behaviour so that if the target is a custom column it always overwrites

## [1.4.3] - 2011-04-07
### Added
- Add a Paste Goodreads.com right-click option (ctrl+V) to Pick Goodreads book dialog as alternative for Opera users to drag/drop

## [1.4.2] - 2011-04-07
### Fixed
- For URL not defined

## [1.4.1] - 2011-04-04
### Fixed
- For moved functions not declared properly reported by kenr276
- For settings not saving when ok in preferences
- For edit shelf/tag mappings after switching libraries where col does not exist

## [1.4.0] - 2011-04-03
### Changed
- Rewritten for new plugin infrastructure in Calibre 0.7.53

## [1.3.2] - 2011-03-23
### Added
- Allow upload tags for a book that is not on your exclusive shelves

## [1.3.1] - 2011-03-23
### Fixed
- For selected_goodreads_id function rename

## [1.3.0] - 2011-03-23
### Added
- Add "Upload tags to shelves" feature, as a mirror to the "Download tags from shelves"

## [1.2.0] - 2011-03-16
### Added
- Allow Download tags from shelves to be targeted at a custom column, not just tags.
### Fixed
- For drag/drop where url had '-' instead of '.' separator

## [1.1.1] - 2011-03-09
### Fixed
- For download shelves as tags

## [1.1.0] - 2011-03-09
### Added
- Add menu/config options to download tags from shelves
- Add option to create new shelves
- Add option to edit shelves on Goodreads from config dialog
- Add warning when removing from exclusive shelves
### Changed
- Migrate Goodreads Id to Identifiers
- Remove restriction on #shelves downloaded.
### Fixed
- For no Goodreads book selected when linking
- For book showing as linked after deleted
- For no isbn giving NoneType error
- For trailing whitespace title

## [1.0.0] - 2011-02-27
_Initial release of Goodreads Sync plugin_
