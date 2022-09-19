## Release History

**Version 1.7.0** - xx Sep 2022
- New: All kiwidude plugins updated/migrated to: https://github.com/kiwidude68/calibre_plugins
- New: Malay, Russian translations - thanks to abuyop and Caarmi
- Update: Drop PyQt4 support, require calibre 2.x or later.
- Update: Refactoring of common code

**Version 1.6.2** - 08 Sep 2022
- New: Add translation support for config screen.
- New: Chinese, Spanish, French, Hungarian, Italian, Japanese, Dutch, Polish, Ukranian translations - thanks to everyone!!!

**Version 1.6.1** - 06 Sep 2022
- New: Add configuration option to use edition published date or first published date  (default).
- Fix: Remove debug code, fixes for isbn, publication date and series index when multiple series.

**Version 1.6.0** - 03 Sep 2022
- Update: Support new Goodreads web page formats in conjunction with legacy pages.

**Version 1.5.3** - 05 Jan 2022 - made by davidfor
- Update: Cleanup in preparation for calibre 6/Qt6.

**Version 1.5.2** - 30 Nov 2020 - made by davidfor
- Fix: Use mobi-asin identifier 

**Version 1.5.1** - 25 Sep 2020 - made by davidfor
- New: Czech translation - thanks to seeder
- New: Add download page count from databazeknih.cz and cbdb.cz - thanks to seeder
- Fix: Wasn't getting the series info.

**Version 1.5.0** - 19 Sep 2020 - made by davidfor
- Update: Changes for Python 3 support in calibre.
- Fix: Small error in handling editions.

**Version 1.4.0** - 20 Dec 2018 - made by davidfor
- Fix: Site change for rating.
- Fix: Add extra attempt to convert language name to code.

**Version 1.3.0** - 10 Nov 2018 - made by davidfor
- New: Add get_book_url for pasting URL and getting an identifier
- Change: Generate HTTPS URL for identifier.

**Version 1.2.0** - 23 Oct 2018 - made by davidfor
- New: Add search by ASIN or other Amazon id if it exists.
- New: Use auto_complete API for ISBN and ASIN search. Based on code from MR user botmtl. 

**Version 1.1.17** - 13 Oct 2018 - made by davidfor
- Fix: Changes in search page plus fixing issue with scanning editions.

**Version 1.1.16** - 03 Oct 2018 - made by davidfor
- New: Get the ASIN if the book is am Amazon edition. There is an option to turn this on. It is off by default. This is based on code from @Iceybones.
- Update: Checks through the search results for a match to the title and author. This will solve the problem reported by @saitoh183.
- Fix: Series separated from the title.

**Version 1.1.14** - 17 Apr 2018 - made by davidfor
- Fix: Change in search page.

**Version 1.1.13** - 17 Dec 2017 - made by davidfor
- Fix: Normalize title to solve issues with accented characters.

**Version 1.1.12** - 30 Dec 2016 - made by davidfor
- Fix: Ratings were not always being retrieved properly.

**Version 1.1.11** - 8 Feb 2016 - made by davidfor
- Fix: Site changes for the description/comments.
- Fix: Site and option changes for genre and classification. 

**Version 1.1.10** - 26 Oct 2015
- Fix: Site changes for the description/comments.

**Version 1.1.9** - 11 Jul 2015
- Fix: Do not change case of tags downloaded, so YA stays as YA.

**Version 1.1.8** - 08 Jul 2014
- Update: Change to allow Qt4 or Qt5.

**Version 1.1.7** - 25 Aug 2013
- Fix: For more.../less... on authors

**Version 1.1.6** - 17 Aug 2013
- New: Support Dutch language

**Version 1.1.5** - 10 Jul 2013
- Fix: Updated to match Goodreads website change which broke ISBB and cover parsing

**Version 1.1.4** - 04 Mar 2013
- Fix: Goodreads change for when large number of authors to ensure more.../less... is removed correctly

**Version 1.1.3** - 28 Dec 2012
- New: Support for "languages" metadata field
- Fix: Get all contributing authors option

**Version 1.1.2** - 23 Jun 2012
- Fix: Reject editions that do not match in title (such as different languages) and handle non-ascii characters better
- Fix: Handle books with short descriptions since Goodreads website change

**Version 1.1.1** - 12 Jun 2012
- Fix: Match Goodreads website change which stopped tags being downloaded
- Fix: Change to the comments to no longer strip paragraph breaks

**Version 1.1.0** - 03 Mar 2012
- Fix: The "Scan multiple editions for title/author searches" option broken from Goodreads website change

**Version 1.0.9** - 14 Nov 2011
- New: Support case insensitive comparisons of genre tag mappings
- New: Allow renaming an item changing only case
- Update: When sorting to display the mappings in the config screen, ignore case

**Version 1.0.8** - 25 Oct 2011
- Fix: If large number of authors, ensure more... and ...less is stripped from authors results.

**Version 1.0.7** - 10 Aug 2011
- Fix: Ensure a "close but not quite" series # does not throw an error within the plugin.

**Version 1.0.6** - 21 Jun 2011
- Fix: Handle change to Goodreads website which prevented title/author results returning

**Version 1.0.5** - 12 May 2011
- Update: Ensure any covers less than 1000 bytes in size are ignored.
- Update: No longer prefix the comments with SUMMARY: in output for consistency with other plugins

**Version 1.0.4** - 08 May 2011
- Update: Remove code supporting versions prior to 0.8
- Update: Strip trailing comma from series name if it exists
- Update: Put summary comments on line following the word SUMMARY: rather than on same line.

**Version 1.0.3** - 29 Apr 2011
- Fix: Ensure non ascii author names are parsed correctly.

**Version 1.0.2** - 26 Apr 2011
- Fix: Properly fix the ordering of tags.

**Version 1.0.1** - 25 Apr 2011
- Update: Support for API change upcoming in Calibre 0.7.58 allowing hyperlinked ids in book details panel
- Fix: Ensure tags mapped are returned by order of popularity not alphabetically so applying a tag threshold works better

**Version 1.0** - 23 Apr 2011
- Initial release of plugin, rewritten consolidation of Goodreads Metadata and Goodreads Covers plugins
