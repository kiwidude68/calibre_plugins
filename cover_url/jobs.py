from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

import traceback, time
from calibre.gui2.threaded_jobs import ThreadedJob

from calibre_plugins.cover_url.goodreads import GoodreadsCoverWorker

# Pull in translation files for _() strings
try:
    load_translations()
except NameError:
    pass # load_translations() added in calibre 1.9


def start_download_threaded(gui, ids, interval, callback):
    '''
    This approach to download uses an in-process Thread to
    perform the work.
    '''
    job = ThreadedJob('covers plugin',
            _('Download cover urls for %d books')%len(ids),
            download_threaded, (ids, interval, gui.current_db), {}, callback)
    gui.job_manager.run_threaded_job(job)
    gui.status_bar.show_message(_('Download cover urls started'), 3000)


def get_job_details(job):
    '''
    Convert the job result into a set of parameters including a detail message
    summarising the success of the download operation.
    '''
    updated_ids, failed_ids = job.result
    if not hasattr(job, 'html_details'):
        job.html_details = job.details
    det_msg = []
    for i, title, reason in failed_ids:
        det_msg.append('%s - %s'%(title,reason))
    det_msg = '\n'.join(det_msg)
    return updated_ids, failed_ids, det_msg


def download_threaded(ids, interval, db, log=None, abort=None, notifications=None):
    '''
    In combination with start_download_threaded this function performs
    the download of the cover url(s) from a separate thread.
    '''
    ids = list(ids)
    failed_ids = list()
    updated_ids = []
    count = 0
    for book_id in ids:
        if abort.is_set():
            log.error('Aborting...')
            break        
        title = db.title(book_id, index_is_id=True)
        try:
            identifiers = db.get_identifiers(book_id, index_is_id=True)
            goodreads_id = identifiers.get('goodreads', '')
            if not goodreads_id:
                log.error('No Goodreads id for this book. Download metadata first!', book_id)
                failed_ids.append((book_id, title, 'No Goodreads id for this book'))
            else:
                log('Processing %s (%d)'%(title, book_id))
                workers = []
                goodreads_worker = None
                if goodreads_id:
                    log.info('Will search Goodreads using id: %s'% goodreads_id)
                    goodreads_worker = GoodreadsCoverWorker(goodreads_id, log)
                    workers.append(goodreads_worker)

                if (count > 0):
                    log.info('Sleeping before next job for: %d secs'% interval)
                    time.sleep(interval)

                for w in workers:
                    w.start()

                while not abort.is_set():
                    a_worker_is_alive = False
                    for w in workers:
                        w.join(0.2)
                        if abort.is_set():
                            break
                        if w.is_alive():
                            a_worker_is_alive = True
                    if not a_worker_is_alive:
                        break

                cover_url = None
                if goodreads_worker and goodreads_worker.cover_url:
                    log('   Got Goodreads cover url: %s'%(goodreads_worker.cover_url))
                    cover_url = goodreads_worker.cover_url
                if cover_url:
                    updated_ids.append((book_id, cover_url))
                else:
                    log.error('No cover found for book', book_id)
                    failed_ids.append((book_id, title, _('No cover found for book')))
        except:
            log.error(traceback.format_exc())
            failed_ids.append((book_id, title, _('Exception occurred')))
        count += 1
        notifications.put((count/len(ids),
            _('Processed %d of %d')%(count, len(ids))))
    log('Download complete, with %d failures'%len(failed_ids))
    return (updated_ids, failed_ids)
