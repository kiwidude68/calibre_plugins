# Barnes & Noble Change Log

## [1.5.0] - 2023-04-02
### Changed
- B&N identifier now just using the numeric store value alone, without the sub-page prefix.
### Fixed
- Configuration screen broken from removal of TOC feature. (aragonit)

## [1.4.0] - 2022-10-16
### Added
- All kiwidude plugins updated/migrated to: https://github.com/kiwidude68/calibre_plugins
- Portuguese translation (Comfy.n)
- Polish translation (moje konto)
### Changed
- **Breaking:** Drop PyQt4 support, require calibre 2.x or later.

## [1.3.0] - 2022-09-09
### Added
- Add translation support for config screen.
- Spanish, French, Japanese, Dutch, Ukranian translations - thanks to everyone!!!
### Changed
- Remove TOC append option from configuration as not supported by plugin any more.
### Fixed
- Updated for latest website pages.
- Support for calibre 6/Qt6.

## [1.2.16] - 2020-04-16
### Changed
- Ported to python 3 - author (gbm)

## [1.2.15] - 2018-04-22
### Changed
- For changes to B&N website - author (qsxwdc)

## [1.2.14] - 2016-08-01
### Changed
- For changes to B&N website - author names (jhowell)

## [1.2.13] - 2015-07-30
### Changed
- For changes to B&N website (jhowell)

## [1.2.12] - 2014-07-17
### Changed
- For Qt4 and Qt5

## [1.2.11] - 2013-09-08
### Changed
- Updated for changes to B&N website

## [1.2.10] - 2013-04-15
### Fixed
- The URL hyperlink when clicking from book details panel to reflect changes to website

## [1.2.9] - 2012-12-27
### Changed
- For changes to B&N website

## [1.2.8] - 2012-07-01
### Changed
- Use a different search URL for title/author searches which seems to give better search results

## [1.2.7] - 2012-06-23
### Changed
- Improve the image not available exclusion checking
### Fixed
- Logic for extracting series from title due to B&N website changes

## [1.2.6] - 2012-06-07
### Changed
- Further tweaking to improve matching of search results to match latest website layout

## [1.2.5] - 2012-06-01
### Changed
- Improve the title/author matching logic for new website layout
- Ensure "[NOOK Book]" is always stripped from the title

## [1.2.4] - 2012-04-29
### Changed
- Ensure the "Image not available" images are excluded

## [1.2.3] - 2012-04-16
### Changed
- More B&N website changes - if fallback to title/author search, just use a keyword search
- When matching results for title/author, handle new website page layout

## [1.2.2] - 2012-03-06
### Changed
- Fix for change to B&N website affecting the comments field.

## [1.2.1] - 2011-11-25
### Changed
- Add back support for the old style website pages as B&N haven't completely migrated yet.

## [1.2.0] - 2011-11-22
### Changed
- Rewritten to support new B&N website for non textbooks

## [1.1.3] - 2011-08-25
### Changed
- Change logic for determining image directory to handle smaller numbered images

## [1.1.2] - 2011-08-06
### Changed
- Grab the front cover when there are multiple covers available
- Support change to website where wgt-ProductTitle class titles no longer inside a span

## [1.1.1] - 2011-06-16
### Changed
- Support additional noresults url location after rewrite when lookup by ISBN
- Alter the details URL looked up to prevent an infinite loop on some books due to B&N website error
- If the main format returned is not acceptable (e.g. Audiobook) look for an "Also Available As:" section
- Reorder priority of matching results to those with shortest titles (to de-prioritise box sets)
- Strip '?' from title based lookups
- For non ascii names, ensure the comparison is done with non-asii equivalents

## [1.1.0] - 2011-06-05
### Changed
- Rewritten to support new B&N website

## [1.0.6] - 2011-05-29
### Changed
- When an ISBN is not directly found, process the search results page

## [1.0.5] - 2011-05-21
### Changed
- Respond to change to website layout which prevented metadata download working

## [1.0.4] - 2011-05-20
### Added
- Add option to append TOC from website Features tab to the comments field (available on B&N Textbooks)

## [1.0.3] - 2011-05-13
### Changed
- Remove some debugging stuff from the log
- Strip hyperlinks text from the comments since these don't get retained and just confuse the output

## [1.0.2] - 2011-05-09
### Changed
- Make sure that Image not available gifs are not returned as fallback covers

## [1.0.1] - 2011-05-09
### Added
- Add "Audio" to list of excluded format types
- Add a config option (like Goodreads) to return all contributing authors (off by default)
### Changed
- Modify prioritisation of results to increase chance of getting a large cover when multiple have covers
### Fixed
- Multiple authors being returned when they have contribution type in brackets after them

## [1.0.0] - 2011-05-08
_Initial release of plugin_
