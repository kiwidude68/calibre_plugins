# Search The Internet Plugin
[![MobileRead][mobileread-image]][mobileread-url]
[![History][changelog-image]][changelog-url] 
[![License][license-image]][license-url]
[![calibre Version][calibre-image]][calibre-url]
[![Status][status-image]][status-image] 

## Overview

This plugin was designed to allow quick navigation from the selected books in the library view in Calibre to a choice of websites in your web browser.

By default websites such as FantasticFiction, Amazon, Google and Wikipedia are assigned, however around 100 more website links are included for you to select from and you can add/remove your own to this list.

I mainly use this plugin to look for better quality metadata than that available from the default Calibre sources, however it is also useful to get detailed reviews, identify missing books in a series, accurate publication dates, find similar authors etc.

## Main Features

- Launch website searches for books matching author, title, isbn or any other book metadata field
- Can assign multiple pages to open at once in a special group
- Easy to use configuration dialog accessed via right-click menu or Preferences -> Plugins
- Over 100 predefined website urls for you to choose from, plus the ability to add your own.
- Supports HTTP POST searches for websites that cannot use a querystring
- Menu is fully customisable to change ordering, add submenus, keyboard shortcuts and images
- Import and export capability for backup or sharing with other users
- Help file web page available from the configuration dialog

## Configuration Options

| Column  | Description |
| --------| ----------- |
| Active | Items ticked in this first column will appear in your menu.<br>A small selection are ticked by default. |
| Menu Text | The name to appear in the menu.<br>Leave this blank if you want a separator row.<br>You must have a value in this column before you can edit the later columns.<br>Erasing the value in this column will clear the other columns. |
| Submenu | An optional sub-menu name to display this menu item within.<br>If you have many menu items you may find it more manageable to group them within sub-menus.<br>So for instance typing `Amazon` into this column for all the Amazon rows in the grid will ensure they<br>are displayed within an “Amazon” sub-menu when the “Search the Internet” menu is expanded. |
| Open Group | Allows you to open multiple website links from a single click.<br>Tick this checkbox for each row in the menu that you would like to include in this special group.<br>If one or more menu items have this ticked then a special “Open Group” menu item will appear.<br>If no active menu items have this option ticked, the “Open Group” option does not appear. |
| Image | The filename of an image icon to display next to your menu item.<br>Leave blank for no image.<br>Images for the supplied menu items are included in the plugin zip file.<br>To add your own image files, choose the **Add New Image...** menu item within the combobox. |
| URL | Items ticked in this first column will appear in your menu.<br>A small selection are ticked by default. |
| Encoding | The encoding to use when translating title and author names for passing to the website.<br>Of particular importance to users with foreign language titled books.<br>The default of `utf-8` should be sufficient for most websites. |
| Method | Whether to use HTTP `GET` (default) or `POST` to submit the search.<br>Any website that you can query by pasting the search url into the browser will use `GET`.<br>Some websites require data must be submitted from a hidden form via `POST`.<br>Specify your name/value pairs in your url exactly the same as you would for a querystring. |

The buttons available perform the following functions:

- **Move Up** / **Move Down** – Change the order the included items will appear in your menu. You can select multiple rows at once to move up and down.
- **Add** – Adds a blank row for you to create your own website menu link below the currently selected row.
- **Delete** – Allows you to remove menu items from the list completely. Although this should rarely be necessary as you can just untick an item to not display it.
- **Reset to Defaults** – Can be used if you want to discard all your changes and return to the plugin default menu. You will be prompted to confirm this action before proceeding, as this will remove any custom menu items or other changes you have made to ordering, shortcuts etc. Should you change your mind after the change you can cancel all changes made in the configuration dialog when you exit.
- **Keyboard Shortcuts...** – Launches the Calibre shortcuts dialog showing all of the available active menu items that you could apply a keyboard shortcut to along with their current settings.

In addition there is a context menu available within the grid, offering these options:

- **Add image** – Alternative way to add new images to the Calibre images repository for use by the plugin. Functionally equivalent to that in the dropdown image combo, except that if you add an image it will not change the image name selected in the dropdown values.
- **Open images folder** – Allows direct access to the Calibre configuration folder for your custom images. If the folder does not yet exist you are prompted if you would like to create it.
- **Move active to top** –  Moves all of the rows you have checked as active to the top of the grid. You may find this useful to help focus on editing just the menu items of interest to you.
- **Test url** – Launches the selected website url(s) using the last test data selected using the menu option below it.
- **Test url using...** – Opens a dialog allowing you to specify which test book data to use and then launch the selected website url(s) without closing the configuration dialog. A number of example books have been included to suit various international websites, the values for each can be overwritten if desired.
- **Import...** – Allows importing of menu items from a .zip file, created using the Export menu item described below. Can be used to import menu items created by other users, or your own if you use Export to back them up. All menu items imported will be inserted below the currently selected row, along with any images they require.
- **Export...** – Allows you to export the selected menu item(s) to a .zip file, which is actually a .zip file with a renamed extension. All data for those selected menu items entered will be stored in the .zip file along with any custom images you may have added. This feature could be used to share menu items with other users, or as an alternative way to backup your menu settings.

The final option on this screen allows you to specify a keyboard shortcut for the **Open Group** menu item to open multiple website links at once. As mentioned above this menu item only appears in your menu if you have checked the **Open Group** column for one or more menu items that also have **Active** checked.

## Url Tokens

The following tokens are examples of those supported for substitution at run-time using data from the selected book. Most should be self explanatory. Note that as of version 1.5 this plugin uses the Calibre template language so more complex formulas or other metadata fields are possible.

Note that for all fields that their values are encoded for safely passing as part of a URL, such as replacing spaces with + signs. So if you apply a formula it will be with the encoded version of the value.

| Token | Description |
| ----- | ----------- |
| {author} | The author of the book (first if there are multiple).<br>If your authors are stored in LN, FN format, the name will be flipped in an attempt to always pass the name in FN LN format.<br>For querystring purposes, any spaces are replaced with + signs, so it will be generated as FN+LN |
| {title} | The title of the book. |
| {publisher} | The publisher of the book |
| {isbn} | The 13-digit ISBN number of the book. |

## Adding Custom Menu Images

You have several choices for how you add custom .png images for your menu items.

The easiest way is to expand the **Image** column dropdown on the configuration dialog for the plugin and select the **Add New Image...** menu option. This will show a configuration dialog allowing you to source the image:

- **From web domain favicon** - Use this option to download the image file that you see in your browser location bar/bookmarks when you navigate to the website. It uses a google service http://www.google.com/s2/favicons?domain=xxx which returns the image as a png file for you to save. You just need to type the top level domain name such as www.google.com or www.amazon.com along with the name to save it as.
- **From .png file** - Allows you to copy a .png file from your local drives to the correct Calibre location for you.

Alternatively if you want to place them manually these should be placed in a `\resources\images` folder within the Calibre configuration folder as described in the Calibre help. You can find this directory by using:

> **Preferences -> Miscellaneous -> Open calibre configuration directory**

You can also use the **Open images folder** context menu option available in the menu items grid on the configuration dialog for this plugin.

It is quite probable as a first time user you do not already have the required resource subfolder. If that is the case create the `\resources\images` subdirectories yourself.

## Using a Different Web Browser

The behaviour of this plugin is to display web pages using the system configured default web browser, opening each page in a new tab.

If you wish to use a different web browser than your system default, then you can do this by modifying the environment variables for while Calibre is running (such as using a batch file to launch Calibre). The help file for `webbrowser.py` states the following:

> “If the environment variable `BROWSER` exists, it is interpreted to override the platform default list of browsers, as a os.pathsep-separated list of browsers to try in order. When the value of a list part contains the string `%s`, then it is interpreted as a literal browser command line to be used with the argument URL substituted for `%s`; if the part does not contain `%s`, it is simply interpreted as the name of the browser to launch.”

## Backing Up Your Settings

Menu items are persisted into a `Search The Internet.json` file located within the calibre configuration directory for plugins (see above). So if you backup your Calibre configuration directory these settings will be included. Along with all your other Calibre preferences.

You may also chose to use the **Export...** right click feature to save your settings in a .zip file that can be re-imported at any time.

## Known Issues

- Calibre decides on startup whether to scan the `resources\images` folder for custom images only if that folder exists at that time. The very first time you add a custom image using this plugin it will create this directory for you if it does not exist. However in that one scenario you will need to restart Calibre before any custom images you add will be displayed within Calibre. If the directory already exists when Calibre starts, then any new images you add will be displayed immediately. This limitation is by design for performance reasons.
- Retrieving the favicon for a website using Google’s service (as done underneath the covers by this plugin) will lose any transparency for the image. If the icon is a 16x16 coloured square this is unimportant, however icons that are “shaped” with a transparent background will instead have a white background. If this is important to you either edit the downloaded .png manually to erase the background or download it by looking at the web page source code.

## Development / Contributions

All kiwidude's calibre plugins are now developed and maintained in GitHub at:
- https://github.com/kiwidude68/calibre_plugins

Please see the README.md and CONTRIBUTING.md at the above site for more information.


[mobileread-image]: https://img.shields.io/badge/MobileRead-Plugin%20Thread-blue?logo=data:image/x-icon;base64,AAABAAEAEBAAAAEAIABoBAAAFgAAACgAAAAQAAAAIAAAAAEAIAAAAAAAQAQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAns32/zqT5v8SeeD/Enng/xJ54P8SeeD/LYvl/3+78v8AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAZazv/xJ54P8SeeD/Enng/zqT5v9Jm+n/HoLi/xJ54P8SeeD/OpPm/wAAAAAAAAAAAAAAAAAAAAAAAAAAzub7/xJ54P8SeeD/Enng/4/D9P/p6en/0tLS/8Tc8P8SeeD/Enng/xJ54P+Pw/T/AAAAAAAAAAAAAAAAAAAAAL3e+v8SeeD/Enng/xJ54P+93vr/Wlpa/zc3N/8AAAAAEnng/xJ54P8SeeD/f7vy/wAAAAAAAAAAAAAAAAAAAAAAAAAAHoLi/xJ54P8SeeD/T3+r/yQkJP9+jpz/Zazv/xJ54P8SeeD/Enng/73e+v8AAAAAAAAAAAAAAAAAAAAAz8Kt/66uof+Gj4L/ho+C/5SKb/+Vh2j/ho+C/4aPgv+Gj4L/ho+C/5OVgv+6qYP/yryi/wAAAAAAAAAAp5BW/6eQVv+nkFb/p5BW/6eQVv+nkFb/p5BW/6eQVv+nkFb/p5BW/6eQVv+nkFb/p5BW/6eQVv8AAAAA6ePb46eQVv+nkFb/p5BW/6eQVv+nkFb/xLWY/8/Crf/Pwq3/vq6N/7qogv+6qIL/uqiC/7qogv+nkFb/5uDW/+bg1v+nkFb/p5BW/6eQVv+nkFb/p5BW/+zn4f///////////8zMzP92dnb/VFRU/9nZ2f//////taJ5/8/Crf/m4Nb/p5BW/6eQVv+nkFb/p5BW/6eQVv/m4Nb////////////MzMz/k5OT/8zMzP/z8/P//////8S1mP/EtZj/5uDW/6eQVv+nkFb/p5BW/6eQVv+nkFb/oZ6Z/5OTk//m5ub/////////////////8/Pz/3Z2dv9xcHD/j4h7/9rRwf+nkFb/p5BW/6eQVv+nkFb/VVNP/8zMzP/z8/P/dnZ2/9nZ2f///////////5OTk//z8/P//////3Rxa//Pwq3/p5BW/6eQVv+nkFb/p5BW/2FgYP///////////76+vv/MzMz///////////+ioqL/oqKi/76+vv91b2X/z8Kt/6eQVv+nkFb/p5BW/6eQVv+JfWX/bGtq/4WFhf+FhYX//////////////////////76+vv++vr7/taJ5/8/Crf+nkFb/p5BW/6eQVv+nkFb/p5BW/8m7ov//////+Pb1/+bg1v/g2Mz/z8Kt/8/Crf+6qIL/uqiC/6eQVv/m4Nb/uqmD/7qpg/+nkFb/p5BW/6eQVv+nkFb/rZZh/7qpg/+/r43/z8Kt/8/Crf/m4NYd5uDWVQAAAAAAAAAA8A8AAOAHAADAAwAAwEMAAOADAADAAQAAgAEAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAMAAA==
[mobileread-url]: https://www.mobileread.com/forums/showthread.php?t=118758

[changelog-image]: https://img.shields.io/badge/History-CHANGELOG-blue.svg
[changelog-url]: CHANGELOG.md

[license-image]: https://img.shields.io/badge/License-GPL-yellow.svg
[license-url]: ../LICENSE.md

[calibre-image]: https://img.shields.io/badge/calibre-2.0.0-green
[calibre-url]: https://www.calibre-ebook.com/

[status-image]: https://img.shields.io/badge/Status-Stable-green