from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

import os
from functools import partial

# calibre Python 3 compatibility.
from six import text_type as unicode

try:
    from urllib.parse import quote_plus
except ImportError:
    from urllib import quote_plus

try:
    from qt.core import QMenu, QToolButton, QUrl
except ImportError:
    from PyQt5.Qt import QMenu, QToolButton, QUrl

from calibre.gui2 import error_dialog, open_url
from calibre.gui2.actions import InterfaceAction
from calibre.utils.config import config_dir, tweaks
from calibre.utils.formatter import EvalFormatter
from calibre.ebooks.metadata.book.formatter import SafeFormat
from calibre.devices.usbms.driver import debug_print

import calibre_plugins.search_the_internet.config as cfg
from calibre_plugins.search_the_internet.common_icons import set_plugin_icon_resources, get_icon
from calibre_plugins.search_the_internet.common_menus import (unregister_menu_actions, create_menu_action_unique,
                                                              create_menu_item)

try:
    load_translations()
except NameError:
    pass # load_translations() 


template_formatter = EvalFormatter()
template_formatter = SafeFormat()

class SearchTheInternetAction(InterfaceAction):

    name = 'Search The Internet'
    action_spec = (_('Search Internet'), None, None, None)
    popup_type = QToolButton.InstantPopup
    action_type = 'current'

    def genesis(self):
        self.menu = QMenu(self.gui)

        # Read the plugin icons and store for potential sharing with the config widget
        icon_names = ['images/'+i for i in cfg.get_default_icon_names()]
        icon_resources = self.load_resources(icon_names)
        set_plugin_icon_resources(self.name, icon_resources)

        self.rebuild_menus()

        # Assign our menu to this action and an icon
        self.qaction.setMenu(self.menu)
        self.qaction.setIcon(get_icon('images/'+cfg.PLUGIN_ICONS[0]))

    def rebuild_menus(self):
        # Ensure any keyboard shortcuts from previous display of plugin menu are cleared
        unregister_menu_actions(self)

        c = cfg.plugin_prefs[cfg.STORE_MENUS_NAME]
        data_items = cfg.get_menus_as_dictionary(c[cfg.MENUS_KEY])

        m = self.menu
        m.clear()

        sub_menus = {}
        self.open_group_data = []
        for data in data_items:
            active = data['active']
            if active:
                menu_text = data['menuText']
                sub_menu_text = data['subMenu']
                open_group = data['openGroup']
                image_name = cfg.get_pathed_icon(data['image'])
                tokenised_url = cfg.fix_legacy_url(data['url'])
                encoding = data['encoding']
                method = data.get('method', 'GET')
                self.create_menu_item_ex(m, sub_menus, menu_text, sub_menu_text,
                                         image_name, tokenised_url, encoding, method)
                if open_group and menu_text:
                    self.open_group_data.append((tokenised_url, encoding))
        m.addSeparator()
        if len(self.open_group_data) > 0:
            self.create_menu_item_ex(m, sub_menus, _('Open Group'),
                                  image_name='images/open_group.png', open_group=True)
        create_menu_action_unique(self, m, _('&Customize plugin')+'...', 'config.png',
                                  shortcut=False, triggered=self.show_configuration)
        self.gui.keyboard.finalize()

    def create_menu_item_ex(self, m, sub_menus, menu_text, sub_menu_text='',
                            image_name='', url='', encoding='', method='', open_group=False):
        parent_menu = m
        if sub_menu_text:
            # Create the sub-menu if it does not exist
            if sub_menu_text not in sub_menus:
                ac = create_menu_item(self, parent_menu, sub_menu_text, image_name)
                sm = QMenu()
                ac.setMenu(sm)
                sub_menus[sub_menu_text] = sm
            # Now set our menu variable so the parent menu item will be the sub-menu
            parent_menu = sub_menus[sub_menu_text]

        if not menu_text:
            ac = parent_menu.addSeparator()
        else:
            ac = create_menu_action_unique(self, parent_menu, menu_text, image_name,
                           unique_name=menu_text,
                           triggered=partial(self.search_web_link, url, encoding, method, open_group))
        return ac

    def search_web_link(self, tokenised_url, encoding, method, open_group=False):
        rows = self.gui.library_view.selectionModel().selectedRows()
        if not rows or len(rows) == 0:
            return
        self.db = self.gui.library_view.model().db
        for row in rows:
            if open_group:
                # User clicked the Open Group menu action, loop through all in group to open
                for url, enc in self.open_group_data:
                    if url:
                        self.search_web_for_book(row.row(), url, enc, method)
            else:
                self.search_web_for_book(row.row(), tokenised_url, encoding, method)

    def search_web_for_book(self, row, tokenised_url, encoding, method):
        mi = self.db.get_metadata(row)
        if not encoding:
            encoding = 'utf-8'
        self.open_tokenised_url(tokenised_url, encoding, method, mi)

    def open_tokenised_url(self, tokenised_url, encoding, method, mi):
        if not tokenised_url:
            return error_dialog(self.gui, _('Cannot open link'),
                                _('This menu item has not been configured with a url.'), show=True)
        # Get all the values from the book's metadata
        vals = mi.all_non_none_fields()
        vals['title'] = self.convert_title_to_search_text(mi.title, encoding, method)
        # Will only use the first author for the lookup if there are multiple
        vals['author'] = self.convert_author_to_search_text(mi.authors[0], encoding, method)
        vals['authors'] = vals['author'] # for name compatibility
        # rebuild the values dict, converting values to internet safe versions
        fixed_vals = {}
        for k in vals:
            fixed_vals[k] = unicode(vals[k]) # convert non-string types
            if k not in ['author', 'authors', 'title']:
                fixed_vals[k] = self.convert_to_search_text(fixed_vals[k], encoding, method)

        debug_print("open_tokenised_url - tokenised_url=", tokenised_url)
        debug_print("open_tokenised_url - mi=", mi)
        debug_print("open_tokenised_url - fixed_vals=", fixed_vals)
        url = template_formatter.safe_format(tokenised_url, mi, 'STI template error', mi)
        if method == 'POST':
            # We will write to a temporary file to do a form submission
            url = self.create_local_file_for_post(url)
            if url is None:
                return
            open_url(QUrl('file:///' + url))
        else:
            # Use the default web browser
            if isinstance(url, unicode):
                url = url.encode('utf-8')
            open_url(QUrl.fromEncoded(url))

    def create_local_file_for_post(self, url):
        if url.find('?') == -1:
            error_dialog(self.gui, _('Invalid URL'), 
                         _('You cannot use POST for this url '
                           'as you have not specified any arguments after a ?'), 
                         show=True
                         )
            return None
        url_parts = url.partition('?')
        args = url_parts[2].split('&')
        input_values = {}
        for arg in args:
            pair = arg.split('=')
            if len(pair) != 2:
                error_dialog(self.gui, _('Invalid URL'), 
                            _('You cannot use POST for this url '
                              'as it does not have name=value for ') + pair,
                             show=True
                            )
                return None
            # When submitting data via post, we want any quotes escaped
            input_values[pair[0]] = pair[1].replace('"','\"')
        js_submit = 'function mySubmit() { var frm=document.getElementById("form"); frm.submit(); }'
        # Set up file content elements
        input_field = '<input type="hidden" name="{0}" value="{1}" />'
        base_file_contents = """
<form id="form" action="{1}" method="post">
    <p>This page should disappear automatically once loaded.</p>
    <p>If your browser does not have javascript enabled, click on the button below.</p>
    <input id="button" type="submit" value="search" />
    {2}
</form>
<script type="text/javascript">
    {0}
    window.onLoad = mySubmit();
</script>
        """
        # Build input fields
        input_fields = ""
        for key, value in list(input_values.items()):
            input_fields += input_field.format(key, value)
        # Write out to a temp file
        temp_file = self.interface_action_base_plugin.temporary_file('_post.html')
        temp_file_data = base_file_contents.format(js_submit, url_parts[0], input_fields)
        temp_file.write(temp_file_data.encode("UTF-8"))
        temp_file.close()
        return os.path.abspath(temp_file.name)

    def convert_to_search_text(self, text, encoding, method):
        # First we strip characters we will definitely not want to pass through.
        # Periods from author initials etc do not need to be supplied
        text = text.replace('.', '').replace('  ',' ')
        # Now encode the text using Python function with chosen encoding
        if method == 'GET':
            text = quote_plus(text.encode(encoding, 'ignore'))
            # If we ended up with double spaces as plus signs (++) replace them
            text = text.replace('++','+')
        else:
            # For HTTP Post we do not want the encoding performed
            text = text.encode(encoding, 'ignore')
        return text

    def convert_title_to_search_text(self, title, encoding, method):
        # Ampersands are going to cause grief if this is an HTTP POST request because
        # of the crude splitting of the URL we do on ampersands. So strip them.
        if method == 'POST':
            title = title.replace('&','')
        return self.convert_to_search_text(title, encoding, method)

    def convert_author_to_search_text(self, author, encoding, method):
        # We want to convert the author name to FN LN format if it is stored LN, FN
        # We do this because some websites (Kobo) have crappy search engines that
        # will not match Adams+Douglas but will match Douglas+Adams
        # Not really sure of the best way of determining if the user is using LN, FN
        # Approach will be to check the tweak and see if a comma is in the name

        # Comma separated author will be pipe delimited in Calibre database
        fn_ln_author = author
        if author.find(',') > -1:
            # This might be because of a FN LN,Jr - check the tweak
            sort_copy_method = tweaks['author_sort_copy_method']
            if sort_copy_method == 'invert':
                # Calibre default. Hence "probably" using FN LN format.
                fn_ln_author = author
            else:
                # We will assume that we need to switch the names from LN,FN to FN LN
                parts = author.split(',')
                surname = parts.pop(0)
                parts.append(surname)
                fn_ln_author = ' '.join(parts).strip()
        return self.convert_to_search_text(fn_ln_author, encoding, method)

    def show_help(self):
        # Extract on demand the help file resource
        def get_help_file_resource():
            # We will write the help file out every time, in case the user upgrades the plugin zip
            # and there is a later help file contained within it.
            HELP_FILE = 'Search The Internet Help.html'
            file_path = os.path.join(config_dir, 'plugins', HELP_FILE)
            # In version 1.5 I have renamed the help file, so delete the old one if it exists
            legacy_file_path = os.path.join(config_dir, 'plugins', 'search_the_internet_help.html')
            if os.path.exists(legacy_file_path) and os.access(legacy_file_path, os.W_OK):
                os.remove(legacy_file_path)
            file_data = self.load_resources(HELP_FILE)[HELP_FILE]
            with open(file_path,'wb') as f:
                f.write(file_data)
            return file_path
        url = 'file:///' + get_help_file_resource()
        open_url(QUrl(url))

    def show_configuration(self):
        self.interface_action_base_plugin.do_user_config(self.gui)
