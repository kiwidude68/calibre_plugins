# Quick Preferences Plugin
[![MobileRead][mobileread-image]][mobileread-url]
[![History][changelog-image]][changelog-url] 
[![License][license-image]][license-url]
[![calibre Version][calibre-image]][calibre-url]
[![Status][status-image]][status-image] 

## Overview

This plugin provides a way to quickly switch calibre settings without manually clicking through the various calibre Preferences dialogs. Specifically it caters for preferences related to adding books (but could be added to in future if needed).

Some example common use cases:
- You are importing batches of books with differing filename conventions and want to quickly toggle between various regular expressions for each.
- You want to quickly toggle which metadata source(s) you are downloading from.

By default I have included two regex patterns - the default calibre one, and a second for handling titles in "author [- optional series #] - title" format.

## Main Features

- Add to your toolbar a quick selection dropdown button rather than navigating through the calibre Preferences dialog.
- Store as many regular expressions file patterns as you wish
    - Optionally specify a pairing of the swap author name setting with your regular expression
- Quickly switch between sets of metadata source preferences
- Toggle various other options related to adding books (see below)
- Keeps in sync with changes made via the Preferences dialog
- Customise which menu options are included on the dropdown
- Customise keyboard shortcuts

## Available Preferences

| Plugin Terminology  | calibre Preference |
| ------------------- | ------------------ |
| Metadata sources | **Preferences -> Sharing -> Metadata download -> Metadata source**<br>Checkboxes for which are enabled |
| File patterns | **Preferences -> Import/export -> Adding books -> Reading metadata**<br>Configure metadata from file name -> Regular expression |
| Swap author names | **Preferences -> Import/export -> Adding books -> Reading metadata**<br>Swap author first name and last name when reading author from filename |
| Read metadata from file | **Preferences -> Import/export -> Adding books -> Reading metadata**<br>Read metadata from file contents rather than filename |
| Automerge added books | **Preferences -> Import/export -> Adding books -> Adding actions**<br>Auto-merge added books if they already exist |

## Configuration Options

| Option  | Description |
| ------- | ----------- |
| File pattern menu items | Define the menu items for import file patterns to flip between.<br>Optionally enforce a value for the swap author name FN LN preference (see below).
| Enabled metatada source menu items | Define the menu items for quickly fipping metadata sources.
| Include in menu | Optionally hide from the Quick Preferences menu for settings you will not change.

The default regular expressions included for file patterns:

| Menu Item  | Regular expression |
| ------------------- | ------------------ |
| Title - Author (Default) | `(?P<title>.+) - (?P<author>[^_]+)` |
| Author [- Series #]- Title | `^(?P<author>((?!\s-\s).)+)\s-\s(?:(?:\[\s*)?(?P<series>.+)\s(?P<series_index>[\d\.]+)(?:\s*\])?\s-\s)?(?P<title>[^(]+)(?:\(.*\))?` |

### Swap Author Names

Some extra explanation for why a heavy user of this plugin might use this feature when importing books and controlling when to swap author name format between FN LN and LN, FN.

The default behavior in the configuration options for this plugin has the **Swap Names** column checkbox shown as unspecified (solid gray). When you use that menu item from the Quick Preferences plugin menu, it will **not** modify your current calibre preference swapping author names. The current value of that preference will apply during the import.

However if you were regularly importing batches of books that use a mixture of "FN LN" and "LN, FN" then you might want more control over this in a single menu item click.

The configuration options for this plugin allow you to pair a matching value for the swap names preference with that particular menu item. So you could create additional menu items to ensure for instance that when importing filenames that you know are "FN LN" then you want calibre to swap the names. Then when switching back to the "LN, FN" filename menu item you are wanting calibre to NOT swap the names. 

| Example Menu Title  | Swap Names | Impact |
| --------------------| ---------- | ------ |
| LN, FN | Unspecified | Importing will respect whatever "current" setting is for swapping names. |
| LN, FN No Swap | False | Sets calibre swap names setting to `False`. Importing will not swap names. |
| FN LN Swap | True | Sets calibre swap names setting to `True`. Importing will swap author names. |

However you should not mix and match approaches - either use Swap Names values on all menu items, or leave them all unspecified. Otherwise you risk getting surprise behavior depending on what the underlying calibre preference was flipped to by whichever of the other menu items you previously selected.

## Development / Contributions

All kiwidude's calibre plugins are now developed and maintained in GitHub at:
- https://github.com/kiwidude68/calibre_plugins

Please see the README.md and CONTRIBUTING.md at the above site for more information.


[mobileread-image]: https://img.shields.io/badge/MobileRead-Plugin%20Thread-blue?logo=data:image/x-icon;base64,AAABAAEAEBAAAAEAIABoBAAAFgAAACgAAAAQAAAAIAAAAAEAIAAAAAAAQAQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAns32/zqT5v8SeeD/Enng/xJ54P8SeeD/LYvl/3+78v8AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAZazv/xJ54P8SeeD/Enng/zqT5v9Jm+n/HoLi/xJ54P8SeeD/OpPm/wAAAAAAAAAAAAAAAAAAAAAAAAAAzub7/xJ54P8SeeD/Enng/4/D9P/p6en/0tLS/8Tc8P8SeeD/Enng/xJ54P+Pw/T/AAAAAAAAAAAAAAAAAAAAAL3e+v8SeeD/Enng/xJ54P+93vr/Wlpa/zc3N/8AAAAAEnng/xJ54P8SeeD/f7vy/wAAAAAAAAAAAAAAAAAAAAAAAAAAHoLi/xJ54P8SeeD/T3+r/yQkJP9+jpz/Zazv/xJ54P8SeeD/Enng/73e+v8AAAAAAAAAAAAAAAAAAAAAz8Kt/66uof+Gj4L/ho+C/5SKb/+Vh2j/ho+C/4aPgv+Gj4L/ho+C/5OVgv+6qYP/yryi/wAAAAAAAAAAp5BW/6eQVv+nkFb/p5BW/6eQVv+nkFb/p5BW/6eQVv+nkFb/p5BW/6eQVv+nkFb/p5BW/6eQVv8AAAAA6ePb46eQVv+nkFb/p5BW/6eQVv+nkFb/xLWY/8/Crf/Pwq3/vq6N/7qogv+6qIL/uqiC/7qogv+nkFb/5uDW/+bg1v+nkFb/p5BW/6eQVv+nkFb/p5BW/+zn4f///////////8zMzP92dnb/VFRU/9nZ2f//////taJ5/8/Crf/m4Nb/p5BW/6eQVv+nkFb/p5BW/6eQVv/m4Nb////////////MzMz/k5OT/8zMzP/z8/P//////8S1mP/EtZj/5uDW/6eQVv+nkFb/p5BW/6eQVv+nkFb/oZ6Z/5OTk//m5ub/////////////////8/Pz/3Z2dv9xcHD/j4h7/9rRwf+nkFb/p5BW/6eQVv+nkFb/VVNP/8zMzP/z8/P/dnZ2/9nZ2f///////////5OTk//z8/P//////3Rxa//Pwq3/p5BW/6eQVv+nkFb/p5BW/2FgYP///////////76+vv/MzMz///////////+ioqL/oqKi/76+vv91b2X/z8Kt/6eQVv+nkFb/p5BW/6eQVv+JfWX/bGtq/4WFhf+FhYX//////////////////////76+vv++vr7/taJ5/8/Crf+nkFb/p5BW/6eQVv+nkFb/p5BW/8m7ov//////+Pb1/+bg1v/g2Mz/z8Kt/8/Crf+6qIL/uqiC/6eQVv/m4Nb/uqmD/7qpg/+nkFb/p5BW/6eQVv+nkFb/rZZh/7qpg/+/r43/z8Kt/8/Crf/m4NYd5uDWVQAAAAAAAAAA8A8AAOAHAADAAwAAwEMAAOADAADAAQAAgAEAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAMAAA==
[mobileread-url]: https://www.mobileread.com/forums/showthread.php?t=118776

[changelog-image]: https://img.shields.io/badge/History-CHANGELOG-blue.svg
[changelog-url]: CHANGELOG.md

[license-image]: https://img.shields.io/badge/License-GPL-yellow.svg
[license-url]: ../LICENSE.md

[calibre-image]: https://img.shields.io/badge/calibre-2.0.0-green
[calibre-url]: https://www.calibre-ebook.com/

[status-image]: https://img.shields.io/badge/Status-Stable-green
