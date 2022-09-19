#!/usr/bin/env python
# vim:fileencoding=UTF-8:ts=4:sw=4:sta:et:sts=4:ai
from __future__ import (unicode_literals, division, absolute_import,
                        print_function)

__license__   = 'GPL v3'
__copyright__ = '2022, Grant Drake'

import os

# calibre Python 3 compatibility.
import six

try:
    from qt.core import (QIcon, QPixmap)
except ImportError:
    from PyQt5.Qt import (QIcon, QPixmap)

from calibre.constants import iswindows
from calibre.constants import numeric_version as calibre_version
from calibre.utils.config import config_dir

# ----------------------------------------------
#          Global resources / state
# ----------------------------------------------

# Global definition of our plugin name. Used for common functions that require this.
plugin_name = None
# Global definition of our plugin resources. Used to share between the xxxAction and xxxBase
# classes if you need any zip images to be displayed on the configuration dialog.
plugin_icon_resources = {}

def set_plugin_icon_resources(name, resources):
    '''
    Set our global store of plugin name and icon resources for sharing between
    the InterfaceAction class which reads them and the ConfigWidget
    if needed for use on the customization dialog for this plugin.
    '''
    global plugin_icon_resources, plugin_name
    plugin_name = name
    plugin_icon_resources = resources

# ----------------------------------------------
#          Icon Management functions
# ----------------------------------------------

def get_icon_6_2_plus(icon_name):
    '''
    Retrieve a QIcon for the named image from
    1. Calibre's image cache
    2. resources/images
    3. the icon theme
    4. the plugin zip
    Only plugin zip has images/ in the image name for backward compatibility.
    '''
    icon = None
    if icon_name:
        icon = QIcon.ic(icon_name)
        ## both .ic and get_icons return an empty QIcon if not found.
        if not icon or icon.isNull():
            icon = get_icons(icon_name.replace('images/',''), plugin_name,
                             print_tracebacks_for_missing_resources=False)
        if not icon or icon.isNull():
            icon = get_icons(icon_name, plugin_name,
                             print_tracebacks_for_missing_resources=False)
    if not icon:
        icon = QIcon()
    return icon

def get_icon_old(icon_name):
    '''
    Retrieve a QIcon for the named image from the zip file if it exists,
    or if not then from Calibre's image cache.
    '''
    if icon_name:
        pixmap = get_pixmap(icon_name)
        if pixmap is None:
            # Look in Calibre's cache for the icon
            return QIcon(I(icon_name))
        else:
            return QIcon(pixmap)
    return QIcon()

def get_pixmap(icon_name):
    '''
    Retrieve a QPixmap for the named image
    Any icons belonging to the plugin must be prefixed with 'images/'
    '''
    global plugin_icon_resources, plugin_name
    if not icon_name.startswith('images/'):
        # We know this is definitely not an icon belonging to this plugin
        pixmap = QPixmap()
        pixmap.load(I(icon_name))
        return pixmap

    # Check to see whether the icon exists as a Calibre resource
    # This will enable skinning if the user stores icons within a folder like:
    # ...\AppData\Roaming\calibre\resources\images\Plugin Name\
    if plugin_name:
        local_images_dir = get_local_images_dir(plugin_name)
        local_image_path = os.path.join(local_images_dir, icon_name.replace('images/', ''))
        if os.path.exists(local_image_path):
            pixmap = QPixmap()
            pixmap.load(local_image_path)
            return pixmap

    # As we did not find an icon elsewhere, look within our zip resources
    if icon_name in plugin_icon_resources:
        pixmap = QPixmap()
        pixmap.loadFromData(plugin_icon_resources[icon_name])
        return pixmap
    return None

def get_local_images_dir(subfolder=None):
    '''
    Returns a path to the user's local resources/images folder
    If a subfolder name parameter is specified, appends this to the path
    '''
    images_dir = os.path.join(config_dir, 'resources/images')
    if subfolder:
        images_dir = os.path.join(images_dir, subfolder)
    if iswindows:
        images_dir = os.path.normpath(images_dir)
    return images_dir

if calibre_version >= (6,2,0):
    get_icon = get_icon_6_2_plus
else:
    get_icon = get_icon_old

