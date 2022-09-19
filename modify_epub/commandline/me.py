#!/usr/bin/env python
# vim:fileencoding=UTF-8:ts=4:sw=4:sta:et:sts=4:ai
from __future__ import (unicode_literals, division, absolute_import,
                        print_function)
import six

__license__   = 'GPL v3'
__copyright__ = '2012, Grant Drake'

import sys, os, shutil, traceback

from calibre.utils.logging import Log
from calibre.ptempfile import PersistentTemporaryFile

HELP_INFO = '''
To invoke this script:  
 
  calibre-debug -e me.py "input_epub_path" ["output_epub_path"] args

    input_epub_path   - Mandatory. Path to the input epub to be modified. 

    output_epub_path  - Optional. Path to the output epub name after modification. 
                        If not specified, will overwrite the input_epub_path.

    --quiet, --q      - Hide any debug or log output except for errors

    --help, --h       - Display the help listing available options
    
    args              - One or more of the following values:
    
        FILE_OPTIONS
            --remove_itunes_files
            --remove_calibre_bookmarks
            --remove_os_artifacts
            --remove_unused_images
			--unpretty
			--strip_spans
			--strip_kobo
        
        MANIFEST_OPTIONS
            --remove_missing_files
            --add_unmanifested_files
            --remove_unmanifested_files
        
        ADOBE_OPTIONS
            --zero_xpgt_margins
            --remove_xpgt_files
            --remove_drm_meta_tags
        
        TOC_OPTIONS
            --flatten_toc
            --remove_broken_ncx_links
        
        STYLE_OPTIONS
            --encode_html_utf8
            --remove_embedded_fonts
            --rewrite_css_margins
            --append_extra_css
            --smarten_punctuation
            --remove_javascript
        
        JACKET_OPTIONS
            --remove_all_jackets
            --remove_legacy_jackets
        
        COVER_OPTIONS
            --remove_broken_covers
            --remove_cover
            --insert_replace_cover "path_to_image"
        
        METADATA_OPTIONS
            --remove_non_dc_elements

e.g. To view the help output listing command arguments:
    calibre-debug -e me.py --help

e.g. To overwrite an epub in place replacing the cover image 
    calibre-debug -e me.py foo.epub --insert_replace_cover "cover.jpg"

e.g. To write a new bar.epub after smartening punctuation and removing javascript 
    calibre-debug -e me.py foo.epub bar.epub --smarten_punctuation --remove_javascript
'''


UNSUPPORTED_OPTIONS = ['add_replace_jacket', 'update_metadata']
QUIET_OPTIONS = ['q', 'quiet']
HELP_OPTIONS = ['h', 'help']


def dump_help():
    print(HELP_INFO)


def make_absolute_path(file_path):
    if not os.path.isabs(file_path):
        file_path = os.path.join(os.getcwd(), file_path)
        file_path = os.path.normpath(file_path)
    return file_path


def parse_args(args):
    epub_input_path = None
    epub_output_path = None
    options = {}
    cover_path = None
    quiet = False
    
    from calibre_plugins.modify_epub.dialogs import ALL_OPTIONS
    for option_name, _t, _tt in ALL_OPTIONS:
        options[option_name] = False
    i = 0
    aborted = False
    while i < len(args):
        arg = args[i]
        i += 1
        if arg.startswith('--'):
            option_name = arg[2:].lower()
            if option_name in HELP_OPTIONS:
                dump_help()
                aborted = True
                break
            if option_name in UNSUPPORTED_OPTIONS:
                continue
            if option_name in QUIET_OPTIONS:
                quiet = True
            elif option_name in options:
                if option_name == 'insert_replace_cover':
                    if i >= len(args) or args[i].startswith('-'):
                        print('ERROR: --insert_replace_cover requires a path to the cover image')
                        aborted = True
                        break
                    cover_path = make_absolute_path(args[i])
                    i += 1
                options[option_name] = True
            else:
                print(('ERROR: Unknown argument: ', option_name))
                aborted = True
                break
        else:
            # We have some other argument being a path - make it fully qualified
            if epub_input_path is None:
                epub_input_path = make_absolute_path(arg)
            else:
                epub_output_path = make_absolute_path(arg)
    
    if aborted:
        return None, None, None, None, None
    return epub_input_path, epub_output_path, options, cover_path, quiet


def pump_debug_output(epub_input_path, epub_output_path, options, cover_path):
    print('------------------------------------')
    print('MODIFY EPUB OPTIONS')
    print(('Input ePub:  ', epub_input_path))
    if epub_output_path:
        print(('Output epub: ', epub_output_path))
    if cover_path:
        print(('Cover path:  ', cover_path))
    enabled_options = [o for o,v in six.iteritems(options) if v]
    print(('Options:     ', ','.join(enabled_options)))
    print('------------------------------------')


def copy_cover(cover_path):
    # Create a temporary file we can copy a cover argument to since the
    # standard Modify ePub logic will delete file at location passed.
    ext = os.path.splitext(cover_path)[1]
    cf = PersistentTemporaryFile(ext)
    cf.close()
    shutil.copy(cover_path, cf.name)
    return cf.name


def invoke_modify_epub(epub_path, options, cover_path, quiet):
    from calibre_plugins.modify_epub.modify import modify_epub
    if quiet:
        log = Log(Log.ERROR)
    else:
        log = Log()
    title = os.path.basename(epub_path)
    return modify_epub(log, title, epub_path, None, cover_path, options)


def main():
    retcode = 0
    # Get all the following command line arguments
    args = sys.argv[1:]
    try:
        # Parse all the input arguments
        epub_input_path, epub_output_path, options, cover_path, quiet = parse_args(args)

        if not epub_input_path:
            return 2

        # Pump some debug output
        if not quiet:
            pump_debug_output(epub_input_path, epub_output_path, options, cover_path)
        
        # If an epub output path specified, copy our input epub there for modification
        if epub_output_path is None:
            epub_output_path = epub_input_path
        else:
            shutil.copy(epub_input_path, epub_output_path)
            
        # If a path to a cover specified, make a temporary copy as Modify ePub will delete it
        temp_cover_path = None
        if cover_path:
            temp_cover_path = copy_cover(cover_path)

        # Invoke the Modify ePub plugin
        new_epub_path = invoke_modify_epub(epub_output_path, options, temp_cover_path, quiet)

        # If not modified but user specified an output path, remove the unchanged copy
        if not new_epub_path:
            if epub_input_path != epub_output_path:
                os.remove(epub_output_path)
    except:
        print((traceback.format_exc()))
        return 2

    sys.stdout.flush()
    sys.stderr.flush()
    return retcode

if __name__ == "__main__":
    main()

