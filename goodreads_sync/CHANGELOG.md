## Release History

**Version 1.16.0** - XX Sep 2022
- New: All kiwidude plugins updated/migrated to: https://github.com/kiwidude68/calibre_plugins
- Update: Drop PyQt4 support, require calibre 2.x or later.
- Update: Refactoring of common code

**Version 1.15.6** - 15 Aug 2022
- Fix: Error in previous version meant some menu items were not enabled on the "Sync from Goodreads shelf" dialog.

**Version 1.15.5** - 11 Aug 2022
- Fix: Calibre v6/Qt6 - Drag-and-drop to "Link Goodreads" and "Switchdialog.
- Fix: Calibre v6/Qt6 - Fix selection issues as Qt6 allows deleselecting all entries in the lists.

**Version 1.15.4** - 13 Jul 2022
- Fix: Calibre v6/Qt6 - Fix date handling in dialogs.

**Version 1.15.3** - 12 Jul 2022
- Update: Updates for calibre v6/Qt6

**Version 1.15.2** - 11 Jun 2021 - made by davidfor
- Update: Allow the list of actions to stretch when the height of the Sync from shelf dialog is changed.

**Version 1.15.1** - 19 Mar 2021 - made by davidfor
- Fix: Sync 100 books per shelf as with 200 it just keeps going. 

**Version 1.15.0** - 26 Dec 2020 - made by davidfor
- New: Added the option "Put books on currently-reading shelf" to the "Update Reading Progress". 
- Fix: Progress bar when syncing shelves and updating the library should have been "Books". 
- Fix: Errors handling books when updating calibre after a "Sync from shelf". This gave terrible performance and some books would not have been updated correctly. 
- Fix: Python 3 incompatibility when opening help. 
- Fix: Python 3 incompatibility when opening Goodreads page from dialogs. 
- Fix: Python 3 incompatibility when handling from Goodreads. 

**Version 1.14.3** - 30 Jun 2020 - made by davidfor
- Fix: Remove a version check in the Oauth2 library. This was lost when the library was updated. This will allow the calibre 3.x versions to use the plugin.

**Version 1.14.2** - 12 Feb 2020 - made by davidfor
- Fix: Decode result from parse_qsl for Python 3.

**Version 1.14.1** - 03 Feb 2020 - made by davidfor
- Update: Missed some strings for translations.
- Update: Spanish translation thanks to dunhill.
 
**Version 1.14.0** - 28 Jan 2020 - made by davidfor
- New: Make translatable.
- New: Spanish translation thanks to dunhill.
- Update: Changes for Python 3 support in calibre.

**Version 1.13.0** - 02 Jan 2020 - made by davidfor
- New: Use dropdown for editing tag-like columns when editing shelf add and sync actions.
- New: Added progress bars for most actions
- Update: Match a change in calibre related to "RECOVER_PARSER".
- Fix: Set a default width for the title column in all dialogs.
- Fix: Tags in sync/add actions should be comma separated.

**Version 1.12.1** - 04 Oct 2018 - made by davidfor
- Fix: Remove load of unneeded import of pin_columns and add pin_view attribute as needed.

**Version 1.12.0** - 17 Apr 2018 - made by davidfor
- Fix: Errors when the series index was not just a number.
- Fix: Edit the rating in the Sync Progress dialog gives an error and the drop down appears in the wrong place.
- Fix: Use local timezone when displaying the date read.

**Version 1.11.0** - 20 Dec 2017 - made by davidfor
- Update: Change to only use HTTPS due to site changes.
- Update: Update httplib2 to latest version.

**Version 1.10.1** - 5 Jan 2017 - made by davidfor
- Fix: Remove debugging line mistakenly left in.

**Version 1.10.0** - 30 Dec 2016 - made by davidfor
- New: Add option not to display the "View shelf" menu. Causes problems if lots of shelves.
- Update: Encode the URL before opening it.
- Update: Disable sorting on lists when updating values.
- Fix: Rating display after change in calibre 2.67

**Version 1.9.0** - 14 Mar 2016 - made by davidfor
- New: Add sorting for most of the dialogs
- New: Add option to put finished books on the read shelf from the update progress dialog
- Update: Limit comment text to 420 characters when updating the reading progress.
- Update: Don't use the review column for the reading progress comment.

**Version 1.8.0** - 11 Nov 2015 - made by davidfor
- New: Add support for proxies.
- Update: Add detail to error message when searching for editions.

**Version 1.7.7** - 11 Jan 2015
- Fix: Drag/drop into the Goodreads dialog due to change to use of HTTPS url

**Version 1.7.6** - 15 Dec 2014
- Update: Improved dynamic menu support in line with calibre changes

**Version 1.7.5** - 23 Aug 2014
- Fix: For changes to support calibre 2.0

**Version 1.7.4** - 12 Aug 2014
- Update: Support for upcoming calibre 2.0

**Version 1.7.3** - 11 Nov 2013
- Fix: Drag/drop into the Goodreads dialog due to change to use of HTTPS url

**Version 1.7.2** - 24 Aug 2013
- Fix: Replace some incorrect legacy code that was looking up the old ISBN field in the database instead of identifiers.
- Fix: When Goodreads error is thrown during Add to Shelf to ensure a second error is not displayed to user.

**Version 1.7.1** - 05 Jun 2012
- Fix: Switching editions throwing error caused by changes in 1.7.0

**Version 1.7.0** - 02 Jun 2012
- New: Allow synchronising review text to/from goodreads
- Update: Change the date handling to (hopefully) correctly handle timezones for issues some users experienced
- Update: Adjust some dialog layouts to ensure buttons are sized better with different styles applied
- Update: Minor performance enhancement for when syncing books from large shelves
- Update: Enable gzip compression for oauth calls to see if improves performance

**Version 1.6.7** - 12 May 2012
- Fix: For book titles containing apostrophes for when searching to link books

**Version 1.6.6** - 03 May 2012
- Fix: Bug when error dialog is to be displayed about missing a custom column

**Version 1.6.5** - 20 Apr 2012
- Update: Change the url for authentication to not have a trailing slash as recent Goodreads release broke this.
- Update: Add protection for blank author from bug in calibre
- Fix: When get an error during authentication, do not throw a misleading second error.

**Version 1.6.4** - 14 Feb 2012
- Update: For the switch edition feature, ensure that variations of ISBN scraped from web page are handled better
- Update: On Add to shelf dialog, make the Add to shelf button a default one so can just hit enter

**Version 1.6.3** - 12 Feb 2012
- Add a Switch edition dialog for a linked book to allow picking another edition for page count/cover purposes
- Also allow access to the switch edition dialog from the linked book screen.

**Version 1.6.2** - 30 Dec 2011
- Fix: For missing config value for users upgrading to 1.6 then using sync without configuring shelf first.

**Version 1.6.1** - 21 Dec 2011
- Fix: For the Download shelves as tags feature, broken in 1.6.0

**Version 1.6.0** - 20 Dec 2011
- Update: Adding to/removing from shelves changes:
    - support add/remove to multiple shelves (remembers last choice)
    - support uploading your calibre rating and/or date read custom column
    - support performing other actions when adding to shelf such as setting custom column values
Syncing from shelves changes:
    - support syncing from multiple shelves (intermediate dialog that remembers last choice)
    - support syncing your Goodreads rating and/or date read to custom columns
    - dialog now shows what actions will be applied/columns updated for selected shelves
- Update: Configuration dialogs reworked:
    - tag mappings now edited directly in the shelves grid
    - support multi-select to allow specifying sync rules for multiple shelves at once
    - support configuring actions to take place when adding books to a shelf
    - support uploading rating & date read to goodreads on a per shelf basis
    - support syncing rating & date read from goodreads on a per shelf basis
    - support specifying which columns to sync to for tags, date read and ratings
    - support options for hiding Add to shelf and Sync from shelf menus
    - drop the restriction allowing only one action for a specific column (to allow people to do add/remove tags in a single sync action)
- Update: Menus reworked:
    - add/remove shelf no longer has a shelves submenu forcing a single shelf. Can choose multiple shelves on the new dialog.
    - sync from shelf no longer has a shelves submenu forcing a single shelf. Intermediate dialog to choose instead.
- Update: Change the configuration file to store the tag mappings in the shelves data, and tag mapping column no longer per user
- Update: When matching against a calibre book from the sync dialog, exclude trailing punctuation from title/author
- Update: Add tooltips to the add shelf dialog
- Update: When a Goodreads error occurs, include the xml error response in the error dialog as has reason for error
- Update: Upgrade oauth2 to v1.5.210 and httplib2 to v0.7.2
- Update: Remove support for users upgrading from versions prior to 1.1

**Version 1.5.2** - 2 Nov 2011
- Fix: For updating boolean columns to use prefs rather than tweaks since changed in Calibre 0.7.55

**Version 1.5.1** - 19 Sep 2011
- Fix: In new menu building code for when a user has multiple Goodreads user accounts setup.

**Version 1.5.0** - 17 Sep 2011
- Update: Upgrade to support the centralised keyboard shortcut management in Calibre

**Version 1.4.15** - 11 Jul 2011
- Fix bug of DEBUG not available when error thrown
- Update: Ensure the book details pane is updated after adding a Goodreads link to the selected book

**Version 1.4.14** - 17 Jun 2011
- New: Allow enumerated text columns for sync action columns
- Update: Ensure the book details pane is updated after removing a Goodreads link to the selected book

**Version 1.4.13** - 02 Jun 2011
- Update: Upgrade the oauth2 library to 1.5.170
- Update: Ensure the book details pane is updated after shelf changes or linking books

**Version 1.4.12** - 17 May 2011
- Fix: Bug of removing from id cache error when does not exist in cache

**Version 1.4.11** - 09 May 2011
- Update: Do not try to write null ISBN to database after performing a sync

**Version 1.4.10** - 08 May 2011
- Update: Change all webbrowser launching to use Calibre's wrapper for the default browser for better Linux support

**Version 1.4.9** - 07 May 2011
- Fix: For no ISBN causing errors when adding to shelf

**Version 1.4.8** - 04 May 2011
- Update: Remove the add shelves button from the edit shelf tag mappings dialog. Always display all your shelves.
- Update: When adding a shelf to the mapping list, default it to having no Calibre tags instead of a tag of the shelf name.
- Fix: For correct error dialog not showing when have an error during Goodreads communication.

**Version 1.4.7** - 23 Apr 2011
- Update: Force the Goodreads/Calibre id caches to be updated more frequently.

**Version 1.4.6** - 13 Apr 2011
- Update: Change the URL searched against as Goodreads have changed their website.

**Version 1.4.5** - 09 Apr 2011
- Update: Support skinning of icons by putting them in a plugin name subfolder of local resources/images

**Version 1.4.4** - 08 Apr 2011
- Update: Change the Download shelves as tags behaviour so that if the target is a custom column it always overwrites

**Version 1.4.3** - 07 Apr 2011
- New: Add a Paste Goodreads.com right-click option (ctrl+V) to Pick Goodreads book dialog as alternative for Opera users to drag/drop

**Version 1.4.2** - 07 Apr 2011
- Fix: For URL not defined

**Version 1.4.1** - 04 Apr 2011
- Fix: For moved functions not declared properly reported by kenr276
- Fix: For settings not saving when ok in preferences
- Fix: For edit shelf/tag mappings after switching libraries where col does not exist

**Version 1.4** - 03 Apr 2011
- Update: Rewritten for new plugin infrastructure in Calibre 0.7.53

**Version 1.3.2** - 23 Mar 2011
- New: Allow upload tags for a book that is not on your exclusive shelves

**Version 1.3.1** - 23 Mar 2011
- Fix: For selected_goodreads_id function rename

**Version 1.3** - 23 Mar 2011
- New: Add "Upload tags to shelves" feature, as a mirror to the "Download tags from shelves"

**Version 1.2** - 16 Mar 2011
- New: Allow Download tags from shelves to be targeted at a custom column, not just tags.
- Fix: For drag/drop where url had '-' instead of '.' separator

**Version 1.1.1** - 09 Mar 2011
- Fix: For download shelves as tags

**Version 1.1** - 09 Mar 2011
- New: Add menu/config options to download tags from shelves
- New: Add option to create new shelves
- New: Add option to edit shelves on Goodreads from config dialog
- New: Add warning when removing from exclusive shelves
- Update: Migrate Goodreads Id to Identifiers
- Update: Remove restriction on #shelves downloaded.
- Fix: For no Goodreads book selected when linking
- Fix: For book showing as linked after deleted
- Fix: For no isbn giving NoneType error
- Fix: For trailing whitespace title

**Version 1.0** - 27 Feb 2011
- Initial release of Goodreads Sync plugin