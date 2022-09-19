# Find Duplicates Plugin
[![MobileRead][mobileread-image]][mobileread-url]
[![History][changelog-image]][changelog-url] 
[![License][license-image]][license-url]
[![calibre Version][calibre-image]][calibre-url]
[![Status][status-image]][status-image] 

## Overview

This plugin will help you to identify duplicate authors, titles, formats, series, publishers, tags and identifiers in your Calibre libraries.

- **Duplicate authors** are where you have multiple variants of an author due to spacing, punctuation, spelling differences or word order. e.g. Kevin Anderson / Kevin J. Anderson / Keven Anderson / Anderson, Kevin / Anderson Kevin / Bloggs, Joe & Anderson, Kevin
- **Duplicate titles** are where you have multiple book entries with either the same or varying titles. e.g. Martian Way / The Martian Way / The Martian Way (2010) / The Martian Way and Other Stories
- **Duplicate formats** are where the contents of a particular format like ePub are binary identical to another in your library

The plugin offers a variety of matching algorithms for finding possible groups of duplicate candidates. Each algorithm combination provides a differing trade-off of the number of genuine duplicates found versus the number of false positives (near duplicates).

When the search is complete the results of each group are presented to you to navigate through. You can then do one of three things:

- If the group contains genuine duplicates, use the existing Merge feature in the Edit metadata menu to resolve the duplicate book entries.
- If the group contains non duplicates, you can mark the group as exempt to prevent those books or authors from appearing together in future searches.
- Skip the group for now and just move to the next one, either deferring your decision or to mark all remaining groups as exemptions when finished.

New to version 1.4 is a "Find metadata variations" menu which allows you to find variations of author, publisher, series and tag names and rename directly on this dialog. Again a number of different matching algorithms are available for use.

Version 1.5 has added the ability to perform duplicate comparisons across multiple libraries. So for instance if you have a "working" library and a "main" library, you can search for duplicates between those libraries with the same range of algorithms and produce a report for later resolution.

Version 1.8 adds a new advanced mode which offers more flexibility and options, you can read more on that [here][advanced-url]. 

## Main Features

- Searches either your entire library or respecting any search restriction set at the time you Find Duplicates.
- Choose your desired combination of title and author matching from any of "identical", "similar", "soundex", "fuzzy" or "ignore" algorithms.
- Choose alternative algorithms such as matching identifiers or binary comparison.
- View the results either one group at a time, or showing all duplicate candidates at once using highlighting to show the groups.
- When doing author duplicate searches (ignore title), optionally highlight the authors under consideration in the tag browser for ease of renaming
- Sort the result groups either by title/author (default) or by the size of the group
- Fine tune the soundex algorithm options to make them "fuzzier" or more explicit matching.
- Optionally include the languages field when comparing titles, so intentionally using the same book title in different languages does not show as duplicates.
- Optionally have binary duplicate formats automatically removed from your library when doing a binary comparison.
- Mark the current group as exempt or all groups as exempt from appearing as duplicates again
- Review your duplicate exemptions with the opportunity to reverse the exemption allowing duplicate consideration again
- Exempt either individual books (title searches) or authors (author searches)
- Clicking the clear search button, setting a different restriction or choosing an explicit Clear duplicate results menu option will exit duplicate search mode.
- Switching libraries or restarting Calibre will also clear any duplicate search results. Your exemptions will be remember and are stored per library.
- Customize the keyboard shortcuts for a number of the menu options.
- Find metadata variations for authors, publishers, series and tags to eradicate unwanted duplicates with an alternative simplified UI to rename them.
- Find duplicates across multiple libraries, producing a report.
- When placed on the toolbar, clicking the toolbar button without duplicate groups displayed will display the Find Duplicates options dialog. When results are displayed, clicking on the button will move to the next result. Ctrl+click or shift+click to navigate to the previous result.
- Use delete key to remove entry from library list in cross library search options.
- New Advanced Mode: It allows the user to match books without restrictions on the type nor the number of columns used. It also allows for user defined algorithms by using templates. It comes with a sort dialog allowing you to sort books based on columns and templates. To complement the sort feature, it adds extra marks to first and last books in each duplicate group: "first_duplicate", "last_duplicate". You can find more on that [here][advanced-url].

## Development / Contributions

All kiwidude's calibre plugins are now developed and maintained in GitHub at:
- https://github.com/kiwidude68/calibre_plugins

Please see the README.md and CONTRIBUTING.md at the above site for more information.


[advanced-url]: https://www.mobileread.com/forums/showpost.php?p=4021095&postcount=738

[mobileread-image]: https://img.shields.io/badge/MobileRead-Plugin%20Thread-blue?logo=data:image/x-icon;base64,AAABAAEAEBAAAAEAIABoBAAAFgAAACgAAAAQAAAAIAAAAAEAIAAAAAAAQAQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAns32/zqT5v8SeeD/Enng/xJ54P8SeeD/LYvl/3+78v8AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAZazv/xJ54P8SeeD/Enng/zqT5v9Jm+n/HoLi/xJ54P8SeeD/OpPm/wAAAAAAAAAAAAAAAAAAAAAAAAAAzub7/xJ54P8SeeD/Enng/4/D9P/p6en/0tLS/8Tc8P8SeeD/Enng/xJ54P+Pw/T/AAAAAAAAAAAAAAAAAAAAAL3e+v8SeeD/Enng/xJ54P+93vr/Wlpa/zc3N/8AAAAAEnng/xJ54P8SeeD/f7vy/wAAAAAAAAAAAAAAAAAAAAAAAAAAHoLi/xJ54P8SeeD/T3+r/yQkJP9+jpz/Zazv/xJ54P8SeeD/Enng/73e+v8AAAAAAAAAAAAAAAAAAAAAz8Kt/66uof+Gj4L/ho+C/5SKb/+Vh2j/ho+C/4aPgv+Gj4L/ho+C/5OVgv+6qYP/yryi/wAAAAAAAAAAp5BW/6eQVv+nkFb/p5BW/6eQVv+nkFb/p5BW/6eQVv+nkFb/p5BW/6eQVv+nkFb/p5BW/6eQVv8AAAAA6ePb46eQVv+nkFb/p5BW/6eQVv+nkFb/xLWY/8/Crf/Pwq3/vq6N/7qogv+6qIL/uqiC/7qogv+nkFb/5uDW/+bg1v+nkFb/p5BW/6eQVv+nkFb/p5BW/+zn4f///////////8zMzP92dnb/VFRU/9nZ2f//////taJ5/8/Crf/m4Nb/p5BW/6eQVv+nkFb/p5BW/6eQVv/m4Nb////////////MzMz/k5OT/8zMzP/z8/P//////8S1mP/EtZj/5uDW/6eQVv+nkFb/p5BW/6eQVv+nkFb/oZ6Z/5OTk//m5ub/////////////////8/Pz/3Z2dv9xcHD/j4h7/9rRwf+nkFb/p5BW/6eQVv+nkFb/VVNP/8zMzP/z8/P/dnZ2/9nZ2f///////////5OTk//z8/P//////3Rxa//Pwq3/p5BW/6eQVv+nkFb/p5BW/2FgYP///////////76+vv/MzMz///////////+ioqL/oqKi/76+vv91b2X/z8Kt/6eQVv+nkFb/p5BW/6eQVv+JfWX/bGtq/4WFhf+FhYX//////////////////////76+vv++vr7/taJ5/8/Crf+nkFb/p5BW/6eQVv+nkFb/p5BW/8m7ov//////+Pb1/+bg1v/g2Mz/z8Kt/8/Crf+6qIL/uqiC/6eQVv/m4Nb/uqmD/7qpg/+nkFb/p5BW/6eQVv+nkFb/rZZh/7qpg/+/r43/z8Kt/8/Crf/m4NYd5uDWVQAAAAAAAAAA8A8AAOAHAADAAwAAwEMAAOADAADAAQAAgAEAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAMAAA==
[mobileread-url]: https://www.mobileread.com/forums/showthread.php?t=131017

[changelog-image]: https://img.shields.io/badge/History-CHANGELOG-blue.svg
[changelog-url]: CHANGELOG.md

[license-image]: https://img.shields.io/badge/License-GPL-yellow.svg
[license-url]: ../LICENSE.md

[calibre-image]: https://img.shields.io/badge/calibre-2.0.0-green
[calibre-url]: https://www.calibre-ebook.com/

[status-image]: https://img.shields.io/badge/Status-Stable-green
