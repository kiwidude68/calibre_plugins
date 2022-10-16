# Fantastic Fiction Change Log

## [1.6.0] - 2022-10-16
_All kiwidude plugins updated/migrated to: https://github.com/kiwidude68/calibre_plugins_
### Added
- Spanish translation (@dunhill)
- Russian translation (Caarmi)
- Ukranian translation (@yurchor)
### Changed
- **Breaking:** Drop PyQt4 support, require calibre 2.85.1 or later.
- Refactoring of common code
- Removed searching for title + author which always fails, much faster!

## [1.5.1] - 2022-01-05
### Changed
- Make compatible with calibre 6/Qt6. (@davidfor)

## [1.5.0] - 2021-11-28
### Added
- Add Reduce header sizes option to replace h1,h2,h3 tags with h4 in comments (off by default).
- Get the publishing date from the oldest editions. Can be configured on or off.
### Changed
- Fix layout of configuration.
- Code cleanup.
### Fixed
- Titles/authors with apostrophes can result in not finding search matches.

## [1.4.0] - 2020-09-19
### Changed
- Changes for Python 3 support in calibre.
- Handle series index with decimals.

## [1.3.0] - 2018-11-10
### Added
- Add id_from_url for pasting URL and getting an identifier. (@davidfor)
- Add option to keep Genre in the comments.
### Fixed
- Site changed to add Preview button added in comments. Remove this.
- New version of the API.

## [1.2.0] - 2017-05-28
### Changed
- To url https://www.fantasticfiction.com and other changes to the site. (@davidfor)

## [1.1.6] - 2014-10-02
### Fixed
- Updated for website changes

## [1.1.5] - 2014-07-28
### Changed
- Support for upcoming calibre 2.0

## [1.1.4] - 2013-08-17
### Fixed
- For changes to FF website

## [1.1.3] - 2013-07-21
### Fixed
- For change to FF website where not picking up publisher/isbn correctly

## [1.1.2] - 2013-04-16
### Fixed
- For change to FF website where not picking up authors correctly

## [1.1.1] - 2012-06-23
### Fixed
- For further changes to FantasticFiction website for lookups by ISBN

## [1.1.0] - 2012-06-05
### Fixed
- For changes to FantasticFiction website for how to scrape the search results

## [1.0.6] - 2011-07-16
### Fixed
- Support an additional edge case of Genre with a blank comments

## [1.0.5] - 2011-07-16
### Added
- Offer options for what to do with the Genre: addition the Goodreads website now has (discard, tags)

## [1.0.4] - 2011-05-16
### Changed
- For ISBN based lookups, strip any : from title returned to prevent treating as a subtitle
- Strip '?' from title based lookups and the words "A Novel"
- Strip leading "The" from title for ISBN based lookups
- If title/authors returned by FF for ISBN lookup results in no matches, retry with calibre title/authors
- When checking book returned from search is correct, compare with FF isbn and calibre title/authors before rejecting
- Support change to FF website to surround ISBN with `<strong>` tags
### Fixed
- Ensure UTF-8 decoding of search results in case of rare issues
- For rare "url malformed" error when written by multiple authors but only one on FantasticFiction

## [1.0.3] - 2011-05-13
### Changed
- Tweak the logic when searching by ISBN so falls back to use original title/author for search

## [1.0.2] - 2011-05-12
### Changed
- No longer prefix comments for a book with 'SUMMARY:'
### Fixed
- Ensure no issues with no author being specified or no title being specified
- Ensure no series books parsed correctly

## [1.0.1] - 2011-05-12
### Added
- Add support for ISBN based lookups
### Fixed
- Non-ascii title/author names not being parsed correctly
- Re-runnability after a FF id is retrieved

## [1.0.0] - 2011-05-12
_Initial release of plugin_
