from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

import os
from calibre.ebooks.conversion.preprocess import HTMLPreProcessor
from calibre.ebooks.oeb.iterator import EbookIterator

from calibre_plugins.extract_isbn.scan import BookScanner

# Define a crude lookup mapping of tuples for when iterating across
# non PDF books that based on the size of the book dictates the ordering
# of how many files to scan at the front of the book, then how many
# from end of book to scan in reverse. Then rest of book is scanned.
# (Min #files, #files at start, #files at end to scan in reverse)
EPUB_FILE_SCANS = [(15, 10, -5),
                   (10, 6, -4),
                   (6, 4, -2),
                   (3, 2, -1),
                   (2, 1, -1),
                   (1, 1, 0)]


def get_isbn_from_non_pdf(log, book_path):
    scanner = BookScanner(log)
    iterator = EbookIterator(book_path)
    try:
        iterator.__enter__(only_input_plugin=True, run_char_count=False,
                           read_anchor_map=False)
        if len(iterator.spine) == 0:
            return
        preprocessor = HTMLPreProcessor()

        def _process_file(path, forward=True):
            if not os.path.exists(path):
                log.error('  File does not exist:', path)
                return
            with open(path, 'rb') as f:
                html = f.read().decode('utf-8', 'replace')
            html = preprocessor(html, get_preprocess_html=True)
            scanner.look_for_identifiers_in_text([html], forward=forward)

        # For PDFs we scan the first 10 pages then the last 5
        # For other formats (all converted to ePub) there is no concept
        # of pages, only files in the spine (manifest).
        # So based on the size of the ePub, we will scan the first few
        # files, then the last few in reverse, then the rest of the content.
        count = len(iterator.spine)
        for min_files, front_count, rear_count in EPUB_FILE_SCANS:
            if count >= min_files:
                first_files = iterator.spine[:front_count]
                last_files = []
                if rear_count != 0:
                    last_files = iterator.spine[rear_count:]
                middle_files = []
                if count - min_files > 0:
                    middle_files = iterator.spine[front_count:rear_count]
                break

        log('  Scanning first %d, then last %d, then remaining %d files' %\
                 (len(first_files), len(last_files), len(middle_files)))
        for path in first_files:
            _process_file(path, forward=True)
            if scanner.has_identifier():
                break

        if not scanner.has_identifier() and last_files:
            for path in reversed(last_files):
                _process_file(path, forward=False)
                if scanner.has_identifier():
                    break

        if not scanner.has_identifier() and middle_files:
            for path in middle_files:
                _process_file(path, forward=True)
                if scanner.has_identifier():
                    break
    finally:
        if iterator:
            iterator.__exit__()

    return scanner.get_isbn_result()
