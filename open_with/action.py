from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

from functools import partial
import os, re, shlex, subprocess

try:
    from qt.core import QMenu, QToolButton
except ImportError:
    from PyQt5.Qt import QMenu, QToolButton

try:
    load_translations()
except NameError:
    pass # load_translations() added in calibre 1.9

from calibre.constants import iswindows, isosx, DEBUG
from calibre.gui2 import error_dialog, sanitize_env_vars
from calibre.gui2.actions import InterfaceAction

import calibre_plugins.open_with.config as cfg
from calibre_plugins.open_with.common_icons import set_plugin_icon_resources, get_icon
from calibre_plugins.open_with.common_menus import (unregister_menu_actions, create_menu_action_unique,
                                                    create_menu_item)

FILENAME_TOKEN_PATTERN = re.compile(r'%FILENAME([0-9]*)%')

class OpenWithAction(InterfaceAction):

    name = 'Open With'
    action_spec = (_('Open With'), None, None, None)
    popup_type = QToolButton.InstantPopup
    action_type = 'current'
    dont_add_to = frozenset(['context-menu-device'])

    def genesis(self):
        self.is_library_selected = True
        self.menus_by_format = {}
        self.menu = QMenu(self.gui)

        # Read the plugin icons and store for potential sharing with the config widget
        icon_names = ['images/'+i for i in cfg.get_default_icon_names()]
        icon_resources = self.load_resources(icon_names)
        set_plugin_icon_resources(self.name, icon_resources)

        self.rebuild_menus()

        # Assign our menu to this action and an icon
        self.qaction.setMenu(self.menu)
        self.qaction.setIcon(get_icon('images/'+cfg.PLUGIN_ICONS[0]))
        # Setup hooks so that we only enable the relevant submenus for available formats for the selection.
        self.menu.aboutToShow.connect(self.about_to_show_menu)
        self.menu.aboutToHide.connect(self.about_to_hide_menu)

    def location_selected(self, loc):
        self.is_library_selected = loc == 'library'

    def rebuild_menus(self):
        # Ensure any keyboard shortcuts from previous display of plugin menu are cleared
        unregister_menu_actions(self)

        c = cfg.plugin_prefs[cfg.STORE_MENUS_NAME]
        data_items = cfg.get_menus_as_dictionary(c[cfg.KEY_MENUS])
        m = self.menu
        m.clear()
        self.menus_by_format = {}
        sub_menus = {}
        
        for data in data_items:
            active = data['active']
            if active:
                menu_text = data['menuText']
                sub_menu_text = data['subMenu']
                book_format = data['format']
                image_name = cfg.get_pathed_icon(data['image'])
                external_app_path = data['appPath']
                app_args = data['appArgs']
                self.create_menu_item_ex(m, sub_menus, menu_text, sub_menu_text, book_format,
                                         image_name, external_app_path, app_args)
        m.addSeparator()
        create_menu_action_unique(self, m, _('&Customize plugin')+'...', 'config.png',
                                  shortcut=False, triggered=self.show_configuration)
        create_menu_action_unique(self, m, _('&Help'), 'help.png',
                                  shortcut=False, triggered=cfg.show_help)
        self.gui.keyboard.finalize()

    def create_menu_item_ex(self, m, sub_menus, menu_text, sub_menu_text, book_format,
                            image_name, external_app_path, app_args):
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
            unique_name = book_format + menu_text
            ac = create_menu_action_unique(self, parent_menu, menu_text, image_name,
                           unique_name=unique_name,
                           triggered=partial(self.open_with, book_format, external_app_path, app_args))
            # Maintain our list of menus by format references so we can easily enable/disable menus when user right-clicks.
            menus_for_format = [ac]
            if book_format in self.menus_by_format:
                menus_for_format = self.menus_by_format[book_format]
                menus_for_format.append(ac)
            self.menus_by_format[book_format] = menus_for_format
        return ac

    def about_to_show_menu(self):
        # Enable each format if at least one selected book can be opened with it.
        db = self.gui.current_db
        book_ids = self.get_selected_book_ids()
        if not book_ids or not self.is_library_selected:
            # Right-clicking with no valid row should disable ALL menu options
            self.set_enabled_for_all_menu_formats(False)
            return

        for book_format in self.menus_by_format:
            is_enabled = False
            for book_id in book_ids:
                if book_format == 'COVER':
                    is_enabled = db.has_cover(book_id)
                elif book_format == 'TEMPLATE':
                    is_enabled = True
                else:
                    book_formats = db.formats(book_id, index_is_id=True, verify_formats=False)
                    if not book_formats:
                        book_formats = ''
                    is_enabled = book_format in book_formats.split(',')
                if is_enabled:
                    break
            self.set_enabled_for_menus_in_format(book_format, is_enabled)

    def get_selected_book_ids(self):
        book_ids = self.gui.library_view.get_selected_ids()
        if book_ids:
            return book_ids
        row = self.gui.library_view.currentIndex()
        if row.isValid():
            return [self.gui.library_view.model().id(row)]
        return []

    def about_to_hide_menu(self):
        # When hiding menus we must re-enable all selections in case a shortcut key for the
        # action gets pressed after moving to a new row.
        self.set_enabled_for_all_menu_formats(True)

    def set_enabled_for_menus_in_format(self, book_format, enabled):
        for menu_action in self.menus_by_format[book_format]:
            menu_action.setEnabled(enabled)

    def set_enabled_for_all_menu_formats(self, is_enabled):
        for book_format in self.menus_by_format:
            self.set_enabled_for_menus_in_format(book_format, is_enabled)

    def open_with(self, book_format, external_app_path, app_args):
        if not self.is_library_selected:
            return
        book_ids = self.get_selected_book_ids()
        if not book_ids:
            return error_dialog(self.gui, _('Cannot open with'), _('No book selected'), show=True)
        db = self.gui.library_view.model().db
        paths_to_books = []

        # Check our special case of a format set as "cover" to edit the cover
        if book_format.lower() == 'cover':
            for book_id in book_ids:
                if db.has_cover(book_id):
                    paths_to_books.append(os.path.join(db.library_path,
                            db.path(book_id, index_is_id=True), 'cover.jpg'))
            if not paths_to_books:
                return error_dialog(self.gui, _('Cannot open with'), _('Book has no cover.'), show=True)
        elif book_format.lower() == 'template':
            from calibre.ebooks.metadata.book.formatter import SafeFormat
            safe_format = SafeFormat()
            for book_id in book_ids:
                mi = db.get_metadata(book_id, index_is_id=True)
                paths_to_books.append(safe_format.safe_format(
                        app_args, mi, _('Open With template error'), mi))
        else:
            for book_id in book_ids:
                try:
                    path_to_book = db.format_abspath(book_id, book_format, index_is_id=True)
                except Exception:
                    path_to_book = None
                if path_to_book:
                    paths_to_books.append(path_to_book)

            if not paths_to_books:
                return error_dialog(self.gui, _('Cannot open with'),
                        _('No %s format available. First convert the book to %s.') %
                        (book_format, book_format), show=True)

        # Confirm we have defined an application for that format in tweaks
        if external_app_path is None:
            return error_dialog(self.gui, _('Cannot open with'),
                    _('Path not specified for this format in your configuration.'),
                    show=True)
        is_template = book_format.lower() == 'template'
        self.launch_app(external_app_path, '' if is_template else app_args,
                        paths_to_books, wrap_args=not is_template)

    def launch_app(self, external_app_path, app_args, path_to_file, wrap_args=True):
        if isinstance(path_to_file, (list, tuple)):
            paths_to_files = list(path_to_file)
        else:
            paths_to_files = [path_to_file]
        external_app_path = os.path.expandvars(external_app_path)
        if DEBUG:
            print('Open: ', external_app_path, '(files): ', paths_to_files, ' (args): ', app_args)

        if isosx:
            # For OSX we will not support optional command line arguments currently
            if external_app_path.lower().endswith(".app"):
                args = ['open', '-a', external_app_path] + paths_to_files
            else:
                args = [external_app_path] + paths_to_files
            subprocess.Popen(args)

        else:
            # For Windows/Linux merge any optional command line args with the app/file paths
            app_args_list, has_filename_token, missing_token = self.get_args_list(
                    external_app_path, app_args, paths_to_files)
            if missing_token:
                return error_dialog(self.gui, _('Cannot open with'),
                    _('Not enough selected books have a file for %s.') % missing_token,
                    show=True)
            
            if iswindows:
                # Different behavior required for pre calibre 5.4.0
                # https://www.mobileread.com/forums/showpost.php?p=4048886&postcount=355
                from calibre.constants import numeric_version as calibre_version
                if calibre_version >= (5,4,0):
                    self.launch_windows_5_4_plus(external_app_path, app_args_list, paths_to_files,
                            has_filename_token, wrap_args)
                else:
                    self.launch_windows_pre_5_4(external_app_path, app_args_list, paths_to_files,
                            has_filename_token, wrap_args)
            else: #Linux
                clean_env = dict(os.environ)
                clean_env['LD_LIBRARY_PATH'] = ''
                subprocess.Popen(app_args_list, env=clean_env)

    def get_args_list(self, external_app_path, app_args, paths_to_files):
        # Allow indexed filename tokens in specific argument positions. Without tokens,
        # append every eligible book path as a separate argument.
        if app_args:
            lexer = shlex.shlex(app_args, posix=False)
            lexer.whitespace += ','
            lexer.whitespace_split = True
            raw_args = []
            for arg in lexer:
                if len(arg) > 1 and arg[0] == arg[-1] and arg[0] in ('"', "'"):
                    arg = arg[1:-1]
                raw_args.append(arg)
        else:
            raw_args = []

        app_args_list = []
        has_filename_token = False
        missing_tokens = []
        for arg in raw_args:
            if not FILENAME_TOKEN_PATTERN.search(arg):
                app_args_list.append(arg)
                continue

            has_filename_token = True

            def replace_filename_token(match):
                filename_index = int(match.group(1) or '1') - 1
                if filename_index < 0 or filename_index >= len(paths_to_files):
                    missing_tokens.append(match.group(0))
                    return match.group(0)
                return paths_to_files[filename_index]

            app_args_list.append(FILENAME_TOKEN_PATTERN.sub(replace_filename_token, arg))

        if missing_tokens:
            return None, has_filename_token, missing_tokens[0]

        if not has_filename_token:
            app_args_list.extend(paths_to_files)
        app_args_list.insert(0, external_app_path)
        return app_args_list, has_filename_token, None

    def launch_windows_5_4_plus(self, external_app_path, app_args_list, paths_to_files,
                                has_filename_token, wrap_args=True):
        # Add the files to the recently opened list to support Windows jump lists etc.
        from calibre.gui2 import add_to_recent_docs
        for path_to_file in paths_to_files:
            add_to_recent_docs(path_to_file)

        # Returning to the "old" way of launching processes, where the arguments are passed as a single
        # string to the shell. This is because passing as a list gave out of memory errors for Adobe Acrobat.
        cmd_line = '"%s"'%app_args_list[0]
        file_args_start = len(app_args_list) - len(paths_to_files)
        for i, app_arg in enumerate(app_args_list[1:], start=1):
            is_file_arg = not has_filename_token and i >= file_args_start
            cmd_line += ' "%s"'%app_arg if is_file_arg or wrap_args else ' %s'%app_arg
        with sanitize_env_vars():
            print('cmd_line:', cmd_line)
            DETACHED_PROCESS = 0x00000008
            subprocess.Popen(cmd_line, creationflags=DETACHED_PROCESS)


    def launch_windows_pre_5_4(self, external_app_path, app_args_list, paths_to_files,
                               has_filename_token, wrap_args=True):
        # Add the files to the recently opened list to support Windows jump lists etc.
        from win32com.shell import shell, shellcon
        for path_to_file in paths_to_files:
            shell.SHAddToRecentDocs(shellcon.SHARD_PATHA, path_to_file)
        # As of v1.5.3 will no longer use subprocess because it does not work
        # for users who have non-ascii library paths
        # However we need a special case for Sigil which has issues with C runtime paths
        DETACHED_PROCESS = 0x00000008
        print('About to run a command:', app_args_list)
        if external_app_path.lower().endswith('sigil.exe'):
            clean_env = dict(os.environ)
            del clean_env['PATH']
            subprocess.Popen(app_args_list, creationflags=DETACHED_PROCESS, env=clean_env)
        else:
            from win32process import CreateProcess, STARTUPINFO
            cmd_line = '"%s"'%app_args_list[0]
            file_args_start = len(app_args_list) - len(paths_to_files)
            for i, app_arg in enumerate(app_args_list[1:], start=1):
                is_file_arg = not has_filename_token and i >= file_args_start
                cmd_line += ' "%s"'%app_arg if is_file_arg or wrap_args else ' %s'%app_arg
            si = STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESTDHANDLES
            if DEBUG:
                print('cmd_line: ', cmd_line)
            CreateProcess(None, cmd_line, None, None, False, DETACHED_PROCESS, None, None, si)

    def show_configuration(self):
        self.interface_action_base_plugin.do_user_config(self.gui)
