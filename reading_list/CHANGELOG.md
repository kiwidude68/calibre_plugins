# Reading List Change Log

## [1.15.0] - 2022-10-16
_All kiwidude plugins updated/migrated to: https://github.com/kiwidude68/calibre_plugins_
### Added
- Add Help button to menu and configuration dialog.
- Ukranian translation (@yurchor)
### Changed
- **Breaking:** Drop PyQt4 support, require calibre 2.x or later.
- Refactoring of common code

## [1.14.0] - 2022-09-14
### Fixed
- Sort selectedRows on Edit List, qt gives them in user-selected order.

## [1.13.1] - 2022-08-02
### Fixed
- bug with cal6 icon theme change.

## [1.13.0] - 2022-08-02
### Changed
- Use cal6 icon theme system to allow plugin icon customization

## [1.12.0] - 2022-07-11
### Fixed
- "Restore sort after viewing list" option checkbox in cal6.

## [1.11.0] - 2022-06-25
### Changed
- Allow config dialog to scroll so it can resize smaller

## [1.10.0] - 2022-06-16
### Added
- "Restore sort after viewing list" option added as per capink's contribution.

## [1.9.0] - 2022-04-27
### Changed
- Qt.ItemFlags->Qt.ItemFlag for upcoming Qt6 Calibre

## [1.8.0] - 2022-01-22
### Changed
- Bump Minimum Calibre version to 2.85.1
- Changes for upcoming Qt6 Calibre

## [1.7.6] - 2021-05-01
### Added
- Allow Translations and Spanish translation, thanks dunhill!
### Fixed
- Handle missing default and no lists in settings. Shouldn't happen, but somebody got there.

## [1.7.2] - 2021-03-16
### Fixed
- Delete list and tags_column=''

## [1.7.1] - 2020-11-18
### Fixed
- Sort View Lists sub menu.

## [1.7.0] - 2020-11-08
### Added
- Optional list features: Put any List's View action in the PI top menu and an option to not sort the books in list order on view. Thanks to kiwidude himself for these changes.
- Move up/down 10 & to top/bottom of list in Edit List, thanks to snarkophilus for these changes.
### Changed
- Apply persist_shortcut to view actions when Calibre >= v5.4 so view shortcuts aren't discarded as easily. Calibre PR #1246
### Fixed
- not always detecting 'last' or 'first' selected item correctly in Edit.

## [1.6.15] - 2020-10-08
### Changed
- Honor modify action setting on device pop lists.
### Fixed
- Force pre-existing lists to TAGADDREMOVE to match prior behavior.
- Disable series labels too when series settings disabled.

## [1.6.9] - 2020-07-11
### Fixed
- Auto-populated default lists.

## [1.6.7] - 2020-01-16
### Changed
- Compatibility with Python 3

## [1.6.6] - 2014-11-22
### Fixed
- Keyboard shortcuts not working on calibre >= 2.10

## [1.6.5] - 2014-07-28
### Changed
- Supporting upcoming calibre 2.0

## [1.6.4] - 2013-07-21
### Fixed
- Duplicated keyboard shortcuts between adding to a list and adding series to a list (honest!)

## [1.6.3] - 2013-07-20
### Fixed
- Duplicated keyboard shortcuts between adding to a list and adding series to a list

## [1.6.2] - 2013-05-09
### Added
- Add a "Add series to xxx" menu option to allow quickly adding all books in a series for the selected book(s)
### Changed
- Change for correct support of calibre 0.9.29 virtual libraries feature
- Improve readability of the confirmation text when clearing a reading list

## [1.6.1] - 2013-03-17
### Changed
- Rewrite auto-populate from column to be "auto-populate from search". Users now type a search expression rather than choosing a column/value.

## [1.6.0] - 2012-11-23
### Added
- Ability to automatically create lists based on tags or custom column values
### Changed
- When moving books between lists, turn off warnings to prevent multiple errors being displayed
- If default list is set to an automatically populated list, do not allow the add/edit/clear actions for default list

## [1.5.2] - 2012-08-22
### Fixed
- Signal disconnection which prevented things working once the config window had been opened/closed.

## [1.5.1] - 2012-07-30
### Added
- Allow multiple lists to be selected in the Move to list dialog, as an alternate way for users to add to multiple lists at once
### Changed
- Set a favourites_menu_unique_name attribute on menu actions that have dynamically changing names for Favourites Menu plugin usage
### Fixed
- Ensure error not thrown if device is connected after configuration is closed and objects deleted

## [1.5.0] - 2012-06-22
### Added
- Store list contents in the calibre database rather than a json file, to allow reuse from different computers (not simultaneously!)
- Option in the "Other" tab allowing viewing the plugin data stored in the database
### Changed
- Now requires calibre 0.8.57
- Remove code that supported upgrading from earlier than 1.2.0 of this plugin.

## [1.4.4] - 2012-06-15
### Added
- Add a create_list function to the internal API for use by other plugins
- Add further refresh_screen overloads to the API functions and improve command line testability

## [1.4.3] - 2012-05-30
### Added
- Add a confirmation prompt to the clear list option.
### Changed
- Change the Move to list functionality, so it is always available rather than only when viewing a list. Change behaviour to prompt for source/target lists.
- When choosing Remove from all lists, if currently viewing a list then refresh it.

## [1.4.2] - 2012-01-28
### Added
- Offer option to display the reading order in a custom series column
### Fixed
- Clearing a list would not immediately refresh books on screen that were on that list

## [1.4.1] - 2012-01-12
### Changed
- Refactor some methods to expose the ability to add/remove from lists from other plugins

## [1.4.0] - 2011-11-21
### Added
- List type of "Auto populate list from books on device". Populated when you sync. You cannot manually add/remove.
- Clear menu items for fast way of clearing the contents of a list
- An option on Other Options tab for whether to display the remove books from device dialog, allowing unattended syncing.
### Changed
- Move the devices list onto its own tab to simplify list appearance
### Fixed
- Ensure when a list has auto-clear turned on, items are removed even if not found necessary to sync them

## [1.3.2] - 2011-11-02
### Added
- Allow specifying the value to be assigned to a boolean when adding, rather than always just "Y" (True)
### Changed
- If tristate column and list set to remove value from a boolean column, will set the column to blank (as per previous)
- If non tristate column, will set the value to the opposite of what you specified on config dialog for an add (i.e. ignores current value)
### Fixed
- Updating boolean columns to use prefs rather than tweaks since changed in Calibre 0.7.55

## [1.3.1] - 2011-10-23
### Added
- Allow a list to be associated with "*Any Device" so a single list can be synced to multiple devices
- When switching libraries, if a device is connected then fire the check to see whether lists to sync
- Add list type "Replace device with list, send new only" to delete non-list books from device, send new items not on device
- Add list type "Replace device with list, overwrite all" to delete non-list books from device, overwrite all books with list
### Changed
- Rename list types - Sync new list items -> Add new list items to device, Sync all list items -> Add all list items to device

## [1.3.0] - 2011-09-17
### Changed
- Upgrade to support the centralised keyboard shortcut management in Calibre

## [1.2.7] - 2011-08-06
### Added
- Add a Move menu option when viewing a list, to allow moving an item to another list

## [1.2.6] - 2011-07-31
### Fixed
- Ensure people upgrading who had no list type node in their config xml do not get an error.

## [1.2.5] - 2011-07-30
### Added
- Offer option of controlling whether tags are added only or removed only for each list
### Changed
- When syncing lists, apply and "Remove" type lists before any other list types

## [1.2.4] - 2011-07-05
### Added
- On the View menu item, put a total of items on all lists on the top level menu item
- On the Sync now menu item, put a total count from all the lists that would be synced

## [1.2.3] - 2011-06-20
### Fixed
- For "Sync all items" functionality

## [1.2.2] - 2011-06-20
### Added
- Add a "list type" for each list, which allows syncing new only, all items, or removing items from device

## [1.2.1] - 2011-06-18
### Changed
- When syncing a list, only sync books not already on the device

## [1.2.0] - 2011-06-08
### Added
- Integrate the Book Sync functionality allowing specifying a device to send a list to
- Add a count of the items on a list to the menu
- Add optional keyboard shortcut to add to a specific list

## [1.1.1] - 2011-06-05
### Changed
- Support the config migration for users who jumped from earlier versions

## [1.1.0] - 2011-06-03
### Changed
- Change all tagging column definitions and values to be per list rather than per library
- Support other custom column types of enumeration and boolean

## [1.0.3] - 2011-06-02
### Added
- Add menu option to remove books from the list, with a keyboard shortcut
- Add a button to configuration dialog to allow resetting confirmation dialogs
### Changed
- Change the error and delete list/item confirmation dialogs to have the option to not show again
### Fixed
- Ensure the book details pane is updated for the current row

## [1.0.2] - 2011-05-30
### Added
- Expand on the tags add/remove option to allow choosing a custom column instead
### Changed
- If edit while viewing the contents of a list, refresh the view afterwards
- If a user deletes a list, ensure any tags are removed for items on that list

## [1.0.1] - 2011-05-28
### Added
- Add option to add tags when book added to list, and remove tags when removed from list

## [1.0.0] - 2011-05-28
_Initial release of Reading List plugin_
