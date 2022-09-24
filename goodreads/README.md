# Goodreads Plugin
[![MobileRead][mobileread-image]][mobileread-url]
[![History][changelog-image]][changelog-url] 
[![License][license-image]][license-url]
[![calibre Version][calibre-image]][calibre-url]
[![Status][status-image]][status-image] 

## Overview

This plugin allows Calibre to read book information from [goodreads.com](https://www.goodreads.com/) when you choose to download/fetch metadata. Calibre comes with a number of built-in plugins for a number of information sources such as Amazon and Googlebooks. Adding this plugin can potentially increase both the success rate and quality of information retrieved for some of your books.

## Main Features

- Can retrieve goodreads id, title, author, series, isbn, comments, rating, publisher, publication date, tags, language and covers.
- Option to retrieve the precise rating and # votes into identifiers than can be bound to custom columns.
- Option to customise the Goodreads genre -> Calibre tag mappings. A default set of the most popular genre tag mappings is included as a starting point.
- Option to additionally search multiple editions of a book for the best set of metadata excluding audio editions (plugin will run slightly slower with this enabled, disabled by default).
- Option to retrieve all contributors to a book as an author. By default this is turned off, however Goodreads is able to provide illustrators, editors etc should you want these retrieved.
- By retrieving the Goodreads id this plugin offers improved integration with the **Goodreads Sync** plugin. This works both ways - once you have linked to a specific Goodreads edition then retrieving metadata will obtain it for only that edition.
- The goodreads id will also be displayed in the book details panel to be clicked on and taken directly to the website for that book.


## Configuration Options

| Option  |Description |
| ------| ----------- |
| Scan multiple editions for title/author searches | By default the first match from the Goodreads search is used.<br>Historically this edition was often an audiobook which may not contain ideal metadata.<br>Enabling this option will ensure audiobook editions are skipped, but will take longer to retrieve. |
| Get all contributing authors | Some books will have many authors listed.<br>Default behavior (unchecked) is to get only the authors who have a profile on Goodreads. |
| Get ASIN for kindle editions | If checked, will try to read the mobi-asin (Amazon) identifier in the returned metadata.<br>This is in addition to the goodreads identifier. |
| Use first published date | Books will usually have multiple dates - when first published and specific edition.<br>When checked (default) will return the first published date ignoring edition date.
| Get rating count into grrating identifier | Optionally create a `grrating` identifier containing a more precise rating.<br>e.g. `grrating:3.78` which can be bound to a custom column.<br>By default this feature is unchecked.
| Get # votes into grvotes identifier | Optionally create a `grvotes` identifier containing rating votes.<br>e.g. `grvotes:12345` which can be bound to a custom column.<br>By default this feature is unchecked.


## Displaying Goodreads Rating / #Votes in Custom Columns

By default calibre rounds up a rating to display it as a number of stars. However some users want something more detailed - there can be a perceived difference between 3.6 and 4.4, but calibre will display both as 4 stars. 

Similarly calibre also has no default column for the # votes that make up the weighting for that rating. An average rating based on many thousands of votes could be considered more balanced than one that has only a few hundred.

You can download the rating count/votes into the identifiers for a book using the metadata configuration options above for the Goodreads plugin. The following instructions will allow you to then display these as calibre columns in your library.

### Adding a Goodreads Rating column

- **Preferences -> Interface -> Add your own columns**
- Click on `+` button then set at least the following

| Field | Value | Comments |
| ----- | ----- | -------- |
| Lookup name: | grrating | Suggested value only, you can customise
| Column heading: | GR | Suggested value only, you can customise
| Column type: | `Column built from other columns` | Mandatory
| Template: | `{identifiers:select(grrating)}` | Mandatory
| Sort/search column by | `Number` | Mandatory

### Adding a Goodreads Votes column

- **Preferences -> Interface -> Add your own columns**
- Click on `+` button then set at least the following:

| Field | Value | Comments |
| ----- | ----- | -------- |
| Lookup name: | grvotes | Suggested value only, you can customise
| Column heading: | GR # | Suggested value only, you can customise
| Column type: | `Column built from other columns` | Mandatory
| Template: | `{identifiers:select(grvotes)}` | Mandatory
| Sort/search column by | `Number` | Mandatory

After adding your column(s), click Apply and restart calibre.


## Development / Contributions

All kiwidude's calibre plugins are now developed and maintained in GitHub at:
- https://github.com/kiwidude68/calibre_plugins

Please see the README.md and CONTRIBUTING.md at the above site for more information.


[mobileread-image]: https://img.shields.io/badge/MobileRead-Plugin%20Thread-blue?logo=data:image/x-icon;base64,AAABAAEAEBAAAAEAIABoBAAAFgAAACgAAAAQAAAAIAAAAAEAIAAAAAAAQAQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAns32/zqT5v8SeeD/Enng/xJ54P8SeeD/LYvl/3+78v8AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAZazv/xJ54P8SeeD/Enng/zqT5v9Jm+n/HoLi/xJ54P8SeeD/OpPm/wAAAAAAAAAAAAAAAAAAAAAAAAAAzub7/xJ54P8SeeD/Enng/4/D9P/p6en/0tLS/8Tc8P8SeeD/Enng/xJ54P+Pw/T/AAAAAAAAAAAAAAAAAAAAAL3e+v8SeeD/Enng/xJ54P+93vr/Wlpa/zc3N/8AAAAAEnng/xJ54P8SeeD/f7vy/wAAAAAAAAAAAAAAAAAAAAAAAAAAHoLi/xJ54P8SeeD/T3+r/yQkJP9+jpz/Zazv/xJ54P8SeeD/Enng/73e+v8AAAAAAAAAAAAAAAAAAAAAz8Kt/66uof+Gj4L/ho+C/5SKb/+Vh2j/ho+C/4aPgv+Gj4L/ho+C/5OVgv+6qYP/yryi/wAAAAAAAAAAp5BW/6eQVv+nkFb/p5BW/6eQVv+nkFb/p5BW/6eQVv+nkFb/p5BW/6eQVv+nkFb/p5BW/6eQVv8AAAAA6ePb46eQVv+nkFb/p5BW/6eQVv+nkFb/xLWY/8/Crf/Pwq3/vq6N/7qogv+6qIL/uqiC/7qogv+nkFb/5uDW/+bg1v+nkFb/p5BW/6eQVv+nkFb/p5BW/+zn4f///////////8zMzP92dnb/VFRU/9nZ2f//////taJ5/8/Crf/m4Nb/p5BW/6eQVv+nkFb/p5BW/6eQVv/m4Nb////////////MzMz/k5OT/8zMzP/z8/P//////8S1mP/EtZj/5uDW/6eQVv+nkFb/p5BW/6eQVv+nkFb/oZ6Z/5OTk//m5ub/////////////////8/Pz/3Z2dv9xcHD/j4h7/9rRwf+nkFb/p5BW/6eQVv+nkFb/VVNP/8zMzP/z8/P/dnZ2/9nZ2f///////////5OTk//z8/P//////3Rxa//Pwq3/p5BW/6eQVv+nkFb/p5BW/2FgYP///////////76+vv/MzMz///////////+ioqL/oqKi/76+vv91b2X/z8Kt/6eQVv+nkFb/p5BW/6eQVv+JfWX/bGtq/4WFhf+FhYX//////////////////////76+vv++vr7/taJ5/8/Crf+nkFb/p5BW/6eQVv+nkFb/p5BW/8m7ov//////+Pb1/+bg1v/g2Mz/z8Kt/8/Crf+6qIL/uqiC/6eQVv/m4Nb/uqmD/7qpg/+nkFb/p5BW/6eQVv+nkFb/rZZh/7qpg/+/r43/z8Kt/8/Crf/m4NYd5uDWVQAAAAAAAAAA8A8AAOAHAADAAwAAwEMAAOADAADAAQAAgAEAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAMAAA==
[mobileread-url]: https://www.mobileread.com/forums/showthread.php?t=130638

[changelog-image]: https://img.shields.io/badge/History-CHANGELOG-blue.svg
[changelog-url]: CHANGELOG.md

[license-image]: https://img.shields.io/badge/License-GPL-yellow.svg
[license-url]: ../LICENSE.md

[calibre-image]: https://img.shields.io/badge/calibre-2.0.0-green
[calibre-url]: https://www.calibre-ebook.com/

[status-image]: https://img.shields.io/badge/Status-Stable-green