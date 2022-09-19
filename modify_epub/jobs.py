from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

from calibre.utils.ipc.server import Server
from calibre.utils.ipc.job import ParallelJob
from calibre.utils.logging import Log

from calibre_plugins.modify_epub.modify import modify_epub


def do_modify_epubs(books_to_modify, options, cpus, notification=lambda x,y:x):
    '''
    Master job, to launch child jobs to modify each ePub
    '''
    server = Server(pool_size=cpus)

    # Queue all the jobs
    for book_id, title, authors, epub_file, opf_file, cover_file in books_to_modify:
        args = ['calibre_plugins.modify_epub.jobs', 'do_modify_epub',
                (title, epub_file, opf_file, cover_file, options)]
        job = ParallelJob('arbitrary', str(book_id), done=None, args=args)
        job._book_id = book_id
        job._title = title
        job._authors = authors
        server.add_job(job)

    # This server is an arbitrary_n job, so there is a notifier available.
    # Set the % complete to a small number to avoid the 'unavailable' indicator
    notification(0.01, 'Modifying ePubs')

    # dequeue the job results as they arrive, saving the results
    total = len(books_to_modify)
    count = 0
    modified_epubs_map = dict()
    while True:
        job = server.changed_jobs_queue.get()
        # A job can 'change' when it is not finished, for example if it
        # produces a notification. Ignore these.
        job.update()
        if not job.is_finished:
            continue
        # A job really finished. Get the information.
        modified_epub_path = job.result
        book_id = job._book_id
        if modified_epub_path:
            modified_epubs_map[book_id] = modified_epub_path
        count += 1
        notification(float(count)/total, 'Modifying ePubs')
        # Add this job's output to the current log
        print(('Logfile for book ID %d (%s / %s)'%(book_id, job._title, job._authors)))
        print('Job details', (job.details))
        if count >= total:
            # All done!
            break

    server.close()
    # return the map as the job result
    return modified_epubs_map


def do_modify_epub(title, epub_file, opf_file, cover_file, options):
    '''
    Child job, to modify this specific book
    '''
    return modify_epub(Log(), title, epub_file, opf_file, cover_file, options)

