## Release History

**Version 1.6.0** - xx Sep 2022
- New: All kiwidude plugins updated/migrated to: https://github.com/kiwidude68/calibre_plugins
- Update: Drop PyQt4 support, require calibre 2.85.1 or later.
- Update: Refactoring of common code

**Version 1.5.1** - 05 Jan 2022
- Update: Make compatible with calibre 6/Qt6.

**Version 1.5.0** - 28 Nov 2021
- New: Add Reduce header sizes option to replace h1,h2,h3 tags with h4 in comments (off by default). Done by @kiwidude.
- New: Get the publishing date from the oldest editions. Can be configured on or off.
- Update: Fix layout of configuration.
- Update: Code cleanup.
- Fix: Titles/authors with apostrophes can result in not finding search matches. Done by @kiwidude.

**Version 1.4.0** - 19 Sep 2020
- Update: Changes for Python 3 support in calibre.
- Update: Handle series index with decimals.

**Version 1.3.0** - 10 Nov 2018 - by davidfor
- New: Add id_from_url for pasting URL and getting an identifier  
- New: Add option to keep Genre in the comments.
- Fix: Site changed to add Preview button added in comments. Remove this.
- Fix: New version of the API.

**Version 1.2.0** - 28 May 2017 - by davidfor
- Update: To url https://www.fantasticfiction.com and other changes to the site

**Version 1.1.6** - 02 Oct 2014
- Fix: Updated for website changes

**Version 1.1.5** - 28 Jul 2014
- Update: Support for upcoming calibre 2.0

**Version 1.1.4** - 17 Aug 2013
- Fix: For changes to FF website

**Version 1.1.3** - 21 Jul 2013
- Fix: For change to FF website where not picking up publisher/isbn correctly

**Version 1.1.2** - 16 Apr 2013
- Fix: For change to FF website where not picking up authors correctly

**Version 1.1.1** - 23 Jun 2012
- Fix: For further changes to FantasticFiction website for lookups by ISBN

**Version 1.1.0** - 05 Jun 2012
- Fix: For changes to FantasticFiction website for how to scrape the search results

**Version 1.0.6** - 16 Jul 2011
- Fix: Support an additional edge case of Genre with a blank comments

**Version 1.0.5** - 16 Jul 2011
- New: Offer options for what to do with the Genre: addition the Goodreads website now has (discard, tags)

**Version 1.0.4** - 16 May 2011
- Update: For ISBN based lookups, strip any : from title returned to prevent treating as a subtitle
- Update: Strip '?' from title based lookups and the words "A Novel"
- Update: Strip leading "The" from title for ISBN based lookups
- Update: If title/authors returned by FF for ISBN lookup results in no matches, retry with calibre title/authors
- Update: When checking book returned from search is correct, compare with FF isbn and calibre title/authors before rejecting
- Update: Support change to FF website to surround ISBN with &lt;strong&gt; tags
- Fix: Ensure UTF-8 decoding of search results in case of rare issues
- Fix: For rare "url malformed" error when written by multiple authors but only one on FantasticFiction

**Version 1.0.3** - 13 May 2011
- Update: Tweak the logic when searching by ISBN so falls back to use original title/author for search

**Version 1.0.2** - 12 May 2011
- Update: No longer prefix comments for a book with 'SUMMARY:'
- Fix: Ensure no issues with no author being specified or no title being specified
- Fix: Ensure no series books parsed correctly

**Version 1.0.1** - 12 May 2011
- New: Add support for ISBN based lookups
- Fix: Non-ascii title/author names not being parsed correctly
- Fix: Re-runnability after a FF id is retrieved

**Version 1.0** - 12 May 2011
- Initial release of plugin
