# Reading List Plugin
[![MobileRead][mobileread-image]][mobileread-url]
[![History][changelog-image]][changelog-url] 
[![License][license-image]][license-url]
[![calibre Version][calibre-image]][calibre-url]
[![Status][status-image]][status-image] 

## Overview

This plugin is for a number of users who have requested a "Reading List" ability for their library, allowing them to keep track of which books they would like to read next and in which order. You can have multiple lists per library per device.

This plugin has also integrated all the functionality of the now deprecated Book Sync plugin, allowing you to synchronise list(s) to a device either manually or automatically when it is connected.

You also have the ability to generate lists based on the content of your device. In combination with the ability to apply tags or populate a custom column based on membership in a list, this provides an easy way to keep track of books on your device(s) while they are not connected.

## Main Features

- Create one or more independent lists of books, per library
- Lists can be manually populated, auto-populated based on books on a device, or auto-populated based on a tag/custom column value
- Add all books with the same series series name for the selected books to a list
- Order the contents of a list (for manual lists, order is viewable in calibre only, not on the device)
- Optionally specify a tag or custom column value to be added when books are put on the list and/or removed when taken off the list
- Optionally sync each list to one or more devices, a folder or iTunes
- Specify whether list sync should add only new items not on device, add all items every time, remove all items that are on the list, or replace all items on the device with the list
- Optionally force a sync to the device of your list if adding while it is connected
- Optionally populate a custom series column with your reading list order, for constant visibility within calibre or content server
- Optionally force Kindle Collections to be recreated after a sync. Kindle DX 2,3,4 non-touch owners only, requires the [Kindle Collections plugin][kindle-collections-url]
- Configure devices and the names for individual storage locations
- View the contents of your list in the library view sorted in list sequence.
- Remove books from your list, move books between lists and clear lists.
- Shortcuts customisable in a configuration dialog

## Plugin Menu

| Menu Item  | Description |
| --------| ----------- |
| Add to &lt;Default&gt; list | Add the currently selected book(s) to your **Default** list.
| Add series to &lt;Default&gt; list | Add all books in the same series as currently selected book(s) to your **Default** list.
| Move to list... | Displays a dialog allowing you to choose which list to add eslected books to.
| Remove from &lt;Default&gt; list | Remove selected book(s) from your **Default** list if present on it.
| View &lt;Default&gt; list | Display the books on your **Default** list in calibre book list view.
| View &lt;ListName&gt; list | Display books on the named list in calibre book list view.
| Edit &lt;ListName&gt; list | Edit books on this list allowing you to change reading order.
| Clear &lt;ListName&gt; list | Remove all books from the specified list.
| Set default list | Make the specified list in the submenu your **Default** list.<br>Only impacts the menu options above for ease of access to common list functions.
| Sync Now | Enabled when a device is connected, to manually sync list with your device.
| Customize plugin... | Access to more advanced plugin configuration, such as creating lists.

## Configuration Options

### Lists Tab -> Population Options

| Option  | Description |
| --------| ----------- |
| List type | **Manually add/remove items** - list is populated by your manual actions.<br>**Auto populated from books on device** - When reading device is plugged in, list is overwritten with by whatever books are on that device<br>**Auto populated from search** - List is dynamically tied to the evaluation of a calibre saved search.
| Auto populate from search | Only applies when list type is *Auto populated from search*.<br>Specify the calibre saved search to populate from each time list is used.

### Lists Tab -> Sync Options

| Option  | Description |
| --------| ----------- |
| Device to sync this list to | Enables you to send books on your list to the specified reading device.<br>Reading devices are setup on the **Devices** tab.
| When syncing this list | **Add new list items to device** - Sends only books on the list that are not present on device. Does not remove from device books that are not on list.<br>**Add/overwrite all list items to device** - Sends new books on list and overwrite existing books on list. Does not remove from device books that are not on list.<br>**Remove list items from device** - Does not add books to device. Only removes any that match this list.<br>**Replace device with list, add new items only** - Sends only books on the list that are not present on device. Removes all books from device not on list.<br>**Replace device with list, add/overwrite all** - Sends all books on the list, overwriting if already present on device. Removes all books from device not on list.
| Sync if connected | If checked, list will sync every time the is plugged in.<br>If unchecked you must manually choose from menu to sync a list.
| Clear list after sync | If checked, list will be cleared after a sync has taken place.

### Lists Tab -> Column Update Options

| Option  | Description |
| --------| ----------- |
| When changing list | **Do not update calibre column** - No custom column interaction desired.<br>**Update column for add or remove** - Apply a value to a custom column when add to list, clear value when removed.<br>**Update column for add to list only** - Apply a value to a custom column when add to list. No changes when removed.<br>**Update column for remove from list only** - Apply a value to a custom column when removed from list. No changes when added.
| Column to update | Your calibre custom column to apply some value to based on above rule.<br>e.g. you might add/remove to the `tags` column to indicate book is on your device.
| Value in column | The value in the custom column to apply based on above rule.<br>e.g. the tags column above might have a tag value called `Kindle` to apply when on the list.

### Lists Tab -> Reading Order Options

| Option  | Description |
| --------| ----------- |
| Store in series column | Only enabled if List type is **Manually add/remove items** and **Clear this list after a sync to this device** is unchecked.<br>Specify a series custom column that this list will update.<br>This column will get overwritten by this plugin, do not populate manually!<br>Use this feature if you want your reading list order to be visible on your books view.
| Series name | If specified will be the name displayed in your series column e.g. 'ToRead'<br>If not specified, will be the name of the reading list itself.

### Lists Tab -> Display Options

| Option  | Description |
| --------| ----------- |
| Move View list | By default your lists appear in a View list submenu.<br>If checked, this list will appear in the top level menu instead.
| Apply reading list order | If checked changes your calibre view sort columns when viewing this list.<br>Useful if you have ordered your list specifically.
| Restore sort after viewing | Only enabled if you have checked the above option.<br>Apply whatever sort you had before viewing the list when the list i sno longer displayed.<br>e.g. you apply a search, switch libraries or quit calibre.

### Devices Tab

| Column  | Description |
| --------| ----------- |
| Menu | Whether the specified device should appear in menus/dropdowns for this plugin.
| Name | Display name for this device. Read from the configuration file on the device.
| Location | Name of the storage location within the device. Read from device configuration file.
| Status | Whether this device is currently connected.
| Kindle Collections | For legacy Kindles only (DX, 2, 3, 4 non-touch), offers integration with the Kindle Collections plugin.<br>Modern kindles cannot be supported by the [Kindle Collections plugin][kindle-collections-url] unfortunately.

### Other Tab

| Option  | Description |
| --------| ----------- |
| Keyboard shortcuts | Quick access for modifying keyboard shortcuts for menus in this plugin.
| Reset confirmation dialogs | Various dialogs in this plugin offer a "do not show me again" option.<br>If you want to reset all of them back to becoming visible again click this button.
| View library preferences | For advanced/diagnostic purposes only.<br>Allows viewing/editing library specific plugin settings.
| Show dialog when removing | Relevent when syncing a list means books will get removed from the device.<br>If checked, a dialog will appear asking you to confirm book deletion from device.

## Development / Contributions

All kiwidude's calibre plugins are now developed and maintained in GitHub at:
- https://github.com/kiwidude68/calibre_plugins

Please see the README.md and CONTRIBUTING.md at the above site for more information.


[kindle-collections-url]: https://www.mobileread.com/forums/showthread.php?t=118635

[mobileread-image]: https://img.shields.io/badge/MobileRead-Plugin%20Thread-blue?logo=data:image/x-icon;base64,AAABAAEAEBAAAAEAIABoBAAAFgAAACgAAAAQAAAAIAAAAAEAIAAAAAAAQAQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAns32/zqT5v8SeeD/Enng/xJ54P8SeeD/LYvl/3+78v8AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAZazv/xJ54P8SeeD/Enng/zqT5v9Jm+n/HoLi/xJ54P8SeeD/OpPm/wAAAAAAAAAAAAAAAAAAAAAAAAAAzub7/xJ54P8SeeD/Enng/4/D9P/p6en/0tLS/8Tc8P8SeeD/Enng/xJ54P+Pw/T/AAAAAAAAAAAAAAAAAAAAAL3e+v8SeeD/Enng/xJ54P+93vr/Wlpa/zc3N/8AAAAAEnng/xJ54P8SeeD/f7vy/wAAAAAAAAAAAAAAAAAAAAAAAAAAHoLi/xJ54P8SeeD/T3+r/yQkJP9+jpz/Zazv/xJ54P8SeeD/Enng/73e+v8AAAAAAAAAAAAAAAAAAAAAz8Kt/66uof+Gj4L/ho+C/5SKb/+Vh2j/ho+C/4aPgv+Gj4L/ho+C/5OVgv+6qYP/yryi/wAAAAAAAAAAp5BW/6eQVv+nkFb/p5BW/6eQVv+nkFb/p5BW/6eQVv+nkFb/p5BW/6eQVv+nkFb/p5BW/6eQVv8AAAAA6ePb46eQVv+nkFb/p5BW/6eQVv+nkFb/xLWY/8/Crf/Pwq3/vq6N/7qogv+6qIL/uqiC/7qogv+nkFb/5uDW/+bg1v+nkFb/p5BW/6eQVv+nkFb/p5BW/+zn4f///////////8zMzP92dnb/VFRU/9nZ2f//////taJ5/8/Crf/m4Nb/p5BW/6eQVv+nkFb/p5BW/6eQVv/m4Nb////////////MzMz/k5OT/8zMzP/z8/P//////8S1mP/EtZj/5uDW/6eQVv+nkFb/p5BW/6eQVv+nkFb/oZ6Z/5OTk//m5ub/////////////////8/Pz/3Z2dv9xcHD/j4h7/9rRwf+nkFb/p5BW/6eQVv+nkFb/VVNP/8zMzP/z8/P/dnZ2/9nZ2f///////////5OTk//z8/P//////3Rxa//Pwq3/p5BW/6eQVv+nkFb/p5BW/2FgYP///////////76+vv/MzMz///////////+ioqL/oqKi/76+vv91b2X/z8Kt/6eQVv+nkFb/p5BW/6eQVv+JfWX/bGtq/4WFhf+FhYX//////////////////////76+vv++vr7/taJ5/8/Crf+nkFb/p5BW/6eQVv+nkFb/p5BW/8m7ov//////+Pb1/+bg1v/g2Mz/z8Kt/8/Crf+6qIL/uqiC/6eQVv/m4Nb/uqmD/7qpg/+nkFb/p5BW/6eQVv+nkFb/rZZh/7qpg/+/r43/z8Kt/8/Crf/m4NYd5uDWVQAAAAAAAAAA8A8AAOAHAADAAwAAwEMAAOADAADAAQAAgAEAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAMAAA==
[mobileread-url]: https://www.mobileread.com/forums/showthread.php?t=134856

[changelog-image]: https://img.shields.io/badge/History-CHANGELOG-blue.svg
[changelog-url]: CHANGELOG.md

[license-image]: https://img.shields.io/badge/License-GPL-yellow.svg
[license-url]: ../LICENSE.md

[calibre-image]: https://img.shields.io/badge/calibre-2.0.0-green
[calibre-url]: https://www.calibre-ebook.com/

[status-image]: https://img.shields.io/badge/Status-Stable-green