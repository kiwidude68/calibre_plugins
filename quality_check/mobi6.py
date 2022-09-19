from __future__ import absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2012, Kovid Goyal <kovid@kovidgoyal.net>'

from six.moves import range

try:
    load_translations()
except NameError:
    pass # load_translations() added in calibre 1.9

import struct
from io import BytesIO

from calibre.ebooks.metadata.mobi import MetadataUpdater
from calibre.ebooks.mobi import MobiError

class TopazError(ValueError):
    pass

class FireEXTHHeader(object):
    '''
    This is an extension of the calibre EXTHHeader class just for the
    purposes of getting the cdetype field
    '''
    def __init__(self, raw):
        self.doctype = raw[:4]
        self.length, self.num_items = struct.unpack('>LL', raw[4:12])
        raw = raw[12:]
        pos = 0
        left = self.num_items
        self.cdetype = ''
        self.asin = ''
        self.asin2 = ''
        self.clipping_limit = None

        while left > 0:
            left -= 1
            idx, size = struct.unpack('>LL', raw[pos:pos + 8])
            content = raw[pos + 8:pos + size]
            pos += size
            if idx == 113:
                # asin
                self.asin = content
            elif idx == 401:
                # clippinglimit
                self.clipping_limit = ord(content)
            elif idx == 501:
                # cdetype
                self.cdetype = content
            elif idx == 504:
                # cdetype
                self.asin2 = content


class MinimalMobiHeader(object):

    def __init__(self, raw, log):
        self.log = log
        if len(raw) <= 16:
            self.exth_flag, self.exth = 0, None
        else:
            self.exth_flag, = struct.unpack('>L', raw[0x80:0x84])
            self.length, self.type, self.codepage, self.unique_id, \
                self.version = struct.unpack('>LLLLL', raw[20:40])
            self.exth = None
            if self.exth_flag & 0x40:
                try:
                    self.exth = FireEXTHHeader(raw[16 + self.length:])
                except:
                    self.log.exception('Invalid EXTH header')
                    self.exth_flag = 0


class MinimalMobiReader(object):

    def __init__(self, filename, log):
        self.log = log

        stream = open(filename, 'rb')
        self.stream = stream

        raw = stream.read()
        if raw.startswith(b'TPZ'):
            raise TopazError(_('This is an Amazon Topaz book. It cannot be processed.'))

        self.header   = raw[0:72]
        self.name     = self.header[:32].replace(b'\x00', b'')
        self.num_sections, = struct.unpack('>H', raw[76:78])

        self.ident = self.header[0x3C:0x3C + 8].upper()
        if self.ident not in [b'BOOKMOBI', b'TEXTREAD']:
            raise MobiError(_('Unknown book type: %s') % repr(self.ident))

        self.sections = []
        self.section_headers = []
        for i in range(self.num_sections):
            offset, a1, a2, a3, a4 = struct.unpack('>LBBBB', raw[78 + i * 8:78 + i * 8 + 8])
            flags, val = a1, a2 << 16 | a3 << 8 | a4
            self.section_headers.append((offset, flags, val))

        def section(section_number):
            if section_number == self.num_sections - 1:
                end_off = len(raw)
            else:
                end_off = self.section_headers[section_number + 1][0]
            off = self.section_headers[section_number][0]
            return raw[off:end_off]

        for i in range(self.num_sections):
            self.sections.append((section(i), self.section_headers[i]))

        self.book_header = MinimalMobiHeader(self.sections[0][0], self.log)

    def __enter__(self):
        return self

    def __exit__(self, _type, value, traceback):
        if self.stream:
            self.stream.close()
            self.stream = None


class MinimalMobiUpdater(MetadataUpdater):

    def update(self, asin=None, cdetype=None):
        def update_exth_record(rec):
            recs.append(rec)
            if rec[0] in self.original_exth_records:
                self.original_exth_records.pop(rec[0])

        if self.type != b"BOOKMOBI":
                raise MobiError(_("Setting ASIN only supported for MOBI files of type 'BOOK'.")+"\n"
                                "\tThis is a '%s' file of type '%s'" % (self.type[0:4], self.type[4:8]))
        recs = []
        if asin is not None:
            update_exth_record((113, asin.encode(self.codec, 'replace')))
            update_exth_record((504, asin.encode(self.codec, 'replace')))
        if cdetype is not None:
            update_exth_record((501, cdetype))

        # Include remaining original EXTH fields
        for id_ in sorted(self.original_exth_records):
            recs.append((id_, self.original_exth_records[id_]))
        recs = sorted(recs, key=lambda x:(x[0],x[0]))

        exth = BytesIO()
        for code, data in recs:
            exth.write(struct.pack('>II', int(code), len(data) + 8))
            exth.write(data)
        exth = exth.getvalue()
        trail = len(exth) % 4
        pad = b'\0' * (4 - trail) # Always pad w/ at least 1 byte
        exth = [b'EXTH', struct.pack(b'>II', len(exth) + 12, len(recs)), exth, pad]
        exth = b''.join(exth)

        if getattr(self, 'exth', None) is None:
            raise MobiError(_('No existing EXTH record. Cannot update ASIN.'))

        self.create_exth(exth=exth)

