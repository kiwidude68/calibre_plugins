# Change Log

## [1.7.0] - 2022-09-24
_All kiwidude plugins updated/migrated to: https://github.com/kiwidude68/calibre_plugins_
### Added
- Added configuration option to download precise goodreads rating and review vote count into two identifiers `grrating` and `grvotes`
    - The new identifiers can be bound to custom columns in calibre see `README.md` for details of how.
    - Thanks to Melih for the suggestion!
- Added Russian translations (@Caarmi)
### Changed
- Drop PyQt4 support, require calibre 2.x or later.
- Refactoring of common code

## [1.6.2] - 2022-09-08
### Added
- Add translation support for config screen.
- Chinese, Spanish, French, Hungarian, Italian, Japanese, Dutch, Polish, Ukranian translations - thanks to everyone!!!

## [1.6.1] - 2022-09-06
### Added
- Add configuration option to use edition published date or first published date (default).
### Fixed
- Remove debug code, fixes for isbn, publication date and series index when multiple series.

## [1.6.0] - 2022-09-03
### Changed
- Support new Goodreads web page formats in conjunction with legacy pages.

## [1.5.3] - 2022-01-05
### Changed
- Cleanup in preparation for calibre 6/Qt6. (@davidfor)

## [1.5.2] - 2020-11-30
### Fixed
- Use mobi-asin identifier  (@davidfor)

## [1.5.1] - 2020-09-25
### Added
- Czech translation (@seeder)
- Add download page count from databazeknih.cz and cbdb.cz (@seeder)
### Fixed
- Wasn't getting the series info.

## [1.5.0] - 2020-09-19
### Changed
- Changes for Python 3 support in calibre. (@davidfor)
### Fixed
- Small error in handling editions.

## [1.4.0] - 2018-12-20
### Fixed
- Site change for rating. (@davidfor)
- Add extra attempt to convert language name to code.

## [1.3.0] - 2018-11-10
### Added
- Add get_book_url for pasting URL and getting an identifier. (@davidfor)
### Changed
- Generate HTTPS URL for identifier.

## [1.2.0] - 2018-10-23
### Added
- Add search by ASIN or other Amazon id if it exists. (@davidfor)
- Use auto_complete API for ISBN and ASIN search. Based on code from MR user botmtl. 

## [1.1.17] - 2018-10-13
### Fixed
- Changes in search page plus fixing issue with scanning editions. (@davidfor)

## [1.1.16] - 2018-10-03
### Added
- Get the ASIN if the book is am Amazon edition. There is an option to turn this on. It is off by default. (@davidfor, @Iceybones)
### Changed
- Checks through the search results for a match to the title and author.
### Fixed
- Series separated from the title.

## [1.1.14] - 2018-04-17
### Fixed
- Change in search page. (@davidfor)

## [1.1.13] - 2017-12-17
### Fixed
- Normalize title to solve issues with accented characters. (@davidfor)

## [1.1.12] - 2016-12-30
### Fixed
- Ratings were not always being retrieved properly. (@davidfor)

## [1.1.11] - 2016-02-08
### Fixed
- Site changes for the description/comments. (@davidfor)
- Site and option changes for genre and classification. 

## [1.1.10] - 2015-10-26
### Fixed
- Site changes for the description/comments.

## [1.1.9] - 2015-07-11
### Fixed
- Do not change case of tags downloaded, so YA stays as YA.

## [1.1.8] - 2014-07-08
### Changed
- Change to allow Qt4 or Qt5.

## [1.1.7] - 2013-08-25
### Fixed
- For more.../less... on authors

## [1.1.6] - 2013-08-17
### Added
- Support Dutch language

## [1.1.5] - 2013-07-10
### Fixed
- Updated to match Goodreads website change which broke ISBB and cover parsing

## [1.1.4] - 2013-03-04
### Fixed
- Goodreads change for when large number of authors to ensure more.../less... is removed correctly

## [1.1.3] - 2012-12-28
### Added
- Support for "languages" metadata field
### Fixed
- Get all contributing authors option

## [1.1.2] - 2012-06-23
### Fixed
- Reject editions that do not match in title (such as different languages) and handle non-ascii characters better
- Handle books with short descriptions since Goodreads website change

## [1.1.1] - 2012-06-12
### Fixed
- Match Goodreads website change which stopped tags being downloaded
- Change to the comments to no longer strip paragraph breaks

## [1.1.0] - 2012-0303
### Fixed
- The "Scan multiple editions for title/author searches" option broken from Goodreads website change

## [1.0.9] - 2011-11-14
### Added
- Support case insensitive comparisons of genre tag mappings
- Allow renaming an item changing only case
### Changed
- When sorting to display the mappings in the config screen, ignore case

## [1.0.8] - 2011-10-25
### Fixed
- If large number of authors, ensure more... and ...less is stripped from authors results.

## [1.0.7] - 2011-08-10
### Fixed
- Ensure a "close but not quite" series # does not throw an error within the plugin.

## [1.0.6] - 2011-06-21
### Fixed
- Handle change to Goodreads website which prevented title/author results returning

## [1.0.5] - 2011-05-12
### Changed
- Ensure any covers less than 1000 bytes in size are ignored.
- No longer prefix the comments with SUMMARY: in output for consistency with other plugins

## [1.0.4] - 2011-05-08
### Changed
- Remove code supporting versions prior to 0.8
- Strip trailing comma from series name if it exists
- Put summary comments on line following the word SUMMARY: rather than on same line.

## [1.0.3] - 2011-04-29
### Fixed
- Ensure non ascii author names are parsed correctly.

## [1.0.2] - 2011-04-26
### Fixed
- Properly fix the ordering of tags.

## [1.0.1] - 2011-04-25
### Changed
- Support for API change upcoming in Calibre 0.7.58 allowing hyperlinked ids in book details panel
### Fixed
- Ensure tags mapped are returned by order of popularity not alphabetically so applying a tag threshold works better

## [1.0.0] - 2011-04-23
_Initial release of plugin, rewritten consolidation of Goodreads Metadata and Goodreads Covers plugins_
