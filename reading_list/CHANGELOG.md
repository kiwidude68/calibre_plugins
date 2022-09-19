## Release History

**Version 1.15.0** - XX Sep 2022
- New: All kiwidude plugins updated/migrated to: https://github.com/kiwidude68/calibre_plugins
- Update: Drop PyQt4 support, require calibre 2.x or later.
- Update: Refactoring of common code

**Version 1.14.0** - 2022-09-14
- Fix: Sort selectedRows on Edit List, qt gives them in user-selected order.

**Version 1.13.1** - 2022-08-02
- Fix: bug with cal6 icon theme change.

**Version 1.13.0** - 2022-08-02
- Update: Use cal6 icon theme system to allow plugin icon customization

**Version 1.12.0** - 11 Jul 2022
- Fix: "Restore sort after viewing list" option checkbox in cal6.

**Version 1.11.0** - 25 Jun 2022
- Update: Allow config dialog to scroll so it can resize smaller

**Version 1.10.0** - 16 Jun 2022
- New: "Restore sort after viewing list" option added as per capink's contribution.

**Version 1.9.0** - 27 Apr 2022
- Update: Qt.ItemFlags->Qt.ItemFlag for upcoming Qt6 Calibre

**Version 1.8.0** - 22 Jan 2022
- Update: Bump Minimum Calibre version to 2.85.1
- Update: Changes for upcoming Qt6 Calibre

**Version 1.7.6** - 01 May 2021
- New: Allow Translations and Spanish translation, thanks dunhill!
- Fix: Handle missing default and no lists in settings. Shouldn't happen, but somebody got there.

**Version 1.7.2** - 16 Mar 2021
- Fix: Delete list and tags_column=''

**Version 1.7.1** - 18 Nov 2020
- Fix-: Sort View Lists sub menu.

**Version 1.7.0** - 08 Nov 2020
- New: Optional list features: Put any List's View action in the PI top menu and an option to not sort the books in list order on view. Thanks to kiwidude himself for these changes.
- New: Move up/down 10 & to top/bottom of list in Edit List, thanks to snarkophilus for these changes.
- Update: Apply persist_shortcut to view actions when Calibre >= v5.4 so view shortcuts aren't discarded as easily. Calibre PR #1246
- Fix: not always detecting 'last' or 'first' selected item correctly in Edit.

**Version 1.6.15** - 09 Oct 2020
- Update: Honor modify action setting on device pop lists.
- Fix: Force pre-existing lists to TAGADDREMOVE to match prior behavior.
- Fix: Disable series labels too when series settings disabled.

**Version 1.6.9** - 11 Jul 2020
- Fix: Auto-populated default lists.

**Version 1.6.7** - 16 Jan 2020
- Update: Compatibility with Python 3

**Version 1.6.6** - 22 Nov 2014
- Fix: Keyboard shortcuts not working on calibre >= 2.10

**Version 1.6.5** - 28 Jul 2014
- Update: Supporting upcoming calibre 2.0

**Version 1.6.4** - 21 Jul 2013
- Fix: Duplicated keyboard shortcuts between adding to a list and adding series to a list (honest!)

**Version 1.6.3** - 20 Jul 2013
- Fix: Duplicated keyboard shortcuts between adding to a list and adding series to a list

**Version 1.6.2** - 09 May 2013
- New: Add a "Add series to xxx" menu option to allow quickly adding all books in a series for the selected book(s)
- Update: Change for correct support of calibre 0.9.29 virtual libraries feature
- Update: Improve readability of the confirmation text when clearing a reading list

**Version 1.6.1** - 17 Mar 2013
- Update: Rewrite auto-populate from column to be "auto-populate from search". Users now type a search expression rather than choosing a column/value.

**Version 1.6.0** - 23 Nov 2012
- New: Ability to automatically create lists based on tags or custom column values
- Update: When moving books between lists, turn off warnings to prevent multiple errors being displayed
- Update: If default list is set to an automatically populated list, do not allow the add/edit/clear actions for default list

**Version 1.5.2** - 22 Aug 2012
- Fix: Signal disconnection which prevented things working once the config window had been opened/closed.

**Version 1.5.1** - 30 Jul 2012
- New: Allow multiple lists to be selected in the Move to list dialog, as an alternate way for users to add to multiple lists at once
- Update: Set a favourites_menu_unique_name attribute on menu actions that have dynamically changing names for Favourites Menu plugin usage
- Fix: Ensure error not thrown if device is connected after configuration is closed and objects deleted

**Version 1.5.0** - 22 Jun 2012
- New: Store list contents in the calibre database rather than a json file, to allow reuse from different computers (not simultaneously!)
- New: Option in the "Other" tab allowing viewing the plugin data stored in the database
- Update: Now requires calibre 0.8.57
- Update: Remove code that supported upgrading from earlier than 1.2.0 of this plugin.

**Version 1.4.4** - 15 Jun 2012
- New: Add a create_list function to the internal API for use by other plugins
- New: Add further refresh_screen overloads to the API functions and improve command line testability

**Version 1.4.3** - 30 May 2012
- New: Add a confirmation prompt to the clear list option.
- Update: Change the Move to list functionality, so it is always available rather than only when viewing a list. Change behaviour to prompt for source/target lists.
- Update: When choosing Remove from all lists, if currently viewing a list then refresh it.

**Version 1.4.2** - 28 Jan 2012
- New: Offer option to display the reading order in a custom series column
- Fix: Clearing a list would not immediately refresh books on screen that were on that list

**Version 1.4.1** - 12 Jan 2012
- Update: Refactor some methods to expose the ability to add/remove from lists from other plugins

**Version 1.4.0** - 21 Nov 2011
- New: List type of "Auto populate list from books on device". Populated when you sync. You cannot manually add/remove.
- New: Clear menu items for fast way of clearing the contents of a list
- New: An option on Other Options tab for whether to display the remove books from device dialog, allowing unattended syncing.
- Update: Move the devices list onto its own tab to simplify list appearance
- Fix: Ensure when a list has auto-clear turned on, items are removed even if not found necessary to sync them

**Version 1.3.2** - 2 Nov 2011
- New: Allow specifying the value to be assigned to a boolean when adding, rather than always just "Y" (True)
- Fix: Updating boolean columns to use prefs rather than tweaks since changed in Calibre 0.7.55
- Update: If tristate column and list set to remove value from a boolean column, will set the column to blank (as per previous)
- Update: If non tristate column, will set the value to the opposite of what you specified on config dialog for an add (i.e. ignores current value)

**Version 1.3.1** - 23 Oct 2011
- New: Allow a list to be associated with "*Any Device" so a single list can be synced to multiple devices
- New: When switching libraries, if a device is connected then fire the check to see whether lists to sync
- New: Add list type "Replace device with list, send new only" to delete non-list books from device, send new items not on device
- New: Add list type "Replace device with list, overwrite all" to delete non-list books from device, overwrite all books with list
- Update: Rename list types - Sync new list items -> Add new list items to device, Sync all list items -> Add all list items to device

**Version 1.3.0** - 17 Sep 2011
- Update: Upgrade to support the centralised keyboard shortcut management in Calibre

**Version 1.2.7** - 06 Aug 2011
- New: Add a Move menu option when viewing a list, to allow moving an item to another list

**Version 1.2.6** - 31 Jul 2011
- Fix: Ensure people upgrading who had no list type node in their config xml do not get an error.

**Version 1.2.5** - 30 Jul 2011
- New: Offer option of controlling whether tags are added only or removed only for each list
- Update: When syncing lists, apply and "Remove" type lists before any other list types

**Version 1.2.4** - 05 Jul 2011
- New: On the View menu item, put a total of items on all lists on the top level menu item
- New: On the Sync now menu item, put a total count from all the lists that would be synced

**Version 1.2.3** - 20 Jun 2011
- Fix: For "Sync all items" functionality

**Version 1.2.2** - 20 Jun 2011
- New: Add a "list type" for each list, which allows syncing new only, all items, or removing items from device

**Version 1.2.1** - 18 Jun 2011
- Update: When syncing a list, only sync books not already on the device

**Version 1.2** - 08 Jun 2011
- New: Integrate the Book Sync functionality allowing specifying a device to send a list to
- New: Add a count of the items on a list to the menu
- New: Add optional keyboard shortcut to add to a specific list

**Version 1.1.1** - 05 Jun 2011
- Update: Support the config migration for users who jumped from earlier versions

**Version 1.1** - 03 Jun 2011
- Update: Change all tagging column definitions and values to be per list rather than per library
- Update: Support other custom column types of enumeration and boolean

**Version 1.0.3** - 02 Jun 2011
- New: Add menu option to remove books from the list, with a keyboard shortcut
- New: Add a button to configuration dialog to allow resetting confirmation dialogs
- Update: Change the error and delete list/item confirmation dialogs to have the option to not show again
- Fix: Ensure the book details pane is updated for the current row

**Version 1.0.2** - 30 May 2011
- New: Expand on the tags add/remove option to allow choosing a custom column instead
- Update: If edit while viewing the contents of a list, refresh the view afterwards
- Update: If a user deletes a list, ensure any tags are removed for items on that list

**Version 1.0.1** - 28 May 2011
- New: Add option to add tags when book added to list, and remove tags when removed from list

**Version 1.0** - 28 May 2011
- Initial release of Reading List plugin
