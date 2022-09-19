# Common Files

Anyone who has maintained these plugins historically will know of the ``common_utils.py`` file. When the plugins were first developed and exclusively by kiwidude, this was a single file in a separate folder that was copied into each plugin at zip build time. Bug fixes or additions could be made in one place and apply to all plugins the next time they were built.

During the years that these plugins were independently maintained, without a common repo there was no such control possible over this file. Every developer changed only the functions they chose to for a particular plugin. This led to every single plugin having a different version of this file with varying content/bug fixes.

By consolidating the plugins into a single repo I am able to reinstate the concept of a common library of functions with only one copy of that code to maintain. This does slightly complicate the build process but as it is all encapsulated by the ``build.cmd`` batch file so unless adding new common files then developers should not need to care.

I have also taken the opportunity to split the functions into individual files for ease of maintenance as follows:
| Filename | Purpose |
| -------- | ------- |
| common_compatibility.py | Frequently used compatibility imports for PyQt5 -> Later |
| common_dialogs.py | Common dialogs, that persist their position |
| common_icons.py | The ``get_icon()`` function with all its complexity nowadays |
| common_menus.py | Helper functions for building menus for ``action.py`` |
| common_utils.py | Helper functions for debugging output |
| common_widgets.py | Additional Qt based controls for use in dialogs or grid tables |

One negative to splitting these functions was that any interdependencies between them require some ``build.py`` trickery to insert the correct plugin namespace which is only known at the time the specific plugin is built into a zip. 

A final complication to bear in mind with using dialogs/widgets in common files is translations. I had to modify ``generate-pot.cmd`` to include translations for all the common files.
