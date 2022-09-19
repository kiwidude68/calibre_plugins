from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

import traceback, time
from calibre.gui2.threaded_jobs import ThreadedJob

# Pull in translation files for _() strings
try:
    load_translations()
except NameError:
    pass # load_translations() added in calibre 1.9

from calibre_plugins.ratings.amazon import AmazonRatingWorker, AMAZON_DOMAINS
from calibre_plugins.ratings.goodreads import GoodreadsRatingWorker

def start_download_threaded(gui, ids, include_amazon, include_goodreads, callback):
    '''
    This approach to download uses an in-process Thread to
    perform the work.
    '''
    job = ThreadedJob('ratings plugin',
            _('Download ratings for %d books')%len(ids),
            download_threaded, (ids, include_amazon, include_goodreads, gui.current_db), {}, callback)
    gui.job_manager.run_threaded_job(job)
    gui.status_bar.show_message(_('Download Ratings started'), 3000)


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

def get_amazon_domain_and_asin(identifiers, extra_domains=()):
    identifiers = {k.lower(): v for k, v in identifiers.items()}
    for key, val in identifiers.items():
        if key in ('amazon', 'asin'):
            return 'com', val
        if key.startswith('amazon_'):
            domain = key.partition('_')[-1]
            if domain and (domain in AMAZON_DOMAINS or domain in extra_domains):
                return domain, val
    return None, None

def download_threaded(ids, include_amazon, include_goodreads, db, log=None, abort=None, notifications=None):
    '''
    In combination with start_download_threaded this function performs
    the download of the rating(s) from a separate thread.
    '''
    ids = list(ids)
    failed_ids = list()
    updated_ids = []
    count = 0
    log('User requested read from Amazon: %s Goodreads: %s'%(include_amazon, include_goodreads))
    for book_id in ids:
        if abort.is_set():
            log.error(_('Aborting')+'...')
            break
        title = db.title(book_id, index_is_id=True)
        try:
            identifiers = db.get_identifiers(book_id, index_is_id=True)
            amazon_domain, amazon_id = get_amazon_domain_and_asin(identifiers)
            goodreads_id = identifiers.get('goodreads', '')
            if not amazon_id and not goodreads_id:
                log.error('No Amazon id or Goodreads id for this book. Download metadata first to get identifiers!', book_id)
                failed_ids.append((book_id, title, _('No Amazon or Goodreads id for this book')))
            else:
                log('----------------------------')
                log('Processing %s (Id: %d, Amazon: %s Goodreads: %s)'%(title, book_id, amazon_id, goodreads_id))
                workers = []
                amazon_worker = goodreads_worker = None
                if include_amazon and amazon_id:
                    log.info('Will search Amazon %s using id: %s'% (amazon_domain, amazon_id))
                    amazon_worker = AmazonRatingWorker(amazon_id, amazon_domain, log)
                    workers.append(amazon_worker)
                if include_goodreads and goodreads_id:
                    log.info('Will search Goodreads using id: %s'% goodreads_id)
                    goodreads_worker = GoodreadsRatingWorker(goodreads_id, log)
                    workers.append(goodreads_worker)

                for w in workers:
                    w.start()
                    # Don't send all requests at the same time
                    time.sleep(0.1)

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

                arating = arating_count = grating = grating_count = None
                if amazon_worker and amazon_worker.rating and amazon_worker.rating_count:
                    log('   Got Amazon rating: %.1f rating count: %d'%(amazon_worker.rating, amazon_worker.rating_count))
                    arating = amazon_worker.rating
                    arating_count = amazon_worker.rating_count
                if goodreads_worker and goodreads_worker.rating and goodreads_worker.rating_count:
                    log('   Got Goodreads rating: %.2f rating count: %d'%(goodreads_worker.rating, goodreads_worker.rating_count))
                    grating = goodreads_worker.rating
                    grating_count = goodreads_worker.rating_count
                if arating or grating:
                    updated_ids.append((book_id, arating, arating_count, grating, grating_count))
                else:
                    log.error('No rating found for book %s (Id: %d, Amazon: %s Goodreads: %s'%(title, book_id, amazon_id, goodreads_id))
                    failed_ids.append((book_id, title, _('No rating found for book')))
        except:
            log.error(traceback.format_exc())
            failed_ids.append((book_id, title, _('Exception occurred')))
        count += 1
        notifications.put((count/len(ids),
            _('Processed %d of %d')%(count, len(ids))))
    log('Download complete, with %d failures'%len(failed_ids))
    return (updated_ids, failed_ids)
