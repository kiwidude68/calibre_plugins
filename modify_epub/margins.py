from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

import six
import re

from calibre.constants import iswindows
from calibre.ebooks.oeb.base import XPath

RE_BOOK_MGNS = re.compile(r'(?P<cssid>#\w+\s+)?(?P<selector>(?<!\.)\bbody|@page)\b\s*{(?P<styles>[^}]*margin[^}]+);?\s*\}', re.UNICODE)
CSS_MIME_TYPES = ['text/css']
HTML_MIME_TYPES = ['application/xhtml+xml']
EOLF = '\r\n' if iswindows else '\r'

class MarginsUpdater(object):

    def __init__(self, log, container):
        self.log = log
        self.container = container

    def _get_user_margins(self):
        calibre_default_margins = {
            'margin_right' : 5.0,
              'margin_top' : 5.0,
             'margin_left' : 5.0,
           'margin_bottom' : 5.0,
                    }
        from calibre.ebooks.conversion.config import load_defaults
        ps = load_defaults('page_setup')
        # Only interested in the margins out of page setup settings
        prefs_margins = dict((k,v) for k,v in six.iteritems(ps) if k.startswith('margin_'))
        if 'margin_top' not in prefs_margins:
            # The user has never changed their page setup defaults to save settings
            prefs_margins = calibre_default_margins
        return prefs_margins

    def _prefs_to_css_properties(self, user_margins):
        css_margins = ''
        for pref, value in six.iteritems(user_margins):
            # Negative margins mean we don't want the attribute written
            if value >= 0.0:
                property_name = re.sub('_', '-', pref)
                if value > 0.0:
                    css_margins += property_name+': '+str(value)+'pt; '
                else:
                    css_margins += property_name+': 0; '
        return css_margins.strip()

    def _match_margins(self, match, allow_less=False):
        match = match[0]
        doc_defined_margins = {}

        styles = match[2].lower().strip()
        # delete trailing semicolons
        styles = re.sub('\s*;$', '', styles)
        # match string to prefs
        styles = re.sub('margin-', 'margin_', styles)
        if match[1].lower() == 'body' and styles.find('margin') != -1:
            return True

        stylelist = styles.split(';')
        for style in stylelist:
            if not style.strip():
                continue
            style = [s.strip() for s in style.split(':')]
            property_type = re.sub('-','_', style[0])
            value = float(re.sub('[^\d.]+', '', style[1]))

            if property_type == 'margin': # Not a calibre set value, so we will just replace the whole value
                return True
            if value < 0:  # Definitely not going to match, since negative values reserved to omit margins
                return True
            if property_type.startswith('margin_'):
                if style[1].endswith('pt'):  # Possibly created by calibre since in pts, add to our dimensions
                    doc_defined_margins[property_type] = value
                elif not style[1][-1:].isalpha():  # This is a value with an unspecified unit, might still be by calibre if zero
                    if value == 0.0:
                        doc_defined_margins[property_type] = value
                    else:
                        return True

        # If we got to here, then we found "some" margins in the style that are
        # either identical or a subset of our preferred margins
        for pref, pref_value in six.iteritems(self.user_margins):
            if pref_value < 0.0:  # The user does not want this margin defined
                if pref in doc_defined_margins:  # Currently is defined, so remove it
                    return True
            elif pref not in doc_defined_margins: # Not defined, so add it
                return True
            else:
                doc_value = doc_defined_margins[pref]
                if doc_value != pref_value:
                    if not (doc_value < pref_value and allow_less):
                        return True
        # If we got to here everything matches our prefs
        return False

    def _modify_margins(self, match):
        css_id = match.group('cssid')
        styles = match.group('styles').strip()
        # delete trailing semicolons
        styles = re.sub('\s*;$', '', styles)
        stylelist = styles.split(';')
        retained_styles = []
        for style in stylelist:
            if style.lower().strip().startswith('margin'):
                pass
            elif style:
                retained_styles.append(style.strip())

        if match.group('selector') == '@page' and self.css_user_margins:
            final_styles = ''
            if len(retained_styles) >= 1:
                remaining_styles = '; '.join(retained_styles)
                final_styles = self.css_user_margins+remaining_styles
            else:
                final_styles = self.css_user_margins
            return match.group('selector')+' { '+final_styles+' }'

        elif len(retained_styles) >= 1:
            remaining_styles = '; '.join(retained_styles)
            if css_id:
                return css_id+match.group('selector')+' { '+remaining_styles+' }'
            else:
                return match.group('selector')+' { '+remaining_styles+' }'
        else:
            return ''

    def _modify_inline_margins(self, data):
        HTML_HEAD = re.compile(r'^(.*?</head>)', re.DOTALL)
        m = HTML_HEAD.match(data)
        mod_data = RE_BOOK_MGNS.sub(self._modify_margins, m.group(0))
        data = HTML_HEAD.sub(mod_data, data)
        return data

    def _remove_empty_css_files(self, css_files_to_remove):
        self.log('\t  Removing empty css files')
        for css_file in css_files_to_remove:
            for name in self.container.get_html_names():
                html = self.container.get_parsed_etree(name)
                try:
                    css_links = XPath('//h:link[@rel="stylesheet" and @href]')(html)
                except:
                    css_links = []
                for css_link in css_links:
                    href = css_link.get('href').lower()
                    href_name = self.container.abshref(href, name)
                    if href_name.lower() == css_file.lower():
                        css_link.getparent().remove(css_link)
                        self.log('\t    Removed css link from:', name)
                        self.container.set(name, html)
            self.container.delete_from_manifest(css_file, delete_from_toc=False)

    def rewrite_css_margins(self):
        dirtied = False

        # check user margin prefs
        self.user_margins = self._get_user_margins()
        self.css_user_margins = self._prefs_to_css_properties(self.user_margins)

        css_files_to_remove = []
        for name in self.container.name_path_map:
            mt = self.container.mime_map.get(name, '')
            extension = name[name.lower().rfind("."):].lower()

            if extension in ['.jpg', '.jpeg', '.gif', '.ncx',
                   '.opf', '.xpgt', '.otf','.ttf', '.png']:
                continue

            if name.endswith('titlepage.xhtml'):
                continue

            if mt.lower() in CSS_MIME_TYPES:
                # read the data here because we know it is text, avoiding image decoding
                data = self.container.get_raw(name)
                page_style_exists = True if data.find('@page') != -1 else False
                css_dirtied = False
                match_styles = RE_BOOK_MGNS.findall(data)
                if len(match_styles) > 1:
                    css_dirtied = True
                    data = RE_BOOK_MGNS.sub(self._modify_margins, data)

                elif len(match_styles) == 1:
                    if self._match_margins(match_styles):
                        css_dirtied = True
                        data = RE_BOOK_MGNS.sub(self._modify_margins, data)

                if not page_style_exists and self.css_user_margins:
                    css_dirtied = True
                    data = '@page { ' + self.css_user_margins + ' }' + EOLF + data

                if css_dirtied:
                    self.log('\t  Modified CSS margins in:', name)
                    self.container.set(name, data)
                    dirtied = True

                if len(data.strip()) == 0:
                    self.log('\t    CSS file now empty so will be deleted:', name)
                    css_files_to_remove.append(name)

            elif mt.lower() in HTML_MIME_TYPES:
                # read the data here because we know it is text, avoiding image decoding
                data = self.container.get_raw(name)
                if RE_BOOK_MGNS.findall(data[:1000]):
                    match_styles = RE_BOOK_MGNS.findall(data[:1000])
                    resource_dirtied = False
                    if len(match_styles) > 1:
                        resource_dirtied = True
                        data = self._modify_inline_margins(data)

                    elif len(match_styles) == 1:
                        if self._match_margins(match_styles, True):
                            resource_dirtied = True
                            data = self._modify_inline_margins(data)

                    if resource_dirtied:
                        self.log('\t  Modified inline CSS margins in:', name)
                        self.container.set(name, data)
                        dirtied = True

        if css_files_to_remove:
            self._remove_empty_css_files(css_files_to_remove)
            dirtied = True

        return dirtied

