# Extract ISBN Plugin
[![MobileRead][mobileread-image]][mobileread-url]
[![History][changelog-image]][changelog-url] 
[![License][license-image]][license-url]
[![calibre Version][calibre-image]][calibre-url]
[![Status][status-image]][status-image] 

## Overview

This plugin will determine a number of pages and/or words in a book and store the result in custom column(s). In addition to just general library browsing usage, Kindle users can generate APNX files using the value from a pages custom column. So when you send an ebook to your Kindle device from calibre, you will have page numbering available similar to that when loading Amazon books which offer this feature.

You have two overriding methods of determining page count with this plugin.

The first approach is estimation based on the book content. It requires you either have an `epub` format or a format that is convertible to `epub`. For comics (`cbr` or `cbz`) it will count the images inside. The format used if your book has multiple is chosen based on your Preferred Input Format order, that you set in Preferences -> Behavior.

Note that if you use this option it can be an approximation only of a paperback edition due to differences in fonts, images, layouts etc. By default it uses an "accurate" algorithm similar to that created by user_none for generating APNX files for Kindle users. Alternatively in the configuration you can choose to use the page count used by the calibre e-book viewer, or you can use the Aobe algorithm used by their ADE software and some devices like a Nook. However if the format being counted is a PDF, then as of v1.4.2 there is now a special optimisation to read the actual page count rather than estimating it using any of the above algorithms.

The second page count option is to download the page count from a web page on the Goodreads.com website for your specific linked edition. This can be used for a book with any formats (or even none). How is a goodreads identifier linked? Either by using the [Goodreads metadata download](https://www.mobileread.com/forums/showthread.php?t=130638) plugin, the [Goodreads Sync](https://www.mobileread.com/forums/showthread.php?t=123281) plugin, or by manually typing a `goodreads:xxx` id into your identifiers field for the edition of interest. If the edition you have linked to has no page count, you can switch editions using a feature added to the Goodreads Sync plugin.

Word count is optionally calculated independently of page count. As this is unavailable on a website, it is subject to the same limitations as estimating page count above, in that you must have either an `epub` or a format convertible to `epub` available for it to work.

You can optionally calculate a variety of readability statistics such as [Flesch-Kincaid](http://en.wikipedia.org/wiki/Flesch%E2%80%93Kincaid_readability_test) and [Gunning Fog](http://en.wikipedia.org/wiki/Gunning_fog_index) index.

## Main Features

- Estimate a page count of books to a custom column (except for `PDF`, which is read directly from the info) using one of four algorithms.
- Alternatively download a page count from the Goodreads.com website into a custom column
- Compute a word count to a custom column
- Compute readability statistics for Flesch Reading level, Flesch-Kincaid Grade level and Gunning Fog index into custom column(s)
- Configure different column(s)/algorithm per calibre library
- Configure whether the default for clicking on the toolbar button is to use an estimated page count or a downloaded page count.
- Optionally configure whether to only overwrite counts if you don't already have one
- Optional keyboard shortcuts

## Configuration Options

### Statistics Tab -> Page count options

| Option  | Description |
| --------| ----------- |
| Custom column | Choose which custom column will store your page count data if any.
| Algorithm | **Paragraphs (APNX Accurate)** - Estimates based on the # of paragraphs in the book.<br>**E-Book Viewer (calibre)** - Estimates using same code as calibre ebook viewer<br>**Adobe Digital Editions** - Estimates using same alorithm as Adobe software<br>**Custom (Chars per page)** - Estimates based on user definable # characters per page
| Chars per page | Only applies if you have chosen the **Custom *Chars per page)** option above.

### Statistics Tab -> Word count options

| Option  | Description |
| --------| ----------- |
| Custom column | Choose which custom column will store your word count data if any.
| Use ICU Algorithm | If unchecked, uses simple approach to counting words.<br>If checked, uses more complex algorithm that should also work better with non-English languages.

### Statistics Tab -> Readability options

| Option  | Description |
| --------| ----------- |
| Flesch Reading Ease | Choose which custom column will store your estimated Flesch reading score, if any.
| Flesch-Kincaid Grade | Choose which custom column will store your estimated Flesch-Kincaid grade, if any.
| Gunning Fog Index | Choose which custom column will store your estimated Gunning Fog index, if any.

### Other Tab -> Download options

| Option  | Description |
| --------| ----------- |
| Download options grid | Choose which website source(s) to enable and offer on the plugin menu.
| Show download from all sources menu item | Enable if you want a menu item to hit all matching identifier websites enabled.
| Try to download from each source | If unchecked, downloading is stopped after first source has a page count.<br>If checked, all sources are tried for a page count.

### Other Tab -> Other options

| Option  | Description |
| --------| ----------- |
| Button default | Choose which menu action to perform when plugin button is clicked in toolbar.
| Always overwrite | Do not prompt for confirmation if a book already has an existing word/page count before updating it.
| Update statistics even if not changed | Force update custom column even if has the same value.
| Use Preferred Output Format if available | Use the calibre preference to determine which preferred book format to scan.
| Prompt to save counts | Whether to display a prompt to user after retrieving statistics in background.

## Development / Contributions

All kiwidude's calibre plugins are now developed and maintained in GitHub at:
- https://github.com/kiwidude68/calibre_plugins

Please see the README.md and CONTRIBUTING.md at the above site for more information.


[mobileread-image]: https://img.shields.io/badge/MobileRead-Plugin%20Thread-blue?logo=data:image/x-icon;base64,AAABAAEAEBAAAAEAIABoBAAAFgAAACgAAAAQAAAAIAAAAAEAIAAAAAAAQAQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAns32/zqT5v8SeeD/Enng/xJ54P8SeeD/LYvl/3+78v8AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAZazv/xJ54P8SeeD/Enng/zqT5v9Jm+n/HoLi/xJ54P8SeeD/OpPm/wAAAAAAAAAAAAAAAAAAAAAAAAAAzub7/xJ54P8SeeD/Enng/4/D9P/p6en/0tLS/8Tc8P8SeeD/Enng/xJ54P+Pw/T/AAAAAAAAAAAAAAAAAAAAAL3e+v8SeeD/Enng/xJ54P+93vr/Wlpa/zc3N/8AAAAAEnng/xJ54P8SeeD/f7vy/wAAAAAAAAAAAAAAAAAAAAAAAAAAHoLi/xJ54P8SeeD/T3+r/yQkJP9+jpz/Zazv/xJ54P8SeeD/Enng/73e+v8AAAAAAAAAAAAAAAAAAAAAz8Kt/66uof+Gj4L/ho+C/5SKb/+Vh2j/ho+C/4aPgv+Gj4L/ho+C/5OVgv+6qYP/yryi/wAAAAAAAAAAp5BW/6eQVv+nkFb/p5BW/6eQVv+nkFb/p5BW/6eQVv+nkFb/p5BW/6eQVv+nkFb/p5BW/6eQVv8AAAAA6ePb46eQVv+nkFb/p5BW/6eQVv+nkFb/xLWY/8/Crf/Pwq3/vq6N/7qogv+6qIL/uqiC/7qogv+nkFb/5uDW/+bg1v+nkFb/p5BW/6eQVv+nkFb/p5BW/+zn4f///////////8zMzP92dnb/VFRU/9nZ2f//////taJ5/8/Crf/m4Nb/p5BW/6eQVv+nkFb/p5BW/6eQVv/m4Nb////////////MzMz/k5OT/8zMzP/z8/P//////8S1mP/EtZj/5uDW/6eQVv+nkFb/p5BW/6eQVv+nkFb/oZ6Z/5OTk//m5ub/////////////////8/Pz/3Z2dv9xcHD/j4h7/9rRwf+nkFb/p5BW/6eQVv+nkFb/VVNP/8zMzP/z8/P/dnZ2/9nZ2f///////////5OTk//z8/P//////3Rxa//Pwq3/p5BW/6eQVv+nkFb/p5BW/2FgYP///////////76+vv/MzMz///////////+ioqL/oqKi/76+vv91b2X/z8Kt/6eQVv+nkFb/p5BW/6eQVv+JfWX/bGtq/4WFhf+FhYX//////////////////////76+vv++vr7/taJ5/8/Crf+nkFb/p5BW/6eQVv+nkFb/p5BW/8m7ov//////+Pb1/+bg1v/g2Mz/z8Kt/8/Crf+6qIL/uqiC/6eQVv/m4Nb/uqmD/7qpg/+nkFb/p5BW/6eQVv+nkFb/rZZh/7qpg/+/r43/z8Kt/8/Crf/m4NYd5uDWVQAAAAAAAAAA8A8AAOAHAADAAwAAwEMAAOADAADAAQAAgAEAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAMAAA==
[mobileread-url]: https://www.mobileread.com/forums/showthread.php?t=134000

[changelog-image]: https://img.shields.io/badge/History-CHANGELOG-blue.svg
[changelog-url]: CHANGELOG.md

[license-image]: https://img.shields.io/badge/License-GPL-yellow.svg
[license-url]: ../LICENSE.md

[calibre-image]: https://img.shields.io/badge/calibre-2.0.0-green
[calibre-url]: https://www.calibre-ebook.com/

[status-image]: https://img.shields.io/badge/Status-Stable-green
