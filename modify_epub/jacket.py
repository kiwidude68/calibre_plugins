from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

import os
from calibre.ebooks.oeb.transforms.jacket import render_jacket

def add_replace_jacket(container, log, mi, output_profile, jacket_end_book):
    log('\tAdding or updating jacket')
    remove_non_legacy_jacket(container, log)
    jacket_data = render_jacket(mi, output_profile)

    # Make sure the id and href for this jacket do not conflict with any
    # unrelated existing files.

    id, href = container.generate_unique('calibre_jacket', 'jacket.xhtml')
    opf_path = os.path.dirname(container.name_path_map[container.opf_name])

    # That href will have been generated assuming same directory as opf
    path = os.path.join(opf_path, href)
    name = href

    # Put the data in our container data cache to ensure included when ePub rebuilt
    container.name_path_map[name] = path
    container.set(name, jacket_data)

    # Now we need to add to the manifest
    container.add_to_manifest(id, href)

    # Next add it to the spine. We want it at the start of the book, but
    # after the Calibre titlepage
    # TODO: Might want to make this a bit more bulletproof by looking at the guide etc.

    insert_pos = 0
    spine_items = list(container.get_spine_items())
    if len(spine_items) and spine_items[0].get('id').startswith('titlepage'):
        insert_pos = 1
    if jacket_end_book:
        insert_pos = -1
    container.add_to_spine(id, index=insert_pos)
    container.set(container.opf_name, container.opf)
    return True

def remove_non_legacy_jacket(container, log):
    for name in list(container.name_path_map.keys()):
        if 'jacket' in name and name.endswith('.xhtml'):
            data = container.get_parsed_etree(name)
            if is_current_jacket(data):
                log('\t Current jacket removed: ', name)
                container.delete_from_manifest(name)
                return

def remove_legacy_jackets(container, log):
    log('\tLooking for legacy jackets')
    dirtied = False
    for name in list(container.name_path_map.keys()):
        if 'jacket' in name and name.endswith('.xhtml'):
            data = container.get_parsed_etree(name)
            if not is_current_jacket(data) and is_legacy_jacket(data):
                log('\t Legacy jacket found: ', name)
                dirtied = True
                container.delete_from_manifest(name)
    return dirtied

def remove_all_jackets(container, log):
    log('\tLooking for all jackets')
    dirtied = False
    for name in list(container.name_path_map.keys()):
        if 'jacket' in name and name.endswith('.xhtml'):
            data = container.get_parsed_etree(name)
            if is_current_jacket(data) or is_legacy_jacket(data):
                log('\t Jacket removed: ', name)
                dirtied = True
                container.delete_from_manifest(name)
    return dirtied

def is_legacy_jacket(html):
    nodes = html.xpath('//x:h1[starts-with(@class,"calibrerescale")]',
            namespaces={'x':'http://www.w3.org/1999/xhtml'})
    if not nodes:
        nodes = html.xpath('//x:h2[starts-with(@class,"calibrerescale")]',
            namespaces={'x':'http://www.w3.org/1999/xhtml'})
    return len(nodes) > 0

def is_current_jacket(html):
    nodes = html.xpath('//x:meta[@name="calibre-content" and @content="jacket"]',
            namespaces={'x':'http://www.w3.org/1999/xhtml'})
    return len(nodes) > 0
