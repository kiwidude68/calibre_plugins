# Quality Check Plugin
[![MobileRead][mobileread-image]][mobileread-url]
[![History][changelog-image]][changelog-url] 
[![License][license-image]][license-url]
[![calibre Version][calibre-image]][calibre-url]
[![Status][status-image]][status-image] 

## Overview

This plugin is intended to help you identify covers or book metadata that may need editing in your library that the normal calibre search criteria cannot identify, or is more conveniently accessible. It also offers a battery of ePub quality checks to help you identify ePubs that may warrant further attention to remove cruft files, reconvert etc. You can also search across your ePubs for ad hoc criteria to find text or specifically named items using regular expressions.

Amazon Fire users will find the Mobi checks useful to identify books which will not show in the correct folder due to internal metadata issues with the ASIN or cdetype.

For the OCD types, this plugin can be used to find books that need better quality covers based on physical or file size to be sourced to replace those in your library currently.

You may have noticed when editing individual books in the Edit Metadata screen that your book has a red colored background field indicating a potential problem. This plugin allows you to bulk find all such books in your library so that you can resolve any issues such as by using the bulk metadata edit dialog. A separate "Check missing" menu offers a quick way to serch for common missing data without having to remember calibre's search syntax.

## Main Features

- Find ePub formats that have one, multiple, legacy or no jackets. Legacy jackets are from calibre conversions prior to 0.6.50 which will result in duplicated jackets if you convert again.
- Find ePub formats that are invalid due to a missing container.xml file
- Find ePub formats with invalid namespaces specified in the container or opf manifest
- Find ePub formats that have non dc: namespace elements in the manifest
- Find ePub formats that have files listed in the .opf manifest that are not in the ePub file
- Find ePub formats that have files in the ePub that are not included in the .opf manifest
- Find ePub formats that have CSS files in the ePub manifest that are not used from the html content
- Find ePub formats that have unused image files that can be safely deleted
- Find ePub formats that have iTunes plist or artwork files from viewing the ePub in iTunes
- Find ePub formats that have calibre bookmarks files from the calibre ebook viewer
- Find ePub formats that have OS artifacts like .DS_Store or Thumbs.db
- Find ePub formats that have an NCX TOC that is hierarchical
- Find ePub formats that have an NCX TOC with < 3 entries
- Find ePub formats that have an NCX TOC with broken link entries
- Find ePub formats that have broken &lt;guide&gt; references in the manifest
- Find ePub formats that have html files larger than 260KB requiring splitting
- Find ePub formats that have DRM
- Find ePub formats that have Adobe DRM &lt;meta&gt; tags
- Find ePub formats that have or do not have a cover that is replaceable when exporting from calibre
- Find ePub formats that have or do not have SVG covers created by calibre
- Find ePub formats that have or have not been converted using calibre
- Find ePub formats that have &lt;address&gt; smart tags which corrupt readability
- Find ePub formats that have embedded fonts
- Find ePub formats that have @font-face declarations in CSS or html files
- Find ePub formats that have Adobe .xpgt files with margins specified
- Find ePub formats that have Adobe inline .xpgt links in the html files
- Find ePub formats that have are left or unjustified i.e. no CSS file containing text-align:justify
- Find ePub formats that have book margins different to your calibre defaults
- Find ePub formats that have no book margins defined
- Find ePub formats that have inline margins defined on the content files
- Find ePub formats that have javascript files or &lt;script&gt; blocks
- Find ePub formats that have unsmartened punctuation
- Search the contents of ePub formats for ad hoc regular expressions of your own
- Find Mobi/AZW/AZW3 formats that will not show in the documents folder on an Amazon Fire due to cdetype or ASIN missing/incorrect (with a Fix option below).
- Find Mobi/AZW/AZW3 formats that have their Facebook/Twitter sharing disable on an Amazon Fire (with a Fix option below)
- Find Mobi/AZW/AZW3 formats that have publisher imposed limits on the amount of text that can be placed in clipping notes when read on a Kindle.
- Find books that have covers based on a choice of criteria such as file size or dimensions
- Find books with an invalid title sort
- Find books with an invalid author sort
- Find books with an invalid ISBN
- Find books with an invalid pubdate (equal to date timestamp)
- Find books with a duplicate ISBN
- Find books with a duplicate series
- Find books with a series gap
- Find books with a series numbering that does not match the published date
- Find books with more than a specified number of tags
- Find books with comments that have HTML style tags embedded like bold or italic
- Find books with comments that have no HTML tags at all
- Find books with commas in the author (useful if your author is FN LN)
- Find books with no commas in the author (useful if your author is LN, FN)
- Find books with authors that are all upper or all lower case
- Find books with authors that contain non-alphabetic characters like incorrect separators or cruft
- Find books with authors that contain non-ascii characters of accents/diacritics
- Find books with authors that have initials in a different punctuation to your preference
- Find books with titles that have possible series info like hyphens/numerics
- Find books with titles that do not appear to be a valid title case
- Search for books missing metadata, such as titles, authors, isbn, pubdate, publisher, tags, rating, comments, languages, cover or formats.
- Change the search scope to either search your entire library (respecting search restrictions) or only your selected book(s).
- Swap author names for the selected book(s) between FN LN and LN, FN order or vice versa
- Fix author initials for selected books to your preferred naming format
- Rename author names for selected books to replace non-ascii characters
- Find and fix the file sizes stored for a book format (useful if you edit books outside of calibre)
- Find and fix folder/file paths that are missing commas for inconsistencies within a library for books added after calibre 0.8.35
- Cleanup orphaned opf/jpg files/folders resulting from using Save to Disk followed by Remove from device. Do NOT ever run this against a calibre library folder, it is intended for external save to disk/device folders only.
- Fix Mobi/AZW/AZW3 files for a Kindle Fire to insert an ASIN and set the correct cdetype in the internal data to enable sharing and appear in the correct folder
- Ability to add books to an exclusion list for a particular quality check, if you intentionally want to exempt them. You can view and edit your exclusion lists.
- Customise the menus to hide items not of interest

## Configuration Options

| Option  | Description |
| --------| ----------- |
| Maximum tags | For the "Check excess tags" check, how many tags maximum to allow.
| Exclude tags | For the "Check excess tags" check, ignore these tags when counting how many a book has.
| Author initials format | For author related checks/fixes, specify your desired initial format/spacing.
| Visible Menus | Control which menu options to appear in the plugin main menu.

## Development / Contributions

All kiwidude's calibre plugins are now developed and maintained in GitHub at:
- https://github.com/kiwidude68/calibre_plugins

Please see the README.md and CONTRIBUTING.md at the above site for more information.


[mobileread-image]: https://img.shields.io/badge/MobileRead-Plugin%20Thread-blue?logo=data:image/x-icon;base64,AAABAAEAEBAAAAEAIABoBAAAFgAAACgAAAAQAAAAIAAAAAEAIAAAAAAAQAQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAns32/zqT5v8SeeD/Enng/xJ54P8SeeD/LYvl/3+78v8AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAZazv/xJ54P8SeeD/Enng/zqT5v9Jm+n/HoLi/xJ54P8SeeD/OpPm/wAAAAAAAAAAAAAAAAAAAAAAAAAAzub7/xJ54P8SeeD/Enng/4/D9P/p6en/0tLS/8Tc8P8SeeD/Enng/xJ54P+Pw/T/AAAAAAAAAAAAAAAAAAAAAL3e+v8SeeD/Enng/xJ54P+93vr/Wlpa/zc3N/8AAAAAEnng/xJ54P8SeeD/f7vy/wAAAAAAAAAAAAAAAAAAAAAAAAAAHoLi/xJ54P8SeeD/T3+r/yQkJP9+jpz/Zazv/xJ54P8SeeD/Enng/73e+v8AAAAAAAAAAAAAAAAAAAAAz8Kt/66uof+Gj4L/ho+C/5SKb/+Vh2j/ho+C/4aPgv+Gj4L/ho+C/5OVgv+6qYP/yryi/wAAAAAAAAAAp5BW/6eQVv+nkFb/p5BW/6eQVv+nkFb/p5BW/6eQVv+nkFb/p5BW/6eQVv+nkFb/p5BW/6eQVv8AAAAA6ePb46eQVv+nkFb/p5BW/6eQVv+nkFb/xLWY/8/Crf/Pwq3/vq6N/7qogv+6qIL/uqiC/7qogv+nkFb/5uDW/+bg1v+nkFb/p5BW/6eQVv+nkFb/p5BW/+zn4f///////////8zMzP92dnb/VFRU/9nZ2f//////taJ5/8/Crf/m4Nb/p5BW/6eQVv+nkFb/p5BW/6eQVv/m4Nb////////////MzMz/k5OT/8zMzP/z8/P//////8S1mP/EtZj/5uDW/6eQVv+nkFb/p5BW/6eQVv+nkFb/oZ6Z/5OTk//m5ub/////////////////8/Pz/3Z2dv9xcHD/j4h7/9rRwf+nkFb/p5BW/6eQVv+nkFb/VVNP/8zMzP/z8/P/dnZ2/9nZ2f///////////5OTk//z8/P//////3Rxa//Pwq3/p5BW/6eQVv+nkFb/p5BW/2FgYP///////////76+vv/MzMz///////////+ioqL/oqKi/76+vv91b2X/z8Kt/6eQVv+nkFb/p5BW/6eQVv+JfWX/bGtq/4WFhf+FhYX//////////////////////76+vv++vr7/taJ5/8/Crf+nkFb/p5BW/6eQVv+nkFb/p5BW/8m7ov//////+Pb1/+bg1v/g2Mz/z8Kt/8/Crf+6qIL/uqiC/6eQVv/m4Nb/uqmD/7qpg/+nkFb/p5BW/6eQVv+nkFb/rZZh/7qpg/+/r43/z8Kt/8/Crf/m4NYd5uDWVQAAAAAAAAAA8A8AAOAHAADAAwAAwEMAAOADAADAAQAAgAEAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAMAAA==
[mobileread-url]: https://www.mobileread.com/forums/showthread.php?t=125428

[changelog-image]: https://img.shields.io/badge/History-CHANGELOG-blue.svg
[changelog-url]: CHANGELOG.md

[license-image]: https://img.shields.io/badge/License-GPL-yellow.svg
[license-url]: ../LICENSE.md

[calibre-image]: https://img.shields.io/badge/calibre-3.41.0-green
[calibre-url]: https://www.calibre-ebook.com/

[status-image]: https://img.shields.io/badge/Status-Stable-green