# Extract ISBN Change Log

## [1.6.3] - 2024-05-24
### Changed
- PDF scans now include the `-c -hidden` arguments for pdftohtml and remove newline characters for matches (Paul Harden)

## [1.6.2] - 2024-04-07
### Added
- Chinese (China) translation
### Changed
- Use podofo rather than pdfinfo to retrieve pdf page count. Shoudl fix issues for some users having problems with pdfinfo.exe
### Fixed
- If an exception occurred while attempting to scan a PDF, a second exception would occur when reporting it hiding the original.
- Fix libpng warning: icCCP: known incorrect sRGB profile using `magick mogrify *.png`

## [1.6.1] - 2024-03-17
### Added
- Finnish translation
- Tamil translation
- Turkish translation

## [1.6.0] - 2022-10-16
_All kiwidude plugins updated/migrated to: https://github.com/kiwidude68/calibre_plugins_
### Added
- Configuration option to turn off the dialog prompt when no ISBN found or ISBN is same as existing.
- Configuration option to turn off the dialog prompt with extract results to apply changes silently.
- Help button to configuration dialog
- Russian translation (Caarmi)
- Ukranian translation (@yurchor)
### Changed
- **Breaking:** Drop PyQt4 support, require calibre 2.x or later.
- Refactoring of common code

## [1.5.2] - 2022-09-05
### Changed
- Updated Spanish translations. (@dunhill)

## [1.5.1] - 2022-07-11
### Changed
- Changes for calibre 6/Qt6 (@davidfor)

## [1.5.0] - 2020-06-21
### Added
- Make translatable. (@davidfor)
- Add translations for German, Polish and Spanish. (@Garfield7, @bravosx, @dunhill)
### Changed
- Changes for Python 3 support in calibre.

## [1.4.3] - 2012-08-01
### Changed
- Split bulk extraction into batches with size changeable via plugin configuration 

## [1.4.2] - 2012-06-03
### Changed
- Minimum version set to calibre 0.8.54 (but preferred version is 0.8.55)
- Performance optimisation for epubs for calibre 0.8.51 to reduce unneeded computation
- Change to using different pdf engines for pdf processing due to calibre 0.8.53 breaking the one I was using.
### Fixed
- Stability improvement will activate with calibre 0.8.55 by running pdf analysis on a forked thread
- Minor fix to ensure HTMLPreProcessor object is initialised correctly
- Change to calibre API for deprecated dialog which caused issues that intermittently crashed calibre

## [1.4.1] - 2011-11-12
### Changed
- Exclude leading spaces before the ISBN number which prevented some valid ISBNs from being detected.

## [1.4.0] - 2011-09-11
### Changed
- To support the centralised keyboard shortcut management in Calibre

## [1.3.7] - 2011-07-02
### Fixed
- Bug of question dialog when metadata has changed not being displayed

## [1.3.6] - 2011-06-12
### Changed
- For non PDF file types, based on #files in books scan first x files, last y in reverse then rest
- When scan fails, still give option to view the log rather than standard error dialog
### Fixed
- Bug occurring when same ISBN extracted for a book

## [1.3.5] - 2011-05-25
### Changed
- Add yet another unicode variation of the hyphen separator to the regex

## [1.3.4] - 2011-05-21
### Fixed
- Run the ISBN extraction out of process to get around the memory leak issues

## [1.3.3] - 2011-05-19
### Changed
- Ensure stripped HTML tags replaced with a ! to prevent ISBN running into another number making it invalid

## [1.3.2] - 2011-05-17
### Changed
- Strip the `<style>` tag contents to ensure panose-1 numbers are not picked up as false positives

## [1.3.1] - 2011-05-06
### Changed
- Strip non-ascii characters from the pdfreflow xml which caused it to be invalid
- Support the ^ character being part of the ISBN number
### Fixed
- Attempt to minimise any memory leak issues caused by this plugin itself

## [1.3.0] - 2011-04-29
### Added
- Configuration option for ISBN13 prefixes and option to show updated books when extract completes
- Do all scanning as a background job to keep the UI responsive
### Changed
- Remove all interactive UI options - it will now always scan all formats in preferred order
- Make sure that ISBN-13s start with 977, 978 or 979 (configurable).
- Exclude the various repeating digit ISBNs of 1111111111 etc.
- Exclude all html markup tags to prevent issues like the svg sizes being picked up as ISBNs
- Include endash and other dash variants as possible separators
- When scanning PDF documents, scan the last 5 pages in reverse order so it is the last ISBN found

## [1.2.1] -2011-04-09
### Changed
- Support skinning of icons by putting them in a plugin name subfolder of local resources/images

## [1.2.0] - 2011-04-03
### Changed
- Rewritten for new plugin infrastructure in Calibre 0.7.53
- ISBN matching regex replaced using an approach from drMerry
- PDFs now processed with new Calibre PDF engine to scan just first 10 and last 5 pages

## [1.1.0] - 2011-03-28
### Added
- Add configuration options over the scan behaviour (default + alternate)
    - Ask me which format to scan
    - Scan only the first format in preferred input order
    - Scan all formats in preferred input order until an ISBN found

## [1.0.1] - 2011-03-24
### Added
- Display progress in the status bar
- Ctrl+click or shift+click on the toolbar button to do a non-interactive choice of formats where your book has multiple.
    - It will use the first found based on your preferred input format order list from Preferences->Behaviour
### Fixed
- Skip book formats which we are unable to read, such as djvu

## [1.0.0] - 2011-03-24
_Initial release of Extract ISBN plugin_
