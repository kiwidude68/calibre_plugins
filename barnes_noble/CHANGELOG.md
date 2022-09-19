## Release History

**Version 1.4.0** - XX Sep 2022
- New: All kiwidude plugins updated/migrated to: https://github.com/kiwidude68/calibre_plugins
- New: Add Portuguese translations
- Update: Drop PyQt4 support, require calibre 2.x or later.

**Version 1.3.0** - 09 Sep 2022
- New: Add translation support for config screen.
- New: Spanish, French, Japanese, Dutch, Ukranian translations - thanks to everyone!!!
- Update: Remove TOC append option from configuration as not supported by plugin any more.
- Fix: Updated for latest website pages.
- Fix: Support for calibre 6/Qt6.

**Version 1.2.16** - 16 Apr 2020
- Update: Ported to python 3 - author (gbm)

**Version 1.2.15** - 22 Apr 2018
- Update: For changes to B&N website - author (qsxwdc)

**Version 1.2.14** - 01 Aug 2016
- Update: For changes to B&N website - author names (jhowell)

**Version 1.2.13** - 30 Jul 2015
- Update: For changes to B&N website (jhowell)

**Version 1.2.12** - 17 Jul 2014
- Update: For Qt4 and Qt5

**Version 1.2.11** - 08 Sep 2013
- Updated for changes to B&N website

**Version 1.2.10** - 15 Apr 2013
- Fix: The URL hyperlink when clicking from book details panel to reflect changes to website

**Version 1.2.9** - 27 Dec 2012
- Update: For changes to B&N website

**Version 1.2.8** - 01 Jul 2012
- Update: Use a different search URL for title/author searches which seems to give better search results

**Version 1.2.7** - 23 Jun 2012
- Update: Improve the image not available exclusion checking
- Fix: Logic for extracting series from title due to B&N website changes

**Version 1.2.6** - 07 Jun 2012
- Update: Further tweaking to improve matching of search results to match latest website layout

**Version 1.2.5** - 01 Jun 2012
- Update: Improve the title/author matching logic for new website layout
- Update: Ensure "[NOOK Book]" is always stripped from the title

**Version 1.2.4** - 29 Apr 2012
- Update: Ensure the "Image not available" images are excluded

**Version 1.2.3** - 16 Apr 2012
- Update: More B&N website changes - if fallback to title/author search, just use a keyword search
- Update: When matching results for title/author, handle new website page layout

**Version 1.2.2** - 06 Mar 2012
- Update: Fix for change to B&N website affecting the comments field.

**Version 1.2.1** - 25 Nov 2011
- Update: Add back support for the old style website pages as B&N haven't completely migrated yet.

**Version 1.2** - 22 Nov 2011
- Update: Rewritten to support new B&N website for non textbooks

**Version 1.1.3** - 25 Aug 2011
- Update: Change logic for determining image directory to handle smaller numbered images

**Version 1.1.2** - 06 Aug 2011
- Update: Grab the front cover when there are multiple covers available
- Update: Support change to website where wgt-ProductTitle class titles no longer inside a span

**Version 1.1.1** - 16 Jun 2011
- Update: Support additional noresults url location after rewrite when lookup by ISBN
- Update: Alter the details URL looked up to prevent an infinite loop on some books due to B&N website error
- Update: If the main format returned is not acceptable (e.g. Audiobook) look for an "Also Available As:" section
- Update: Reorder priority of matching results to those with shortest titles (to de-prioritise box sets)
- Update: Strip '?' from title based lookups
- Update: For non ascii names, ensure the comparison is done with non-asii equivalents

**Version 1.1** - 05 Jun 2011
- Update: Rewritten to support new B&N website

**Version 1.0.6** - 29 May 2011
- Update: When an ISBN is not directly found, process the search results page

**Version 1.0.5** - 21 May 2011
- Update: Respond to change to website layout which prevented metadata download working

**Version 1.0.4** - 20 May 2011
- New: Add option to append TOC from website Features tab to the comments field (available on B&N Textbooks)

**Version 1.0.3** - 13 May 2011
- Update: Remove some debugging stuff from the log
- Update: Strip hyperlinks text from the comments since these don't get retained and just confuse the output

**Version 1.0.2** - 09 May 2011
- Update: Make sure that Image not available gifs are not returned as fallback covers

**Version 1.0.1** - 09 May 2011
- New: Add "Audio" to list of excluded format types
- New: Add a config option (like Goodreads) to return all contributing authors (off by default)
- Update: Modify prioritisation of results to increase chance of getting a large cover when multiple have covers
- Fix: Multiple authors being returned when they have contribution type in brackets after them

**Version 1.0** - 08 May 2011
- Initial release of plugin
