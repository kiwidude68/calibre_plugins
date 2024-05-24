from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

import errno, os, subprocess, shutil
from lxml import etree

# calibre Python 3 compatibility.
from six import text_type as unicode

from calibre import prints, CurrentDir
from calibre.constants import iswindows, isbsd, filesystem_encoding
from calibre.customize import numeric_version
from calibre.ebooks import ConversionError, DRMError
from calibre.ptempfile import TemporaryDirectory, PersistentTemporaryFile
from calibre.utils.cleantext import clean_ascii_chars
from calibre.utils.ipc.simple_worker import fork_job, WorkerError
from calibre.utils.logging import GUILog

from calibre_plugins.extract_isbn.scan import BookScanner

FRONT_PAGES = 10
BACK_PAGES = 5


def get_isbn_from_pdf(log, pdf_path):
    '''
    On a forked job execute pdfinfo to read a page count and then pdftohtml
    to get the page count as an xml file.
    '''
    with TemporaryDirectory('_isbn_pdf') as output_dir:
        pdf_copy = os.path.join(output_dir, u'src.pdf')
        with open(pdf_path, 'rb') as src, open(pdf_copy, 'wb') as dest:
            shutil.copyfileobj(src, dest)

        try:
            # We want to run the scanning of the PDF on a fork_job, however
            # that will only be "fixed" in calibre 0.8.55 to allow calling
            # a calibre plugin from such a job. In the meantime, do it the
            # risky way of calling from in-process.
            if numeric_version < (0, 8, 55):
                log.error('Warning: PDF analysis may crash, upgrade to calibre 0.8.55 when possible')
                return get_isbn(output_dir, 'src.pdf', log)

            res = fork_job('calibre_plugins.extract_isbn.pdf', 'get_isbn',
                    (output_dir, 'src.pdf'))
        except WorkerError as e:
            prints(e.orig_tb)
            raise RuntimeError('Failed to run pdfinfo/pdftohtml')
        finally:
            try:
                os.remove(pdf_copy)
            except:
                pass
    info = res['result']
    with open(res['stdout_stderr'], 'rb') as f:
        raw = f.read().strip()
        if raw:
            log(raw)
    return info


def get_isbn(output_dir, pdf_name, log=None):
    is_running_on_fork = False
    if log is None:
        log = GUILog()
        is_running_on_fork = True
    try:
        total_pages = get_page_count(log, output_dir, pdf_name)
        if total_pages is None:
            log.info('get_isbn() found no page count so aborting')
            return None
        
        scanner = BookScanner(log)

        if total_pages <= FRONT_PAGES + BACK_PAGES:
            # No point in doing all the complexity of ranges
            text = call_pdftohtml(log, output_dir, pdf_name)
            scanner.look_for_identifiers_in_text([text])
        else:
            text = call_pdftohtml(log, output_dir, pdf_name, 1, FRONT_PAGES)
            scanner.look_for_identifiers_in_text([text])
            if not scanner.has_identifier():
                text = call_pdftohtml(log, output_dir, pdf_name, total_pages-BACK_PAGES, total_pages)
                scanner.look_for_identifiers_in_text([text])
        return scanner.get_isbn_result()
    finally:
        if is_running_on_fork:
            # We need to print our log out so the parent process can re-log it.
            print(log.html)


def get_page_count(log, output_dir, pdf_name):
    '''
    Try to use podofo to parse the page count.
    This apparently can file for badly formatted pdfs in which case fall back to
    trying to use pdfinfo (which some users have reported issues with).
    '''
    from calibre.utils.podofo import get_podofo
    podofo = get_podofo()
    try:
        p = podofo.PDFDoc()
        path = os.path.join(output_dir, pdf_name)
        with open(path, 'rb') as f:
            raw = f.read()
        p.load(raw)
        page_count = p.page_count()
        log.info('  PDF page count using podofo:', page_count)
        return int(page_count)
    except:
        log.error('get_page_count failed to retrieve using podofo')
        return get_page_count_using_pdfinfo(log, output_dir, pdf_name)

def get_page_count_using_pdfinfo(log, output_dir, pdf_name):
    '''
    Read info dict and cover from a pdf file named src.pdf in output_dir.
    Note that this function changes the cwd to output_dir and is therefore not
    thread safe. Run it using fork_job. This is necessary as there is no safe
    way to pass unicode paths via command line arguments. This also ensures
    that if poppler crashes, no stale file handles are left for the original
    file, only for src.pdf.
    '''

    from calibre.ebooks.pdf.pdftohtml import PDFTOHTML
    os.chdir(output_dir)
    base = os.path.dirname(PDFTOHTML)
    suffix = '.exe' if iswindows else ''
    pdfinfo = os.path.join(base, 'pdfinfo') + suffix

    with CurrentDir(output_dir):
        try:
            log.info('get_page_count_using_pdfinfo() invoking exe: ', pdfinfo)
            raw = subprocess.check_output([pdfinfo, '-enc', 'UTF-8', pdf_name])
        except subprocess.CalledProcessError as e:
            log.error('pdfinfo errored out with return code: %d'%e.returncode)
            return None

    # Process the output into a dictionary which will include the page info.
    try:
        raw = raw.decode('utf-8')
        log.info('get_page_count_using_pdfinfo() returned UTF-8 data')
    except UnicodeDecodeError:
        log.info('pdfinfo returned no UTF-8 data')
        return None

    ans = {}
    for line in raw.splitlines():
        if u':' not in line: continue
        field, val = line.partition(u':')[::2]
        val = val.strip()
        if field and val:
            ans[field] = val.strip()

    if 'Pages' in ans:
        log.info('  PDF page count using pdfinfo:', ans['Pages'])
        return int(ans['Pages'])


def call_pdftohtml(log, output_dir, pdf_name, first=None, last=None):
    '''
    Convert the pdf into html using the pdftohtml app.
    This will write the xml as index.xml into output_dir.
    '''
    from calibre.ebooks.pdf.pdftohtml import PDFTOHTML, popen

    pdfsrc = os.path.join(output_dir, pdf_name)
    index_file = os.path.join(output_dir, u'index.xml')

    if os.path.exists(index_file):
        os.remove(index_file)

    with CurrentDir(output_dir):
        # This is necessary as pdftohtml doesn't always (linux) respect
        # absolute paths. Also, it allows us to safely pass only bytestring
        # arguments to subprocess on widows

        # subprocess in python 2 cannot handle unicode arguments on windows
        # that cannot be encoded with mbcs. Ensure all args are bytestrings.
        def a(x):
            return os.path.basename(x).encode('ascii')

        log.info('call_pdftohtml() scanning pdf from page:', first, 'to:', last)
        exe = PDFTOHTML.encode(filesystem_encoding) if isinstance(PDFTOHTML,
                unicode) else PDFTOHTML

        cmd = [exe, b'-enc', b'UTF-8', b'-noframes', b'-p', b'-nomerge',
                b'-nodrm', b'-q', b'-c', b'-hidden', a(pdfsrc), a(index_file), b'-xml', b'-i']

        if isbsd:
            cmd.remove(b'-nodrm')
        if first is not None:
            cmd.append(b'-f')
            cmd.append(str(first))
        if last is not None:
            cmd.append(b'-l')
            cmd.append(str(last))

        logf = PersistentTemporaryFile(u'pdftohtml_log')
        try:
            log.info('call_pdftohtml() launching process:', cmd)
            p = popen(cmd, stderr=logf._fd, stdout=logf._fd,
                    stdin=subprocess.PIPE)
        except OSError as err:
            if err.errno == errno.ENOENT:
                raise ConversionError(
                    _('Could not find pdftohtml, check it is in your PATH'))
            else:
                raise

        while True:
            try:
                ret = p.wait()
                break
            except OSError as e:
                if e.errno == errno.EINTR:
                    continue
                else:
                    raise
        logf.flush()
        logf.close()
        log.info('call_pdftohtml() reading log output')
        out = open(logf.name, 'rb').read().strip()
        if ret != 0:
            raise ConversionError(out)
        if out:
            log('pdftohtml log:')
            log(out)
        if not os.path.exists(index_file) or os.stat(index_file).st_size < 100:
            raise DRMError()

        log.info('call_pdftohtml() reading index file', index_file)
        with open(index_file, 'rb') as f:
            root = etree.fromstring(clean_ascii_chars(f.read()))
            text = etree.tostring(root, method='text', encoding='unicode')
            return text
