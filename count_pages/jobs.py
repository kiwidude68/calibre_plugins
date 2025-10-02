from __future__ import unicode_literals, division, absolute_import, print_function

__license__ = 'GPL v3'
__copyright__ = '2011, Grant Drake'

import os, traceback, time

from calibre.customize.ui import quick_metadata
from calibre.ebooks import DRMError
from calibre.ptempfile import cleanup
from calibre.utils.ipc.server import Server
from calibre.utils.ipc.job import ParallelJob

import calibre_plugins.count_pages.config as cfg
from calibre_plugins.count_pages.download import DownloadPagesWorker
from calibre_plugins.count_pages.statistics import (get_page_count, get_pdf_page_count,
                                    get_word_count, get_text_analysis, get_gunning_fog_index,
                                    get_flesch_reading_ease, get_flesch_kincaid_grade_level,
                                    get_cbr_page_count, get_cbz_page_count)


def call_plugin_callback(plugin_callback, parent, plugin_results=None):
    '''
    This function executes a callback to a calling plugin. Because this 
    can be called after a job has been run, the plugin and callback function 
    are passed as strings.
    
    The parameters are:

      plugin_callback - This is a dictionary definging the callbak function.
          The elements are:
              plugin_name - name of the plugin to be called
              func_name - name of the function to be called
              args - Arguments to be passed to the callback function. Will be
                  passed as "*args" so must be a collection if it is supplied.
              kwargs - Keyword arguments to be passedd to the callback function.
                  Will be passed as "**kargs" so must be a dictionary if it 
                  is supplied.

      parent - parent gui needed to find the plugin.

      plugin_results - Results to be passed to the plugin.
      
    If the kwargs dictionary contains an entry for "plugin_results", the value
    will be replaced by the parameter "plugin_results". This allows the results
    of the called plugin to be passed to the callback. 
    '''
    print("call_plugin_callback: have callback:", plugin_callback)
    from calibre.customize.ui import find_plugin
    plugin = find_plugin (plugin_callback['plugin_name'])
    if plugin is not None:
        print("call_plugin_callback: have plugin for callback:", plugin)
        callback_func = getattr(plugin.load_actual_plugin(parent), plugin_callback['func_name'])
        args = plugin_callback['args'] if 'args'  in plugin_callback else []
        kwargs = plugin_callback['kwargs'] if 'kwargs' in plugin_callback else {}
        if 'plugin_results' in kwargs and plugin_results:
            kwargs['plugin_results'] = plugin_results
        print("call_plugin_callback: about to call callback - kwargs=", kwargs)
        callback_func(*args, **kwargs)

def do_count_statistics(books_to_scan, pages_algorithm,
                        nltk_pickle, custom_chars_per_page, icu_wordcount,
                        page_count_mode, download_sources, cpus, notification=lambda x, y:x):
    '''
    Master job, to launch child jobs to count pages in this list of books
    '''
    server = Server(pool_size=cpus)

    # Queue all the jobs
    for book_id, title, book_path, download_sources, statistics_to_run in books_to_scan:
        args = ['calibre_plugins.count_pages.jobs', 'do_statistics_for_book',
                (book_path, pages_algorithm, page_count_mode, download_sources, 
                 statistics_to_run, nltk_pickle, custom_chars_per_page, icu_wordcount)]
#         print("do_count_statistics - args=", args)
        print("do_count_statistics - book_path=%s, pages_algorithm=%s, page_count_mode=%s, statistics_to_run=%s, custom_chars_per_page=%s, icu_wordcount=%s"
              % (book_path, pages_algorithm, page_count_mode, 
                 statistics_to_run, custom_chars_per_page, icu_wordcount))
        job = ParallelJob('arbitrary', str(book_id), done=None, args=args)
        job._book_id = book_id
        job._title = title
        job._pages_algorithm = pages_algorithm
        job._download_sources = download_sources
        job._page_count_mode = page_count_mode
        job._statistics_to_run = statistics_to_run
        server.add_job(job)
        print("do_count_statistics - job started for file book_path=%s" % book_path)

    # This server is an arbitrary_n job, so there is a notifier available.
    # Set the % complete to a small number to avoid the 'unavailable' indicator
    notification(0.01, 'Counting Statistics')

    # dequeue the job results as they arrive, saving the results
    total = len(books_to_scan)
    count = 0
    book_stats_map = dict()
    while True:
        job = server.changed_jobs_queue.get()
        # A job can 'change' when it is not finished, for example if it
        # produces a notification. Ignore these.
        job.update()
        if not job.is_finished:
            continue
        # A job really finished. Get the information.
        results = job.result
        book_id = job._book_id
        book_stats_map[book_id] = results
        count = count + 1
        notification(float(count) / total, 'Counting Statistics')

        # Add this job's output to the current log
        print('-------------------------------')
        print('Logfile for book ID %d (%s)' % (book_id, job._title))

        for stat in job._statistics_to_run:
            if stat == cfg.STATISTIC_PAGE_COUNT:
                print('\tMethod of counting _page_count_mode=%s _download_sources=%s' % (job._page_count_mode, job._download_sources))
                print('\tresults=' ,results)
                if job._page_count_mode == 'Download':
                    if job._download_sources is not None:
                        if stat in results and results[stat]:
                            print('\tDownloaded page count from %s: %d' % (cfg.PAGE_DOWNLOADS[results['download_source']]['name'], results[stat]))
                            del book_stats_map[book_id]['download_source']
                        else:
                            print('\tFAILED TO GET PAGE COUNT FROM WEBSITE')
                else:
                    if stat in results and results[stat]:
                        print('\tFound %d pages' % results[stat])
            elif stat == cfg.STATISTIC_WORD_COUNT:
                if stat in results and results[stat]:
                    print('\tFound %d words' % results[stat])
            elif stat == cfg.STATISTIC_FLESCH_READING:
                if stat in results and results[stat]:
                    print('\tComputed %.1f Flesch Reading' % results[stat])
            elif stat == cfg.STATISTIC_FLESCH_GRADE:
                if stat in results and results[stat]:
                    print('\tComputed %.1f Flesch-Kincaid Grade' % results[stat])
            elif stat == cfg.STATISTIC_GUNNING_FOG:
                if stat in results and results[stat]:
                    print('\tComputed %.1f Gunning Fog Index' % results[stat])

        print(job.details)

        if count >= total:
            # All done!
            break

    server.close()
    # return the map as the job result
    return book_stats_map


def do_statistics_for_book(book_path, pages_algorithm, page_count_mode, 
                           download_sources, statistics_to_run,
                           nltk_pickle, custom_chars_per_page, icu_wordcount):
    '''
    Child job, to count statistics in this specific book
    '''
    results = {}
    try:
        iterator = None
        print("do_statistics_for_book: ", book_path, pages_algorithm, page_count_mode, 
                           download_sources, statistics_to_run,
                           custom_chars_per_page, icu_wordcount)

        with quick_metadata:
            try:
                extension = ''
                is_comic = False
                if book_path:
                    extension = os.path.splitext(book_path)[1].lower()
                    is_comic = extension in ['.cbr', '.cbz']
                stats = list(statistics_to_run)
                if cfg.STATISTIC_PAGE_COUNT in stats:
                    pages = None
                    stats.remove(cfg.STATISTIC_PAGE_COUNT)
                    if page_count_mode == 'Download':
                        if download_sources:
                            goodreads_worker = DownloadPagesWorker(download_sources)
                            pages = goodreads_worker.page_count
                            if pages:
                                results['download_source'] = goodreads_worker.source_name
                    else:
                        if extension == '.pdf':
                            # As an optimisation for PDFs we will read the page count directly
                            pages = get_pdf_page_count(book_path)
                        elif extension == '.cbr':
                            pages = get_cbr_page_count(book_path)
                        elif extension == '.cbz':
                            pages = get_cbz_page_count(book_path)
                        else:
                            iterator, pages = get_page_count(iterator, book_path, pages_algorithm, custom_chars_per_page)
                    results[cfg.STATISTIC_PAGE_COUNT] = pages

                if is_comic:
                    if not (len(stats) == 1 and cfg.STATISTIC_PAGE_COUNT in stats):
                        print('Skipping non page count statistics for CBR/CBZ')
                elif book_path:
                    if cfg.STATISTIC_WORD_COUNT in stats:
                        stats.remove(cfg.STATISTIC_WORD_COUNT)
                        iterator, words = get_word_count(iterator, book_path, icu_wordcount)
                        if words == 0:
                            # Something dodgy about the conversion - no point in calculating remaining stats
                            print('ERROR: No words found in this book (conversion error?), word count will not be stored')
                            return results
                        results[cfg.STATISTIC_WORD_COUNT] = words

                    if stats:
                        # The remaining stats are all reading level based
                        # As an optimisation, we will run the text analysis once and
                        # then add the relevant results
                        iterator, text_analysis = get_text_analysis(iterator, book_path, nltk_pickle)
                        if text_analysis['wordCount'] == 0:
                            # Something dodgy about the conversion - no point in calculating remaining stats
                            print('ERROR: No words found in this book (conversion error?) - readability statistics will not be calculated')
                            return results
                        from calibre.utils.localization import get_lang
                        lang = iterator.opf.language
                        lang = get_lang() if not lang else lang
                        print('For this book, using language=%s' % lang)
                        if cfg.STATISTIC_FLESCH_READING in statistics_to_run:
                            results[cfg.STATISTIC_FLESCH_READING] = get_flesch_reading_ease(text_analysis, lang)
                        if cfg.STATISTIC_FLESCH_GRADE in statistics_to_run:
                            results[cfg.STATISTIC_FLESCH_GRADE] = get_flesch_kincaid_grade_level(text_analysis)
                        if cfg.STATISTIC_GUNNING_FOG in statistics_to_run:
                            results[cfg.STATISTIC_GUNNING_FOG] = get_gunning_fog_index(text_analysis)
            finally:
                if iterator:
                    iterator.__exit__()
                    iterator = None
                if book_path is not None:
                    if os.path.exists(book_path):
                        time.sleep(0.1)
                        cleanup(book_path)
        return results
    except DRMError:
        print('\tCannot read pages due to DRM Encryption')
        return results
    except:
        traceback.print_exc()
        return results

