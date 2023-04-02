from __future__ import unicode_literals, division, absolute_import, print_function

__license__ = 'GPL v3'
__copyright__ = '2011, Grant Drake'

import re, os, shutil

from six import text_type as unicode

from calibre import prints
from calibre.ebooks.oeb.iterator import EbookIterator
from calibre.utils.ipc.simple_worker import fork_job, WorkerError

from calibre_plugins.count_pages.nltk_lite.textanalyzer import TextAnalyzer

RE_HTML_BODY = re.compile(u'<body[^>]*>(.*)</body>', re.UNICODE | re.DOTALL | re.IGNORECASE)
RE_STRIP_MARKUP = re.compile(u'<[^>]+>', re.UNICODE)

def get_pdf_page_count(book_path):
    '''
    Optimisation to read the actual page count for PDFs from the PDF itself.
    '''
    from calibre.ptempfile import TemporaryDirectory
    with TemporaryDirectory('_pages_pdf') as pdfpath:
        pdf_copy = os.path.join(pdfpath, 'src.pdf')
        shutil.copyfile(book_path, pdf_copy)
        try:
            res = fork_job('calibre.ebooks.metadata.pdf', 'read_info',
                    (pdfpath, False))
        except WorkerError as e:
            prints(e.orig_tb)
            raise RuntimeError('Failed to run pdfinfo')
        # Let's try to delete this extra copy straight away
        try:
            os.remove(pdf_copy)
        except:
            pass
        info = res['result']
        if not info:
            raise ValueError('Could not read info dict from PDF')
        if 'Pages' in info:
            return int(info['Pages'])


def get_page_count(iterator, book_path, page_algorithm, custom_chars_per_page=0):
    '''
    Given an iterator for the epub (if already opened/converted), estimate a page count
    '''
    if iterator is None:
        iterator = _open_epub_file(book_path)

    count = 0
    if page_algorithm == 0:
        count = _get_page_count_accurate(iterator)
    elif page_algorithm == 1:
        count = _get_page_count_calibre(iterator)
    elif page_algorithm == 2:
        count = _get_page_count_adobe(iterator, book_path)
    elif page_algorithm == 3:
        count = _get_page_count_custom(iterator, custom_chars_per_page)

    print('\tPage count:', count)
    return iterator, count


def get_word_count(iterator, book_path, icu_wordcount):
    '''
    Given an iterator for the epub (if already opened/converted), estimate a word count
    '''
    from calibre.utils.localization import get_lang
    
    if iterator is None:
        iterator = _open_epub_file(book_path)

    lang = iterator.opf.language
    lang = get_lang() if not lang else lang
    count = _get_epub_standard_word_count(iterator, lang, icu_wordcount)

    print('\tWord count:', count)
    return iterator, count


def _open_epub_file(book_path, strip_html=False):
    '''
    Given a path to an EPUB file, read the contents into a giant block of text
    '''
    iterator = EbookIterator(book_path)
    iterator.__enter__(only_input_plugin=True, run_char_count=True,
            read_anchor_map=False)
    return iterator


def _get_page_count_adobe(iterator, book_path):
    '''
    This algorithm uses the proper adobe count. We look at the compressed size in the
    zip of every file in the spine, and apply the 1024 bytes calculation to that...
    '''
    import math
    from calibre.utils.zipfile import ZipFile

    with ZipFile(book_path, 'r') as zf:
        pages = 0.0
        base = iterator.base
        csizes = {os.path.abspath(os.path.join(base, ci.filename)): ci.compress_size for ci in zf.infolist()}

        for path in iterator.spine:
            sz = csizes.get(os.path.abspath(path))
            if sz is not None:
                pages += math.ceil(sz / 1024.0)

        zf.close()

    return pages


def _get_page_count_calibre(iterator):
    '''
    This algorithm uses the ebook viewer page count.
    '''
    count = sum(iterator.pages)
    return count


def _get_page_count_accurate(iterator):
    '''
    The accurate algorithm attempts to apply a similar algorithm
    used for mobi accurate in apnx.py
    '''
    epub_html = _read_epub_contents(iterator)

    # Decide whether to split on <p> or <div> characters
    num_divs = len(epub_html.split('<div'))
    num_paras = len(epub_html.split('<p'))
    split_char = 'p' if num_paras > num_divs else 'd'

    # States
    in_tag = False
    in_p = False
    check_p = False
    closing = False
    p_char_count = 0

    # Get positions of every line
    # A line is either a paragraph starting
    # or every 70 characters in a paragraph.
    lines = []
    pos = -1
    # We want this to be as fast as possible so we
    # are going to do one pass across the text. re
    # and string functions will parse the text each
    # time they are called.
    #
    # We can can use .lower() here because we are
    # not modifying the text. In this case the case
    # doesn't matter just the absolute character and
    # the position within the stream.
    for c in epub_html.lower():
        pos += 1

        # Check if we are starting or stopping a p tag.
        if check_p:
            if c == '/':
                closing = True
                continue
            elif c == split_char:
                if closing:
                    in_p = False
                else:
                    in_p = True
                    lines.append(pos - 2)
            check_p = False
            closing = False
            continue

        if c == '<':
            in_tag = True
            check_p = True
            continue
        elif c == '>':
            in_tag = False
            check_p = False
            continue

        if in_p and not in_tag:
            p_char_count += 1
            if p_char_count == 70:
                lines.append(pos)
                p_char_count = 0

    # Using 31 lines instead of 32 used by APNX to get the numbers similar
    count = int(len(lines) / 31)
    # We could still have a really weird document and massively understate
    # As a backstop count the characters using the "fast count" algorithm
    # and use that number instead
    fast_count = int(len(epub_html) / 2400) + 1
    if (fast_count > count) :
        # Before we are use the backstop, we should strip out the html
        # otherwise our count could be vastly over-stated.
        epub_html = _read_epub_contents(iterator, strip_html=True)
        fast_count = int(len(epub_html) / 2400) + 1

    print('\tEstimated accurate page count')
    print('\t  Lines:', len(lines), ' Divs:', num_divs, ' Paras:', num_paras)
    print('\t  Accurate count:', count, ' Fast count:', fast_count)
    return max([count, fast_count])


def _get_page_count_custom(iterator, custom_chars_per_page):
    '''
    This algorithm uses a custom algorithm with a user supplied
    average page character count.
    '''
    count = 0
    for path in iterator.spine:
        with open(path, 'rb') as f:
            html = f.read().decode('utf-8', 'replace')
            html = unicode(_extract_body_text(html)).strip()
            count = count + int(len(html) / custom_chars_per_page) + 1
    return count


def _get_epub_standard_word_count(iterator, lang='en', icu_wordcount=False):
    '''
    This algorithm counts individual words instead of pages
    '''

    book_text = _read_epub_contents(iterator, strip_html=True)
    
    wordcount = None
    
    if icu_wordcount:
        try:
            from calibre.spell.break_iterator import count_words
            print('\tWord count using icu_wordcount - trying to count_words')
            wordcount = count_words(book_text, lang)
            print('\tWord count - used count_words:', wordcount)
        except:
            try: # The above method is new and no-one will have it as of 08/01/2016.
                print('\tWord count using icu_wordcount - trying to import split_into_words_and_positions')
                from calibre.spell.break_iterator import split_into_words_and_positions
                print('\tWord count - trying split_into_words_and_positions:')
                wordcount = len(split_into_words_and_positions(book_text, lang))
                print('\tWord count - used split_into_words_and_positions:', wordcount)
            except:
                pass
    if not wordcount: # If not using icu wordcount, or it failed, use the old method.
        from calibre.utils.wordcount import get_wordcount_obj
        print('\tWord count using older method - trying get_wordcount_obj')
        wordcount = get_wordcount_obj(book_text)
        wordcount = wordcount.words

    return wordcount


def _read_epub_contents(iterator, strip_html=False):
    '''
    Given an iterator for an ePub file, read the contents into a giant block of text
    '''
    book_files = []
    for path in iterator.spine:
        with open(path, 'rb') as f:
            html = f.read().decode('utf-8', 'replace')
            if strip_html:
                html = unicode(_extract_body_text(html)).strip()
                #print('FOUND HTML:', html)
        book_files.append(html)
    return ' '.join(book_files)


def _extract_body_text(data):
    '''
    Get the body text of this html content with any html tags stripped
    '''
    body = RE_HTML_BODY.findall(data)
    if body:
        return RE_STRIP_MARKUP.sub('', body[0]).replace('.','. ')
    return ''

# ---------------------------------------------------------
#    CBR/CBZ Page Count Functions
# ---------------------------------------------------------

COMIC_PAGE_EXTENSIONS = ['.jpeg', '.jpg', '.gif', '.png', '.webp']

def get_cbr_page_count(book_path):
    from calibre.utils.unrar import names
    pages = set()
    with open(book_path, 'rb') as rf:
        file_names = list(names(rf))
        for name in file_names:
            if '__MACOSX' in name: continue
            ext = os.path.splitext(name)[1].lower()
            if ext in COMIC_PAGE_EXTENSIONS:
                pages.add(name)
    return len(pages)

def get_cbz_page_count(book_path):
    from calibre.utils.zipfile import ZipFile
    page_count = 0
    with ZipFile(book_path, 'r') as zf:
        for name in zf.namelist():
            if '__MACOSX' in name: continue
            ext = os.path.splitext(name)[1].lower()
            if ext in COMIC_PAGE_EXTENSIONS:
                page_count += 1
    return page_count


# ---------------------------------------------------------
#    Readability Statistics Functions
# ---------------------------------------------------------

def get_text_analysis(iterator, book_path, nltk_pickle):
    '''
    Given an iterator for the epub (if already opened/converted), perform text
    analysis using NLTK to produce a dictionary of analysed statistics for
    attribution like words, sentences, syllables etc that we can then perform
    various official readability computations with.
    '''
    if iterator is None:
        iterator = _open_epub_file(book_path)

    epub_html = _read_epub_contents(iterator, strip_html=True)
    # Lets ignore any html content files less than 500 characters to hopefully
    # stop any skewing of results caused by cover pages etc.
    #epub_html = [h for h in epub_html if len(h) > 500]
    text = ''.join(epub_html).strip()
    # TODO: Do not analyse the WHOLE book - just a portion should be sufficient???

    t = TextAnalyzer(nltk_pickle)
    text_analysis = t.analyzeText(text)
    return iterator, text_analysis

def get_flesch_reading_ease(text_analysis, lang=None):
    if lang and lang == 'deu':
        print('\tFlesch Reading Ease: language=%s' % lang)
        score = 180 - text_analysis['averageWordsPerSentence'] - (58.5 * (text_analysis['syllableCount']/ text_analysis['wordCount'])) 
    else:
        score = 206.835 - (1.015 * (text_analysis['averageWordsPerSentence'])) - (84.6 * (text_analysis['syllableCount']/ text_analysis['wordCount']))
    print('\tFlesch Reading Ease:', score)
    return score

def get_flesch_kincaid_grade_level(text_analysis):
    score = 0.39 * (text_analysis['averageWordsPerSentence']) + 11.8 * (text_analysis['syllableCount']/ text_analysis['wordCount']) - 15.59
    print('\tFlesch Kincade Grade:', score)
    return score

def get_gunning_fog_index(text_analysis):
    score = 0.4 * ((text_analysis['averageWordsPerSentence']) + (100 * (text_analysis['complexwordCount']/text_analysis['wordCount'])))
    print('\tGunning Fog:', score)
    return score


# calibre-debug -e statistics.py
if __name__ == '__main__':
    def test_ntlk(book_path):
        pickle_path = os.path.join(os.getcwd(), 'nltk_lite/english.pickle')
        p = open(pickle_path,'rb').read()
        it, ta = get_text_analysis(None, book_path, p)
        get_flesch_reading_ease(ta)
        get_flesch_kincaid_grade_level(ta)
        get_gunning_fog_index(ta)
        it.__exit__()

    #test_ntlk('''C:\Dev\Tools\eclipse\workspace\_Misc\Test\TestDoc.rtf''')
    get_cbz_page_count('''C:\Dev\Tools\eclipse\workspace\_Misc\misery-depot.zip''')
    get_cbr_page_count('''C:\Dev\Tools\eclipse\workspace\_Misc\misery-depot.cbr''')
