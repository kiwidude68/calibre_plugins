## Release History

**Version 1.10.0** - XX Sep 2022
- New: All kiwidude plugins updated/migrated to: https://github.com/kiwidude68/calibre_plugins
- New: Add translation support
- New: Translations for Spanish, French, Russian, Ukranian - thanks to all!
- Update: Support qt.core import syntax for future Qt compatibility
- Update: Refactoring of common code

**Version 1.9.0** - 02 Aug 2022
- Update: Use cal6 icon theme system to allow plugin icon customization

**Version 1.8.0** - 23 Mar 2021
- New: Add Previous View action.
- Update: Performance tweak, apply_state(save_state=False)

**Version 1.7.0** - 19 Jan 2021
- Update: Changes for upcoming Qt6 Calibre

**Version 1.6.0** - 04 Nov 2020
- New: Add 'Re-Apply Current View' action. Only available when a view has been previously applied.
- Update: Change how saved searches are retrieved to newer API.
- Update: Apply persist_shortcut to view actions when Calibre >= v5.4 so view shortcuts aren't discarded as easily. Calibre PR #1246

**Version 1.5.6** - 15 Jun 2020
- New: Add 'Next View' feature

**Version 1.5.5** - 07 Mar 2020
- Fix: Allow for a View named empty string.

**Version 1.5.4** - 16 Jan 2020
- Update: Compatibility with Python 3

**Version 1.4.3** - 24 Jun 2017
- Update: Disambiguation of settings.

**Version 1.3.2** - 22 Nov 2014
- Fix: keyboard shortcuts not working on calibre >= 2.10

**Version 1.3.1** - 24 Jul 2014
- New: Create new Views and update Views with current columns, column widths and sorts.
- New: Can switch Virtual libraries on View activation.
- Update: Compatibility for upcoming calibre 2.0
- Update: Make settings for Virtual library, Saved search and VL additional restriction search clearer.

**Version 1.3.0** - 22 Jun 2012
- New: Store views in the calibre database rather than a json file, to allow reuse from different computers (not simultaneously!)
- New: Add a support option to the "Other" tab allowing viewing the plugin data stored in the database
- Update: Now requires calibre 0.8.57
- Update: No longer support upgrading from plugin versions older than 1.2.0

**Version 1.2.1** - 11 Sep 2011
- Fix: When switching libraries, ensure no issues with old menu items causing a crash

**Version 1.2.0** - 11 Sep 2011
- Update: Support the centralised keyboard shortcut management in Calibre
- Update: When opening the configuration dialog, default to the last selected view

**Version 1.1.2** - 16 Jul 2011
- Fix: Config error introduced with 1.1.1

**Version 1.1.1** - 16 Jul 2011
- Fix: Error issue for first time users

**Version 1.1.0** - 11 Jul 2011
- New: Add ability to store column widths as part of the view information

**Version 1.0.6** - 15 Jun 2011
- New: Indicate the last selected view with a checkbox in the menu

**Version 1.0.5** - 23 Apr 2011
- New: Enhance configuration options to allow specifying a view to apply at startup
- Update: Ensure any auto applying of views is a per library setting
- Fix: Not always remembering the last applied view when restarting/switching libraries

**Version 1.0.4** - 14 Apr 2011
- Fix: Applying a blank saved search not working

**Version 1.0.3** - 12 Apr 2011
- Update: Add text to config dialog advising of behaviour if enable automatic apply view
- Fix: Plugin not working for first time users

**Version 1.0.2** - 11 Apr 2011
- New: Offer configuration option to apply last selected view at startup or switching libraries
- Update: Change configuration file format to offer more flexibility

**Version 1.0.1** - 10 Apr 2011
- Fix: key error when creating new views

**Version 1.0** - 10 Apr 2011
- Initial release of View Manager plugin
