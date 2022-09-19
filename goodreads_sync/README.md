# Goodreads Sync Plugin
[![MobileRead][mobileread-image]][mobileread-url]
[![History][changelog-image]][changelog-url] 
[![License][license-image]][license-url]
[![calibre Version][calibre-image]][calibre-url]
[![Status][status-image]][status-image] 

## Overview

This plugin allows you to synchronise your book collection in Calibre with your shelves on a [Goodreads.com](http://www.goodreads.com/) account.

Goodreads targets the social aspects of sharing your book lists with friends and family. It offers various services such as reviews, book clubs, discussions and recommendations. You can maintain shelves of books you have read, want to read, are currently reading or others of your own design.

In some cases this is information that you also want to keep track of within Calibre using tags or custom columns. Typical examples of usage of this plugin are:

- Adding a book that you have just imported to Calibre to your 'to-read' shelf on Goodreads
- Updating a Calibre custom column to indicate that you have read a book when syncing from your 'read' shelf on Goodreads
- Multiple actions can be applied. e.g. in the example above you might also populate a 'Read Date' custom column and remove a 'To Read' tag from the book in Calibre.
- Using your own genre shelves in Goodreads like science-fiction, romance etc to map to Calibre tags or a custom genre column of your choice.

## Main Features

- Add or remove books to one or more Goodreads shelves from a selection within Calibre
- Syncing the contents from one or more Goodreads shelves into Calibre, performing customisable actions for each shelf
- Configure actions to be performed for when adding books to a shelf or syncing from Goodreads, such as updating tags, custom columns.
- You can also synchronise your rating, date read and or review text custom column with your Goodreads review.
- Ability to download tags for your books based on the shelves they are on. You can customise which Calibre tags if any each shelf name will map to and use a custom genre column instead of tags if desired.
- Ability to upload to shelves for your books based on the tags they have been given. Applies the to the same Calibre column and shelf mappings as for the download tags feature above.
- Link your Calibre books to a Goodreads equivalent giving you right-click access to reviews or other information for that book
- Ability to switch editions for a linked Goodreads book
- Ability to create Empty Books in Calibre for books you sync from a Goodreads shelf
- Optionally update the ISBN in Calibre to match the edition on your Goodreads shelf
- Supports multiple Goodreads user accounts if required for users sharing a single operating system account
- Help file web page available from the configuration dialog or plugin menu


## Configuration Options

| Option  | Description |
| --------| ----------- |
| Goodreads user | Choose from dropdown if you have multiple Goodreads accounts/users of calibre to switch between.
| Authorize Plugin | For setting up, authorize this plugin to communicate with your Goodreads account.
| Refresh Shelves | If you have add/removed shelves on the goodreads website, click this button to refresh.
| Add Shelf | Allows you to create a new shelf in your Goodreads account
| Edit 'Shelf Add' Actions | Configure optional actions to apply when a book is added to your shelf.
| Edit 'Sync' Actions | Configure optional actions to apply when a shelf is synced to your library.

## Other Configuration Options

| Option  | Description |
| --------| ----------- |
| When linking to Goodreads | **Never modify the calibre ISBN**<br>**Replace calibre ISBN only if none present**<br>**Always overwrite calibre ISBN value**
| Display 'Add to shelf' | For reducing plugin submenus
| Display 'Remove from shelf' | For reducing plugin submenus
| Display 'Update reading progress' | For reducing plugin submenus
| Display 'Sync from shelf' | For reducing plugin submenus
| Display 'View shelf' | For reducing plugin submenus
| Reading progress is % read | If checked, the progress column is a % read. If unchecked it is a page number.
| Empty books author as LN, FN | If adding empty calibre books from dialogs in this plugin, use this author format.

## Synchronisable Custom Columns

| Column  | Description |
| --------| ----------- |
| Tags | Choose the calibre column to contain tags metadata
| Rating | Choose the calibre column to contain goodreads rating metadata
| Date read | Choose the calibre column to contain last date read metadata
| Review text | Choose the calibre column to contain review text metadata
| Reading progress | Choose the calibre column to contain % read or last page read

## Development / Contributions

All kiwidude's calibre plugins are now developed and maintained in GitHub at:
- https://github.com/kiwidude68/calibre_plugins

Please see the README.md and CONTRIBUTING.md at the above site for more information.


[mobileread-image]: https://img.shields.io/badge/MobileRead-Plugin%20Thread-blue?logo=data:image/x-icon;base64,AAABAAEAEBAAAAEAIABoBAAAFgAAACgAAAAQAAAAIAAAAAEAIAAAAAAAQAQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAns32/zqT5v8SeeD/Enng/xJ54P8SeeD/LYvl/3+78v8AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAZazv/xJ54P8SeeD/Enng/zqT5v9Jm+n/HoLi/xJ54P8SeeD/OpPm/wAAAAAAAAAAAAAAAAAAAAAAAAAAzub7/xJ54P8SeeD/Enng/4/D9P/p6en/0tLS/8Tc8P8SeeD/Enng/xJ54P+Pw/T/AAAAAAAAAAAAAAAAAAAAAL3e+v8SeeD/Enng/xJ54P+93vr/Wlpa/zc3N/8AAAAAEnng/xJ54P8SeeD/f7vy/wAAAAAAAAAAAAAAAAAAAAAAAAAAHoLi/xJ54P8SeeD/T3+r/yQkJP9+jpz/Zazv/xJ54P8SeeD/Enng/73e+v8AAAAAAAAAAAAAAAAAAAAAz8Kt/66uof+Gj4L/ho+C/5SKb/+Vh2j/ho+C/4aPgv+Gj4L/ho+C/5OVgv+6qYP/yryi/wAAAAAAAAAAp5BW/6eQVv+nkFb/p5BW/6eQVv+nkFb/p5BW/6eQVv+nkFb/p5BW/6eQVv+nkFb/p5BW/6eQVv8AAAAA6ePb46eQVv+nkFb/p5BW/6eQVv+nkFb/xLWY/8/Crf/Pwq3/vq6N/7qogv+6qIL/uqiC/7qogv+nkFb/5uDW/+bg1v+nkFb/p5BW/6eQVv+nkFb/p5BW/+zn4f///////////8zMzP92dnb/VFRU/9nZ2f//////taJ5/8/Crf/m4Nb/p5BW/6eQVv+nkFb/p5BW/6eQVv/m4Nb////////////MzMz/k5OT/8zMzP/z8/P//////8S1mP/EtZj/5uDW/6eQVv+nkFb/p5BW/6eQVv+nkFb/oZ6Z/5OTk//m5ub/////////////////8/Pz/3Z2dv9xcHD/j4h7/9rRwf+nkFb/p5BW/6eQVv+nkFb/VVNP/8zMzP/z8/P/dnZ2/9nZ2f///////////5OTk//z8/P//////3Rxa//Pwq3/p5BW/6eQVv+nkFb/p5BW/2FgYP///////////76+vv/MzMz///////////+ioqL/oqKi/76+vv91b2X/z8Kt/6eQVv+nkFb/p5BW/6eQVv+JfWX/bGtq/4WFhf+FhYX//////////////////////76+vv++vr7/taJ5/8/Crf+nkFb/p5BW/6eQVv+nkFb/p5BW/8m7ov//////+Pb1/+bg1v/g2Mz/z8Kt/8/Crf+6qIL/uqiC/6eQVv/m4Nb/uqmD/7qpg/+nkFb/p5BW/6eQVv+nkFb/rZZh/7qpg/+/r43/z8Kt/8/Crf/m4NYd5uDWVQAAAAAAAAAA8A8AAOAHAADAAwAAwEMAAOADAADAAQAAgAEAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAMAAA==
[mobileread-url]: https://www.mobileread.com/forums/showthread.php?t=123281

[changelog-image]: https://img.shields.io/badge/History-CHANGELOG-blue.svg
[changelog-url]: CHANGELOG.md

[license-image]: https://img.shields.io/badge/License-GPL-yellow.svg
[license-url]: ../LICENSE.md

[calibre-image]: https://img.shields.io/badge/calibre-2.0.0-green
[calibre-url]: https://www.calibre-ebook.com/

[status-image]: https://img.shields.io/badge/Status-Stable-green