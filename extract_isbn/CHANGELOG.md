## Release History

**Version 1.6.0** - xx Sep 2022
- New: All kiwidude plugins updated/migrated to: https://github.com/kiwidude68/calibre_plugins
- Update: Drop PyQt4 support, require calibre 2.x or later.
- Update: Refactoring of common code

**Version 1.5.2** - 05 Sep 2022
- Updated Spanish translations. Thanks to @dunhill

**Version 1.5.1** - 11 July 2022 - by davidfor
- Update: Changes for calibre 6/Qt6

**Version 1.5.0** - 21 June 2020 - by davidfor
- New: Make translatable.
- New: Add translations for German, Polish and Spanish. Thanks to @Garfield7, @bravosx and @dunhill
- Update: Changes for Python 3 support in calibre.

**Version 1.4.3** - 01 Aug 2012
- Update: Split bulk extraction into batches with size changeable via plugin configuration 

**Version 1.4.2** - 03 Jun 2012
- Update: Minimum version set to calibre 0.8.54 (but preferred version is 0.8.55)
- Update: Performance optimisation for epubs for calibre 0.8.51 to reduce unneeded computation
- Upgrade: Minor fix to ensure HTMLPreProcessor object is initialised correctly
- Upgrade: Change to using different pdf engines for pdf processing due to calibre 0.8.53 breaking the one I was using.
- Upgrade: Stability improvement will activate with calibre 0.8.55 by running pdf analysis on a forked thread
- Fix: Change to calibre API for deprecated dialog which caused issues that intermittently crashed calibre

**Version 1.4.1** - 12 Nov 2011
- Upgrade: Exclude leading spaces before the ISBN number which prevented some valid ISBNs from being detected.

**Version 1.4.0** - 11 Sep 2011
- Upgrade: To support the centralised keyboard shortcut management in Calibre

**Version 1.3.7** - 02 Jul 2011
- Fix: Bug of question dialog when metadata has changed not being displayed

**Version 1.3.6** - 12 Jun 2011
- Update: For non PDF file types, based on #files in books scan first x files, last y in reverse then rest
- Update: When scan fails, still give option to view the log rather than standard error dialog
- Fix: Bug occurring when same ISBN extracted for a book

**Version 1.3.5** - 25 May 2011
- Update: Add yet another unicode variation of the hyphen separator to the regex

**Version 1.3.4** - 21 May 2011
- Fix: Run the ISBN extraction out of process to get around the memory leak issues

**Version 1.3.3** - 19 May 2011
- Update: Ensure stripped HTML tags replaced with a ! to prevent ISBN running into another number making it invalid

**Version 1.3.2** - 17 May 2011
- Update: Strip the &lt;style&gt; tag contents to ensure panose-1 numbers are not picked up as false positives

**Version 1.3.1** - 06 May 2011
- Update: Strip non-ascii characters from the pdfreflow xml which caused it to be invalid
- Update: Support the ^ character being part of the ISBN number
- Fix: Attempt to minimise any memory leak issues caused by this plugin itself

**Version 1.3** - 29 Apr 2011
- New: Configuration option for ISBN13 prefixes and option to show updated books when extract completes
- New: Do all scanning as a background job to keep the UI responsive
- Update: Remove all interactive UI options - it will now always scan all formats in preferred order
- Update: Make sure that ISBN-13s start with 977, 978 or 979 (configurable).
- Update: Exclude the various repeating digit ISBNs of 1111111111 etc.
- Update: Exclude all html markup tags to prevent issues like the svg sizes being picked up as ISBNs
- Update: Include endash and other dash variants as possible separators
- Update: When scanning PDF documents, scan the last 5 pages in reverse order so it is the last ISBN found

**Version 1.2.1** - 09 Apr 2011
- Update: Support skinning of icons by putting them in a plugin name subfolder of local resources/images

**Version 1.2** - 03 Apr 2011
- Update: Rewritten for new plugin infrastructure in Calibre 0.7.53
- Update: ISBN matching regex replaced using an approach from drMerry
- Update: PDFs now processed with new Calibre PDF engine to scan just first 10 and last 5 pages

**Version 1.1** - 28 Mar 2011
- New: Add configuration options over the scan behaviour (default + alternate)
    - Ask me which format to scan
    - Scan only the first format in preferred input order
    - Scan all formats in preferred input order until an ISBN found

**Version 1.0.1** - 24 Mar 2011
- New: Display progress in the status bar
- New: Ctrl+click or shift+click on the toolbar button to do a non-interactive choice of formats where your book has multiple.
    - It will use the first found based on your preferred input format order list from Preferences->Behaviour
- Fix: Skip book formats which we are unable to read, such as djvu

**Version 1.0** - 24 Mar 2011
- Initial release of Extract ISBN plugin
