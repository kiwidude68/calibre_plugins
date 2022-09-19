# Favourites Menu Plugin
[![MobileRead][mobileread-image]][mobileread-url]
[![History][changelog-image]][changelog-url] 
[![License][license-image]][license-url]
[![calibre Version][calibre-image]][calibre-url]
[![Status][status-image]][status-image] 

## Overview

Are you…

- Running out of screen space on your toolbar from adding plugins?
- Always forgetting where that xyz calibre feature is located?
- Tired of navigating deep into some menu hierarchy?
- Wanting a menu that you can control what order things appear on, and what they are called?
- Looking to change your life?

Now with with the patent pending all-singing and dancing **Favourites Menu** plugin you can build your own menu on a button! Wow!

Here are some testimonials from our ~~actors~~ customers:

> *“Every time I want the eject option for my Kindle from calibre, I can never click on that silly side arrow, it is just too darn small. Especially after a few drinks - not that I ever do of course. But thanks to kiwidude I can now have it right there on the big ol’ Favourites button just a little clickey clickey away. Cheers!”*

> *”Well I have just about every plugin kiwidude has written. Keep them right here next to my jar of toenail clippings since 1974. But as much as I love them all, I just can’t see them on my 3.5” screen. Now I have just one button to put all of them on – I call it calibre on a button. Thanks dude!”*

> *”I switch libraries – a lot. But every time I open the Library menu they are in a different order. My brain just couldn’t cope, it made me want to cry. But now thanks to Favourites Menu I can have just the libraries I use the most always in the same place. So that’s less time searching, and more time spent keeping my kids out of jail. Thanks kiwidude!”*

> *”I add books using an option from the dropdown on the toolbar button. But last time I dropped it down I sprained my neck reading the description, it was so damn long on screen. I had to take a month off work, the company closed, we lost the house and my wife left me. Thanks to the Favourites Menu plugin though I can have my own ‘Add books’ menu option so it won’t happen again. You’ve literally saved my life!”*

So just how much would you expect to pay have your own Favourites Menu button?

~~$99.99?~~

~~$49.99?~~

No - wait for it - if you download the Favourites Menu plugin in the next 3.2 seconds, it is absolutely free. That’s right - free! Wow!

But wait, that’s not all! If you click twice on the download button, we’ll give you not one, but two copies of the plugin. That’s two copies of the Favourites Menu plugin for no extra cost. Wow!

Our operators are standing by to take your call… ``1-800-555-KIWIDUDE``

## Main Features

- Create a customisable menu button with your favourite menu options
- You can add specific menu actions, submenus or entire plugins to your own menu.
- Add, remove, reorder and rename the menus with separators
- Where appropriate menu items are disabled if they are not relevant to the current context - e.g. device not plugged in.

## Notes for other plugin developers

- As of v1.0.3 Favourites Menu will support a plugin with its menus being rebuilt every time it is displayed (such as to enable/disable items based on the current state of calibre). The pattern for this is that your InterfaceAction class should have a .menu property representing the QMenu, and you will ordinarily have code hooked to the aboutToShow signal. When the Favourites Menu plugin is asked to dropdown will iterate through all of the child plugins it is being asked to display items for and (once per plugin) emit the iaction.menu.aboutToShow signal for any plugins that have such a .menu property.
- If your plugin changes the name of a child item dynamically this can cause a problem for the Favourites Menu plugin (as it uses the text name displayed by a plugin as part of the "key" identifying a menu item). For instance the Reading List plugin includes a count of the items in a child list for some of its actions. To ensure such menu items can be supported by the Reading List plugin, you should simply assign a constant identifying name for the menu item to a .favourites_menu_unique_name property on your qaction at the time you create it. The Favourites Menu plugin will look for such a property being present and use that in preference to the current text name if it is present.

## Development / Contributions

All kiwidude's calibre plugins are now developed and maintained in GitHub at:
- https://github.com/kiwidude68/calibre_plugins

Please see the README.md and CONTRIBUTING.md at the above site for more information.


[mobileread-image]: https://img.shields.io/badge/MobileRead-Plugin%20Thread-blue?logo=data:image/x-icon;base64,AAABAAEAEBAAAAEAIABoBAAAFgAAACgAAAAQAAAAIAAAAAEAIAAAAAAAQAQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAns32/zqT5v8SeeD/Enng/xJ54P8SeeD/LYvl/3+78v8AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAZazv/xJ54P8SeeD/Enng/zqT5v9Jm+n/HoLi/xJ54P8SeeD/OpPm/wAAAAAAAAAAAAAAAAAAAAAAAAAAzub7/xJ54P8SeeD/Enng/4/D9P/p6en/0tLS/8Tc8P8SeeD/Enng/xJ54P+Pw/T/AAAAAAAAAAAAAAAAAAAAAL3e+v8SeeD/Enng/xJ54P+93vr/Wlpa/zc3N/8AAAAAEnng/xJ54P8SeeD/f7vy/wAAAAAAAAAAAAAAAAAAAAAAAAAAHoLi/xJ54P8SeeD/T3+r/yQkJP9+jpz/Zazv/xJ54P8SeeD/Enng/73e+v8AAAAAAAAAAAAAAAAAAAAAz8Kt/66uof+Gj4L/ho+C/5SKb/+Vh2j/ho+C/4aPgv+Gj4L/ho+C/5OVgv+6qYP/yryi/wAAAAAAAAAAp5BW/6eQVv+nkFb/p5BW/6eQVv+nkFb/p5BW/6eQVv+nkFb/p5BW/6eQVv+nkFb/p5BW/6eQVv8AAAAA6ePb46eQVv+nkFb/p5BW/6eQVv+nkFb/xLWY/8/Crf/Pwq3/vq6N/7qogv+6qIL/uqiC/7qogv+nkFb/5uDW/+bg1v+nkFb/p5BW/6eQVv+nkFb/p5BW/+zn4f///////////8zMzP92dnb/VFRU/9nZ2f//////taJ5/8/Crf/m4Nb/p5BW/6eQVv+nkFb/p5BW/6eQVv/m4Nb////////////MzMz/k5OT/8zMzP/z8/P//////8S1mP/EtZj/5uDW/6eQVv+nkFb/p5BW/6eQVv+nkFb/oZ6Z/5OTk//m5ub/////////////////8/Pz/3Z2dv9xcHD/j4h7/9rRwf+nkFb/p5BW/6eQVv+nkFb/VVNP/8zMzP/z8/P/dnZ2/9nZ2f///////////5OTk//z8/P//////3Rxa//Pwq3/p5BW/6eQVv+nkFb/p5BW/2FgYP///////////76+vv/MzMz///////////+ioqL/oqKi/76+vv91b2X/z8Kt/6eQVv+nkFb/p5BW/6eQVv+JfWX/bGtq/4WFhf+FhYX//////////////////////76+vv++vr7/taJ5/8/Crf+nkFb/p5BW/6eQVv+nkFb/p5BW/8m7ov//////+Pb1/+bg1v/g2Mz/z8Kt/8/Crf+6qIL/uqiC/6eQVv/m4Nb/uqmD/7qpg/+nkFb/p5BW/6eQVv+nkFb/rZZh/7qpg/+/r43/z8Kt/8/Crf/m4NYd5uDWVQAAAAAAAAAA8A8AAOAHAADAAwAAwEMAAOADAADAAQAAgAEAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAMAAA==
[mobileread-url]: https://www.mobileread.com/forums/showthread.php?t=183022

[changelog-image]: https://img.shields.io/badge/History-CHANGELOG-blue.svg
[changelog-url]: CHANGELOG.md

[license-image]: https://img.shields.io/badge/License-GPL-yellow.svg
[license-url]: ../LICENSE.md

[calibre-image]: https://img.shields.io/badge/calibre-2.0.0-green
[calibre-url]: https://www.calibre-ebook.com/

[status-image]: https://img.shields.io/badge/Status-Stable-green
