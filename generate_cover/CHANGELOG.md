# Generate Cover Change Log

## [2.3.3] - 2023-09-01
### Added
- Russian translation (ashed)
### Changed
- Allow dialog to have a reduced minimum height by around 100px for use on smaller screen sizes

## [2.3.2] - 2022-12-29
### Added
- Russian translation (ashed)
### Changed
- Allow dialog to have a reduced minimum height by around 100px for use on smaller screen sizes

## [2.3.2] - 2022-12-29
### Fixed
- Export and import not working correctly

## [2.3.1] - 2022-11-07
### Changed
- Rewrite of unsaved changes dialog when OK is pressed on cover options dialog:
    - Rename `Save Changes` to `Generate & Save` button
    - Add `Generate & Revert` button
    - Add `Cancel` button
    - Remove `Discard Changes` button
    - Remove `Dont Save Yet` button
### Fixed
- Generating a cover from FFF plugin will now respect any settings by user to update a custom column after cover generation.

## [2.3.0] - 2022-10-16
_All kiwidude plugins updated/migrated to: https://github.com/kiwidude68/calibre_plugins_
### Added
- Add a Help button to the configuration dialog.
- Ukranian translation (@yurchor)
### Changed
- Move user images from `/resources/images/generate_cover` to `/plugins/generate_cover` to prevent loss if user has not yet migrated to Calibre 6.
- **Breaking:** Drop PyQt4 support.
- Refactoring of common code

## [2.2.0] - 2022-08-02
### Changed
- Use cal6 icon theme system to allow plugin icon customization

## [2.1.1] - 2022-07-14
### Fixed
- Settings export in Calibre6/Qt6

## [2.1.0] - 2022-01-21
### Changed
- Changes for upcoming Qt6 Calibre

## [2.0.2] - 2021-02-06
### Fixed
- Fix for a py2/py3 difference in import zip

## [2.0.1] - 2020-12-04
### Fixed
- Fix image centering again

## [2.0.0] - 2020-11-07
### Changed
- Remove `draw_old.py`, not needed in Cal v2+
- French translation (@un-pogaz)
- Spanish translation (@dunhill)
### Fixed
- Border causing image to move horizontally.

## [1.5.25] - 2020-06-12
### Changed
- Custom text `setText()` instead of `setHtml()`

## [1.5.24] - 2020-05-21
### Changed
- Explicitly enforces the image size limits when read from the file, not just on the spin box in the dialog (and outputs a little debug data).

## [1.5.22] - 2020-01-16
### Changed
- Compatibility with Python 3

## [1.5.21] - 2016-07-31
### Fixed
- Regression in the previous release that broke integration with the FanFicFare plugin

## [1.5.20] - 2016-07-29
### Changed
- Also use the correct calibre APIs to read the cover from the database.
### Fixed
- Incorrect handling of book with multiple authors (extra spaces inserted around &)

## [1.5.19] - 2016-05-21
### Fixed
- Inability to use first font in the list of fonts for rendering text

## [1.5.18] - 2016-05-20
### Changed
- Compatibility for calibre 2.57+

## [1.5.16] - 2014-10-11
### Changed
- Compatibility for calibre 2.4+

## [1.5.15] - 2014-07-15
### Changed
- Compatibility for the upcoming calibre 2.0

## [1.5.14] - 2013-09-29
### Fixed
- User typing \n or or `<br>` or `<br/>` as part of the author to control split across multiple lines

## [1.5.13] - 2013-09-24
### Added
- Add a checkbox option to allow scaling up the cover image to fit the available area if it is too small.
### Changed
- Support the user typing \n or or `<br>` or `<br/>` as part of the title or series to control split across multiple lines

## [1.5.12] - 2013-05-03
### Fixed
- Change made to calibre API in 0.9.29

## [1.5.11] - 2013-03-17
### Fixed
- Import saved cover settings not working

## [1.5.10] - 2013-03-06
### Fixed
- Re-release of 1.5.9 due to problem with zip file

## [1.5.9] - 2013-03-06
### Added
- Add a "Metadata" section to the "Content" tab allowing the user to override title/author/series for one-off covers
- Add ability to configure a custom column (or tags column) to contain a value any time a cover is generated for a book

## [1.5.8] - 2012-12-09
### Changed
- Automatically "correct" any corrupted json files when users upgrade to this version
- Check for corruption every time Generate Cover is opened. If found, show error dialog and autofix.
- Prevent plugin being used in Device View or on Device View context menu

## [1.5.7] - 2012-11-14
### Fixed
- Stretch cover/resize option not finding full path to image.

## [1.5.6] - 2012-11-03
### Added
- Add support for calibre 0.9.5 which changed how Fonts are loaded.

## [1.5.5] - 2012-08-14
### Changed
- No longer use a calibre ImageView to preview cover as it has right-click menu and drag/drop not relevant to this plugin
- Add protection against failed upgrades of the seriesText field.

## [1.5.4] - 2012-06-01
### Changed
- Make the series text an option so foreign language users can change it
- No longer respect the calibre preferences Roman Numerals setting - series index will always be displayed numerically.

## [1.5.3] - 2012-05-31
### Changed
- Ensure paths to images used by this plugin are stored as relative paths for portability
- Change the calibre library image to appear as `{Default Image}` in the images list
- Reorder the images list so `{Default Image}` and `{Current Cover}` appear at the top
- Allow renaming images changing only their casing

## [1.5.2] - 2012-05-20
### Added
 Add a 'Resize cover dimensions to match background image' suboption for if you have stretch image to use as cover background enabled.
### Changed
- Ensure code is more command line friendly via the API for external script usage

## [1.5.1] - 2012-05-03
### Fixed
- Issue of version number not incremented for 1.5.0

## [1.5.0] - 2012-05-02
### Added
- Add a separate right margin option, rather than using left margin for both
- On the Fonts tab allow specifying the alignment for each text item of left, centre, right rather than always centre
- Add export and import capability for sharing settings/images with other users
- Add an 'Autosave setting' option to Settings tab. When checked, any changes to settings are always saved (except when Cancel pressed)
### Changed
- Set maximum font size to 999 instead of 99
- Expose API methods to allow more conveniently calling from other plugins
- When clicking OK (or Import or Export) prompt user to save settings if changed before continuing.
- If font assigned to a setting (whether existing or imported) is not found, use the default font rather than erroring
- If user renames image just by stripping extension, treat this same as if user cancelled rename operation
- Allow importing of multiple images at once.
- Allow importing of multiple setting zips at once.
### Fixed
- Selection changes and corrupted multiple cover settings

## [1.4.0] - 2011-09-11
### Changed
- Upgrade to support the centralised keyboard shortcut management in Calibre

## [1.3.8] - 2011-07-03
### Changed
- Replace the deprecated `composite_formatter` with `SafeFormat()`

## [1.3.7] - 2011-06-04
### Changed
- Use a progress dialog while generating covers

## [1.3.6] - 2011-06-03
### Fixed
- Fonts being set to "Default" resulting in null in config file causing an error

## [1.3.5] - 2011-06-01
### Added
- Add a special token to the list of images representing the current cover for the book to allow embedding
### Fixed
- Abort autosize logic with replaced text when text is too large to fit so plugin does not lockup

## [1.3.4] - 2011-04-27
### Changed
- Allow custom text field to be formatted using Calibre template engine
- Change custom text field so it is a multiline field for more space and complex content

## [1.3.3] - 2011-04-23
### Fixed
- Ensure that margins are set to zero if set to too high a value to prevent crash

## [1.3.2] - 2011-04-09
### Changed
- Support skinning of icons by putting them in a plugin name subfolder of local resources/images

## [1.3.1] - 2011-04-04
### Fixed
- Error for users migrating from particular previous versions

## [1.3.0] - 2011-04-03
### Changed
- Rewritten for new plugin infrastructure in Calibre 0.7.53

## [1.2.1] - 2011-03-26
### Changed
- Ensure version number put in config file for first-time user

## [1.2.0] - 2011-03-26
### Added
- Support freeform text added to cover.
- Add option to autosize text to fit on one line.
### Changed
- Add a timer to ensure GUI does not redraw preview as every UI change made.

## [1.1.0] - 2011-03-16
### Added
- Support drag/drop images.
- Support text colors.
- Support image as background.
- Support linking single font.
- Support named saved settings.
- Copy image files to resources directory.
- Support renaming image files.
### Changed
- Redesign GUI.

## [1.0.2] - 2011-03-05
### Fixed
- Error appearing if trying to customize through preferences

## [1.0.1] - 2011-03-05
### Changed
- Remove fixed widths for users with large fonts

## [1.0.0] - 2011-03-05
_Initial release of Generate Cover plugin_
