# Common Files

Anyone who has maintained these plugins historically will know of the ``common_utils.py`` file. When the plugins were first developed and exclusively by kiwidude, this was a single file in a separate folder that was copied into each plugin at zip build time. Bug fixes or additions could be made in one place and apply to all plugins the next time they were built.

During the years that these plugins were independently maintained, without a common repo there was no such control possible over this file. Every developer changed only the functions they chose to for a particular plugin. This led to every single plugin having a different version of this file with varying content/bug fixes.

By consolidating the plugins into a single repo I am able to reinstate the concept of a common library of functions with only one copy of that code to maintain. This does slightly complicate the build process but as it is all encapsulated by the ``build.cmd`` batch file so unless adding new common files then developers should not need to care.

I have also taken the opportunity to split the functions into individual files for ease of maintenance as follows:
| Filename | Purpose |
| -------- | ------- |
| common_dialogs.py | Common dialogs, that persist their position |
| common_icons.py | The ``get_icon()`` function with all its complexity nowadays |
| common_menus.py | Helper functions for building menus for ``action.py`` |
| common_utils.py | Helper functions for debugging |
| common_widgets.py | Additional Qt based controls for use in dialogs or grid tables |

One negative to splitting these functions was that any interdependencies between them require some ``build.py`` trickery to insert the correct plugin namespace which is only known at the time the specific plugin is built into a zip.

A final complication to bear in mind with using dialogs/widgets in common files is translations. I had to modify ``generate-pot.cmd`` to include translations.

Both approaches have pros and cons. The first means we lose encapsulation and complicates the interfaces for the dialog/widget containing translatable text. The latter means some additional overhead/translation text even if a plugin doesn't use that particular function itself. Though with Transifex I believe it would translate automatically the same text expression across many plugins.

TODO: Which approach to use?

# Migrating Older Plugins

Documenting a bunch of tips here in one place as I work through migrating all these plugins.

The current state of play is:
- When dropping support for Qt4, means supporting only calibre 2.x or later
- The `from qt.core import xxx` syntax is from calibre 5.13 or later

## Migrating Qt 5 to Qt 6

These tips have come from this [MobileRead Qt6 thread](https://www.mobileread.com/forums/showthread.php?t=344064)

## JimmXinu Tips from Qt 6

In [this post](https://www.mobileread.com/forums/showpost.php?p=4188895&postcount=104) JimmXinu listed the changes he made to these plugins:
- Favourites Menu
- Generate Cover
- Manage Series
- Reading List
- View Manager

The following changes were made:
- Remove all Qt4 imports. Keep Qt5 (vs new qt.core (5.13+)) for back compatible to v2.85.1.
- Remove calls to convert_qvariant() and defining code (plus QVariant import); only needed for qt4.
- Remove QTableWidgetItem.UserType from calls to QTableWidgetItem.__init__() as proposed by jackie_w. un_pogaz's code also works, but it makes no difference and I can't find any reason to keep it.
- Remove class NumericLineEdit and QRegExp imports. If you need NumericLineEdit, look at - replacements QRegularExpression and QRegularExpressionValidator.
- Set minimum Calibre version to 2.85.1--or else keep all the qt4 imports, qvariant, etc.
- Change setChecked->setCheckState when called with Qt.Checked/UnChecked. Or change to pass bool instead.
- Remove call to setTabStopWidth from raw prefs viewer--changed in qt6 and not needed

## Capink changes for Qt 6

The following plugins have 5.13 set as their minimum:
- Find Duplicates
- Import List
- Open With

## Migrating Qt 4 to Qt 5

For even older plugins there is this [MobileRead Qt5 thread](https://www.mobileread.com/forums/showthread.php?t=242223) from back in 2014.
