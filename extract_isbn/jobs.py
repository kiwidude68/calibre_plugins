from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

import sys, time
from threading import Event

from calibre.gui2.convert.single import sort_formats_by_preference
from calibre.gui2.threaded_jobs import ThreadedJob
from calibre.utils.config import prefs
from calibre.utils.ipc.server import Server
from calibre.utils.ipc.job import ParallelJob
from calibre.utils.logging import Log

from calibre_plugins.extract_isbn.pdf import get_isbn_from_pdf
from calibre_plugins.extract_isbn.nonpdf import get_isbn_from_non_pdf

try:
    load_translations()
except NameError:
    pass # load_translations() added in calibre 1.9

# ------------------------------------------------------------------------------
#
#              Functions to perform extraction using ThreadedJob
#
# ------------------------------------------------------------------------------

def start_extract_threaded(gui, ids, callback):
    '''
    This approach to extracting an ISBN uses an in-process Thread to
    perform the work. This offers high performance, but suffers from
    memory leaks in the Calibre conversion process and will make the
    GUI less responsive for large numbers of books.

    It is retained only for the purposes of extracting a single ISBN
    as it is considerably faster than the out of process approach.
    '''
    job = ThreadedJob('extract isbn plugin',
            _('Extract ISBN for %d books')%len(ids),
            extract_threaded, (ids, gui.current_db), {}, callback)
    gui.job_manager.run_threaded_job(job)
    gui.status_bar.show_message(_('Extract ISBN started'), 3000)


def extract_threaded(ids, db, log=None, abort=None, notifications=None):
    '''
    In combination with start_extract_threaded this function performs
    the scan of the book(s) from a separate thread.
    '''
    ids = list(ids)
    same_isbn_ids = []
    input_map = prefs['input_format_order']
    failed_ids = list()
    no_format_ids = list()
    extracted_ids = []
    count = 0
    for book_id in ids:
        if abort.is_set():
            log.error('Aborting...')
            break
        mi = db.get_metadata(book_id, index_is_id=True, get_user_categories=False)
        title, formats = mi.title, mi.formats
        if not formats:
            log.error('  No formats available for', title)
            failed_ids.append((book_id, title))
            no_format_ids.append((book_id, title))
        else:
            # Sorted formats using the preferred input conversion list.
            sorted_formats = sort_formats_by_preference(formats, input_map)
            paths_for_formats = []
            for f in sorted_formats:
                paths_for_formats.append((f, db.format_abspath(book_id, f, index_is_id=True)))
            isbn = None
            try:
                isbn = scan_for_isbn(log, Event(), title, paths_for_formats)
            except Exception as e:
                import traceback
                traceback.print_exc()
                log.error('Exception when scanning for ISBN:', e)
                pass
            if isbn:
                if mi.isbn == isbn:
                    log.debug('  Identical ISBN extracted of: %s'%(isbn,))
                    same_isbn_ids.append((book_id, title))
                else:
                    log.warn('  New ISBN extracted of: %s'%(isbn,))
                    extracted_ids.append((book_id, title, mi.last_modified, isbn))
            else:
                log.error('  Failed to extract ISBN')
                failed_ids.append((book_id, title))
        log.info('===================================================')
        count += 1
        notifications.put((count/len(ids),
            _('Scanned %d of %d')%(count, len(ids))))
    log('Scan complete, with %d failures'%len(failed_ids))
    return (extracted_ids, same_isbn_ids, failed_ids, no_format_ids)


def get_job_details(job):
    '''
    Convert the job result into a set of parameters including a detail message
    summarising the success of the extraction operation.
    This is used by both the threaded and worker approaches to extraction
    '''
    extracted_ids, same_isbn_ids, failed_ids, no_format_ids = job.result
    if not hasattr(job, 'html_details'):
        job.html_details = job.details
    det_msg = []
    for i, title in failed_ids:
        if i in no_format_ids:
            msg = title + ' ('+_('No formats')+')'
        else:
            msg = title + ' ('+_('ISBN not found')+')'
        det_msg.append(msg)
    if same_isbn_ids:
        if det_msg:
            det_msg.append('----------------------------------')
        for i, title in same_isbn_ids:
            msg = title + ' ('+_('Same ISBN')+')'
            det_msg.append(msg)
    if len(extracted_ids) > 0:
        if det_msg:
            det_msg.append('----------------------------------')
        for i, title, _last_modified, isbn in extracted_ids:
            msg = ('%s ('+_('Extracted')+' %s)')%(title, isbn)
            det_msg.append(msg)

    det_msg = '\n'.join(det_msg)
    return extracted_ids, same_isbn_ids, failed_ids, det_msg


# ------------------------------------------------------------------------------
#
#              Functions to perform extraction using worker jobs
#
# ------------------------------------------------------------------------------

def do_extract_worker(books_to_scan, failed_ids, no_format_ids,
                      cpus, notification=lambda x,y:x):
    '''
    Master job, to launch child jobs to extract ISBN for a set of books
    This is run as a worker job in the background to keep the UI more
    responsive and get around the memory leak issues as it will launch
    a child job for each book as a worker process
    '''
    server = Server(pool_size=cpus)

    # Queue all the jobs
    for book_id, title, modified_date, existing_isbn, paths_for_formats in books_to_scan:
        args = ['calibre_plugins.extract_isbn.jobs', 'do_extract_isbn_for_book_worker',
                (title, paths_for_formats)]
        job = ParallelJob('arbitrary', str(book_id), done=None, args=args)
        job._book_id = book_id
        job._title = title
        job._modified_date = modified_date
        job._existing_isbn = existing_isbn
        server.add_job(job)

    # This server is an arbitrary_n job, so there is a notifier available.
    # Set the % complete to a small number to avoid the 'unavailable' indicator
    notification(0.01, 'Extracting ISBN')

    # dequeue the job results as they arrive, saving the results
    total = len(books_to_scan)
    count = 0
    extracted_ids, same_isbn_ids = [], []
    while True:
        job = server.changed_jobs_queue.get()
        # A job can 'change' when it is not finished, for example if it
        # produces a notification. Ignore these.
        job.update()
        if not job.is_finished:
            continue
        # A job really finished. Get the information.
        isbn = job.result
        book_id = job._book_id
        title = job._title
        count = count + 1
        notification(float(count)/total, 'Extracted ISBN')
        # Add this job's output to the current log
        print('Logfile for book ID %d (%s)'%(book_id, title))
        print(job.details)
        if isbn:
            if job._existing_isbn == isbn:
                print('  Identical ISBN extracted of: %s'%(isbn,))
                same_isbn_ids.append((book_id, title))
            else:
                print('  New ISBN extracted of: %s'%(isbn,))
                extracted_ids.append((book_id, title, job._modified_date, isbn))
        else:
            print('  Failed to extract ISBN')
            failed_ids.append((book_id, title))
        print('===================================================')

        if count >= total:
            # All done!
            break

    server.close()
    # return the map as the job result
    return extracted_ids, same_isbn_ids, failed_ids, no_format_ids


def do_extract_isbn_for_book_worker(title, paths_for_formats):
    '''
    Child job, to extract isbn from formats for this specific book,
    when run as a worker job
    '''
    log = Log()
    abort = Event()
    try:
        return scan_for_isbn(log, abort, title, paths_for_formats, in_process=False)
    except:
        return None


# ------------------------------------------------------------------------------
#
#              Actually perform the work (shared by both approaches)
#
# ------------------------------------------------------------------------------

def scan_for_isbn(log, abort, title, paths_for_formats, timeout=30, in_process=True):
    if title == _('Unknown'):
        title = None
    start_time = time.time()
    '''
    kwargs = {
        'title': title,
        'paths': paths_for_formats,
        'timeout': timeout,
    }

    log('Running scan for isbn query with parameters:')
    log(kwargs)
    '''

    # For an initial implementation we will not use child threads to scan each format
    for book_format, book_path in paths_for_formats:
        if abort.is_set():
            break
        isbn = scan_format_for_isbn(log, title, book_format, book_path)
        if isbn:
            log('  The isbn was found in %.2f secs'%(time.time() - start_time))
            return isbn

    log('  The scan failed to find an isbn in %.2f secs'%(time.time() - start_time))
    return None


def scan_format_for_isbn(log, title, book_format, book_path, in_process=True):
    try:
        log.info('===================================================')
        log.info('Title:  %s'% title)
        log.info('Format: %s'% book_format)
        if in_process:
            log.info('Path:   %s'% book_path)
        log.info('---------------------------------------------------')
        start = time.time()
        if book_format == 'PDF':
            isbn = get_isbn_from_pdf(log, book_path)
        else:
            isbn = get_isbn_from_non_pdf(log, book_path)
        log.info('  Scan time: %.2f secs' % (time.time() - start,))
    except ValueError as e:
        log.info('  Scan time: %.2f secs' % (time.time() - start,))
        log.exception('ERROR: %s' % e)
    except:
        log.exception('ERROR: %s' % sys.exc_info()[1])
    else:
        return isbn
