from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

import time
from calibre import prints
from calibre.constants import DEBUG

BASE_TIME = None
def debug_print(*args):
    '''
    For debugging plugins, displays timestamped log info when calibre run in debug mode.
    '''
    global BASE_TIME
    if BASE_TIME is None:
        BASE_TIME = time.time()
    if DEBUG:
        prints('DEBUG: %6.1f'%(time.time()-BASE_TIME), *args)
