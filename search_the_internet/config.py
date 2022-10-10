from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

import os, shutil

# calibre Python 3 compatibility.
from six import text_type as unicode
try:
    from urllib.request import urlretrieve
except ImportError:
    from urllib import urlretrieve

from functools import partial

# Maintain backwards compatibility with older versions of Qt and calibre.
try:
    from qt.core import (Qt, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                          QIcon, QFormLayout, QAction, QFileDialog, QDialog, QTableWidget,
                          QTableWidgetItem, QAbstractItemView, QComboBox, QUrl,
                          QGroupBox, QGridLayout, QRadioButton, QDialogButtonBox,
                          QPushButton, QToolButton, QSpacerItem, QModelIndex)
except:
    from PyQt5.Qt import (Qt, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                          QIcon, QFormLayout, QAction, QFileDialog, QDialog, QTableWidget,
                          QTableWidgetItem, QAbstractItemView, QComboBox, QUrl,
                          QGroupBox, QGridLayout, QRadioButton, QDialogButtonBox,
                          QPushButton, QToolButton, QSpacerItem, QModelIndex)

from calibre.ebooks.metadata.book.base import Metadata
from calibre.gui2 import (error_dialog, question_dialog, info_dialog, choose_files,
                          open_local_file, FileDialog, open_url)
from calibre.gui2.actions import menu_action_unique_name
from calibre.utils.config import JSONConfig
from calibre.utils.zipfile import ZipFile

from calibre_plugins.search_the_internet.common_compatibility import qSizePolicy_Minimum, qSizePolicy_Expanding
from calibre_plugins.search_the_internet.common_dialogs import KeyboardConfigDialog
from calibre_plugins.search_the_internet.common_icons import get_icon, get_local_images_dir
from calibre_plugins.search_the_internet.common_widgets import (NoWheelComboBox, CheckableTableWidgetItem, 
                                                                TextIconWidgetItem)

try:
    load_translations()
except NameError:
    pass # load_translations() 

HELP_URL = 'https://github.com/kiwidude68/calibre_plugins/wiki/Search-The-Internet'

PLUGIN_ICONS = ['internet.png', 'open_group.png',
                'move_to_top.png', 'image_add.png',
                'import.png', 'export.png']

COL_NAMES = ['active', 'menuText', 'subMenu', 'openGroup', 'image', 'url', 'encoding', 'method']
DEFAULT_MENU_SET = [
        (False, 'Audible for Author',             '', False, 'stip_audible.png',   'http://www.audible.com/search?advsearchKeywords=&searchTitle=&searchAuthor={author}&field_language=English','utf-8', 'GET'),
        (False, 'Audible for Book',               '', False, 'stip_audible.png',   'http://www.audible.com/search?advsearchKeywords=&searchTitle={title}&searchAuthor={author}&field_language=English','utf-8', 'GET'),
        (False, '', '', False, '', '', '', 'GET'),
        (True,  'Amazon.com for Book',            '', False, 'stip_amazon.png',    'http://www.amazon.com/s/ref=nb_sb_noss?url=search-alias%3Dstripbooks&field-keywords={author}+{title}', 'latin-1', 'GET'),
        (False, 'Amazon.co.uk for Book',          '', False, 'stip_amazon.png',    'http://www.amazon.co.uk/s/ref=nb_sb_noss?url=search-alias%3Dstripbooks&field-keywords={author}+{title}', 'latin-1', 'GET'),
        (False, '', '', False, '', '', '', 'GET'),
        (False, 'Barnes and Noble for Author',    '', False, 'stip_bn.png',        'http://productsearch.barnesandnoble.com/search/results.aspx?store=book&ATH={author}', 'utf-8', 'GET'),
        (False, 'Barnes and Noble for Book',      '', False, 'stip_bn.png',        'http://productsearch.barnesandnoble.com/search/results.aspx?store=book&ATH={author}&TTL={title}', 'utf-8', 'GET'),
        (False, 'Barnes and Noble for ISBN',      '', False, 'stip_bn.png',        'http://search.barnesandnoble.com/books/product.aspx?EAN={isbn}', 'utf-8', 'GET'),
        (False, 'Barnes and Noble for Title',     '', False, 'stip_bn.png',        'http://productsearch.barnesandnoble.com/search/results.aspx?store=book&TTL={title}', 'utf-8', 'GET'),
        (False, '', '', False, '', '', '', 'GET'),
        (False, 'Books-by-ISBN for ISBN',         '', False, 'stip_isbn.png',      'http://books-by-isbn.com/cgi-bin/isbn-lookup.pl?isbn={isbn}', 'utf-8', 'GET'),
        (False, '', '', False, '', '', '', 'GET'),
        (False, 'Classify for Author',            '', False, 'stip_classify.png',  'http://classify.oclc.org/classify2/ClassifyDemo?search-author-txt={author}', 'utf-8', 'GET'),
        (False, 'Classify for Book',              '', False, 'stip_classify.png',  'http://classify.oclc.org/classify2/ClassifyDemo?search-title-txt={title}&search-author-txt={author}', 'utf-8', 'GET'),
        (False, 'Classify for ISBN',              '', False, 'stip_classify.png',  'http://classify.oclc.org/classify2/ClassifyDemo?search-standnum-txt={isbn}', 'utf-8', 'GET'),
        (False, '', '', False, '', '', '', 'GET'),
        (False, 'Demonoid for Author',            '', False, 'stip_demonoid.png',  'http://www.demonoid.me/files/?category=11&subcategory=All&quality=All&seeded=0&external=2&query={author}', 'utf-8', 'GET'),
        (False, 'Demonoid for Book',              '', False, 'stip_demonoid.png',  'http://www.demonoid.me/files/?category=11&subcategory=All&quality=All&seeded=0&external=2&query={author}+{title}', 'utf-8', 'GET'),
        (False, '', '', False, '', '', '', 'GET'),
        (False, 'EBay US',                        '', False, 'stip_ebay.png',      'https://www.ebay.com/sch/i.html?_nkw={author}+{title}&_sacat=267', 'utf-8', 'GET'),
        (False, 'EBay UK',                        '', False, 'stip_ebay.png',      'https://www.ebay.co.uk/sch/i.html?_nkw={author}+{title}&_sacat=267', 'utf-8', 'GET'),
        (False, '', '', False, '', '', '', 'GET'),
        (False, 'EBooks for Author',              '', False, 'stip_ebooks.png',    'http://www.ebooks.com/SearchApp/SearchResults.net?term={author}&RestrictBy=author', 'utf-8', 'GET'),
        (False, 'EBooks for Book',                '', False, 'stip_ebooks.png',    'http://www.ebooks.com/SearchApp/SearchResults.net?term={author}+{title}', 'utf-8', 'GET'),
        (False, '', '', False, '', '', '', 'GET'),
        (False, 'Ellora\'s Cave for Title',       '', False, 'stip_ellora.png',    'http://www.jasminejade.com/searchadv.aspx?IsSubmit=true&SearchTerm={title}&ProductTypeID=5&ShowPics=1', 'utf-8', 'GET'),
        (True,  '', '', False, '', '', '', 'GET'),
        (True,  'FantasticFiction for Author',    '', False, 'stip_ff.png',        'http://www.fantasticfiction.co.uk/search/?searchfor=author&keywords={author}', 'utf-8', 'GET'),
        (True,  'FantasticFiction for Title',     '', False, 'stip_ff.png',        'http://www.fantasticfiction.co.uk/search/?searchfor=book&keywords={title}', 'utf-8', 'GET'),
        (False, '', '', False, '', '', '', 'GET'),
        (False, 'FictFact for Author',            '', False, 'stip_fictfact.png',  'http://www.fictfact.com/search/?q={author}', 'utf-8', 'GET'),
        (False, 'FictFact for Book',              '', False, 'stip_fictfact.png',  'http://www.fictfact.com/search/?q={author}+{title}', 'utf-8', 'GET'),
        (False, '', '', False, '', '', '', 'GET'),
        (False, 'FictionDB for Author',           '', False, 'stip_fictiondb.png', 'http://www.fictiondb.com/search/searchresults.htm?styp=1&srchtxt={author}', 'utf-8', 'POST'),
        (False, 'FictionDB for Book',             '', False, 'stip_fictiondb.png', 'http://www.fictiondb.com/search/searchresults.htm?styp=6&author={author}&title={title}&srchtxt=multi&sgcode=0&tpcode=0&imprint=0&pubgroup=0&genretype=--&rating=-&myrating=-&status=-', 'utf-8', 'POST'),
        (False, 'FictionDB for ISBN',             '', False, 'stip_fictiondb.png', 'http://www.fictiondb.com/search/searchresults.htm?styp=4&srchtxt={isbn}', 'utf-8', 'POST'),
        (False, 'FictionDB for Title',            '', False, 'stip_fictiondb.png', 'http://www.fictiondb.com/search/searchresults.htm?styp=2&srchtxt={title}', 'utf-8', 'POST'),
        (False, '', '', False, '', '', '', 'GET'),
        (False, 'Goodreads for Author',           '', False, 'stip_goodreads.png', 'http://www.goodreads.com/search/search?q={author}&search_type=books', 'utf-8', 'GET'),
        (False, 'Goodreads for Book',             '', False, 'stip_goodreads.png', 'http://www.goodreads.com/search/search?q={author}+{title}&search_type=books', 'utf-8', 'GET'),
        (False, 'Goodreads for ISBN',             '', False, 'stip_goodreads.png', 'http://www.goodreads.com/search/search?q={isbn}&search_type=books', 'utf-8', 'GET'),
        (False, 'Goodreads for Title',            '', False, 'stip_goodreads.png', 'http://www.goodreads.com/search/search?q={title}&search_type=books', 'utf-8', 'GET'),
        (True,  '', '', False, '', '', '', 'GET'),
        (True,  'Google images for Book',         '', False, 'stip_google.png',    'http://www.google.com/images?q=%22{author}%22+%22{title}%22', 'utf-8', 'GET'),
        (True,  'Google images 400x300',          '', False, 'stip_google.png',    'http://www.google.com/images?as_q={author}+%22{title}%22&tbs=isch:1,isz:lt,islt:qsvga,imgo:1&safe=off', 'utf-8', 'GET'),
        (True,  'Google.com for Book',            '', False, 'stip_google.png',    'http://www.google.com/#sclient=psy&q=%22{author}%22+%22{title}%22', 'utf-8', 'GET'),
        (False, '', '', False, '', '', '', 'GET'),
        (False, 'isfdb for Author',               '', False, 'stip_isfdb.png',     'http://www.isfdb.org/cgi-bin/se.cgi?type=Name&arg={author}', 'latin-1', 'GET'),
        (False, 'isfdb for Book',                 '', False, 'stip_isfdb.png',     'http://www.isfdb.org/cgi-bin/edit/tp_search.cgi?TERM_1={title}&USE_1=title&OPERATOR_1=AND&TERM_2={author}&USE_2=author&OPERATOR_2=AND' , 'latin-1', 'GET'),
        (False, 'isfdb for ISBN',                 '', False, 'stip_isfdb.png',     'http://www.isfdb.org/cgi-bin/se.cgi?type=ISBN&arg={isbn}', 'latin-1', 'GET'),
        (False, 'isfdb for Title',                '', False, 'stip_isfdb.png',     'http://www.isfdb.org/cgi-bin/se.cgi?type=Fiction+Titles&arg={title}', 'latin-1', 'GET'),
        (False, '', '', False, '', '', '', 'GET'),
        (False, 'Inkmesh for Author',             '', False, 'stip_inkmesh.png',   'http://www.inkmesh.com/search/?qs={author}&btnE=Find+Ebooks','utf-8', 'GET'),
        (False, 'Inkmesh for Book',               '', False, 'stip_inkmesh.png',   'http://www.inkmesh.com/search/?qs={title}+by+{author}&btnE=Find+Ebooks','utf-8', 'GET'),
        (False, 'Inkmesh for Title',              '', False, 'stip_inkmesh.png',   'http://www.inkmesh.com/search/?qs={title}&btnE=Find+Ebooks','utf-8', 'GET'),
        (False, '', '', False, '', '', '', 'GET'),
        (False, 'Kobo for Author',                '', False, 'stip_kobo.png',      'http://www.kobobooks.com/search/search.html?q={author}&f=author','utf-8', 'GET'),
        (False, 'Kobo for Book',                  '', False, 'stip_kobo.png',      'http://www.kobobooks.com/search/search.html?q={author}+{title}&f=author','utf-8', 'GET'),
        (False, 'Kobo for Title',                 '', False, 'stip_kobo.png',      'http://www.kobobooks.com/search/search.html?q={title}','utf-8', 'GET'),
        (False, '', '', False, '', '', '', 'GET'),
        (False, 'Library of Congress for Author', '', False, 'stip_loc.png',       'http://catalog.loc.gov/cgi-bin/Pwebrecon.cgi?DB=local&Search_Arg={author}&Search_Code=NAME%40&CNT=100&hist=1&type=quick', 'utf-8', 'GET'),
        (False, 'Library of Congress for ISBN',   '', False, 'stip_loc.png',       'http://catalog.loc.gov/cgi-bin/Pwebrecon.cgi?DB=local&Search_Arg={isbn}&Search_Code=STNO^*&CNT=100&hist=1&type=quick', 'utf-8', 'GET'),
        (False, 'Library of Congress for Title',  '', False, 'stip_loc.png',       'http://catalog.loc.gov/cgi-bin/Pwebrecon.cgi?DB=local&Search_Arg={title}&Search_Code=TKEY^*&CNT=100&hist=1&type=quick', 'utf-8', 'GET'),
        (False, '', '', False, '', '', '', 'GET'),
        (False, 'LibraryThing for Author',        '', False, 'stip_lthing.png',    'http://www.librarything.com/search.php?search={author}', 'utf-8', 'GET'),
        (False, 'LibraryThing for Book',          '', False, 'stip_lthing.png',    'http://www.librarything.com/search.php?search={title}+{author}', 'utf-8', 'GET'),
        (False, 'LibraryThing for ISBN',          '', False, 'stip_lthing.png',    'http://www.librarything.com/search.php?search={isbn}', 'utf-8', 'GET'),
        (False, 'LibraryThing for Title',         '', False, 'stip_lthing.png',    'http://www.librarything.com/search.php?search={title}', 'utf-8', 'GET'),
        (False, '', '', False, '', '', '', 'GET'),
        (False, 'Literature-Map like Author',     '', False, 'stip_litmap.png',    'http://www.literature-map.com/{author}.html', 'utf-8', 'GET'),
        (False, '', '', False, '', '', '', 'GET'),
        (False, 'Lovereading like Author',        '', False, 'stip_loveread.png',  'http://www.lovereading.co.uk/authorrec/{author:re(\\+, )}', 'utf-8', 'GET'),
        (False, 'Lovereading for Author',         '', False, 'stip_loveread.png',  'http://www.lovereading.co.uk/search.php?author={author}&format=All+Formats&advsearch=1', 'utf-8', 'GET'),
        (False, 'Lovereading for Book',           '', False, 'stip_loveread.png',  'http://www.lovereading.co.uk/search.php?author={author}&title={title}&format=All+Formats&advsearch=1', 'utf-8', 'GET'),
        (False, 'Lovereading for ISBN',           '', False, 'stip_loveread.png',  'http://www.lovereading.co.uk/search.php?isbn={isbn}&format=All+Formats&advsearch=1', 'utf-8', 'GET'),
        (False, 'Lovereading for Title',          '', False, 'stip_loveread.png',  'http://www.lovereading.co.uk/search.php?title={title}&format=All+Formats&advsearch=1', 'utf-8', 'GET'),
        (False, '', '', False, '', '', '', 'GET'),
        (False, 'ManyBooks for Author',           '', False, 'stip_manybooks.png', 'http://manybooks.net/search.php?search={author}', 'utf-8', 'GET'),
        (False, 'ManyBooks for Title',            '', False, 'stip_manybooks.png', 'http://manybooks.net/search.php?search={title}', 'utf-8', 'GET'),
        (False, '', '', False, '', '', '', 'GET'),
        (False, 'Mobipocket for Author',          '', False, 'stip_mobi.png',      'http://www.mobipocket.com/en/eBooks/searchebooks.asp?Language=EN&searchType=Author&lang=EN&searchStr={author}', 'utf-8', 'GET'),
        (False, 'Mobipocket for Book',            '', False, 'stip_mobi.png',      'http://www.mobipocket.com/en/eBooks/searchebooks.asp?Language=EN&searchType=All&lang=EN&searchStr={title}+{author}', 'utf-8', 'GET'),
        (False, 'Mobipocket for ISBN',            '', False, 'stip_mobi.png',      'http://www.mobipocket.com/en/eBooks/searchebooks.asp?Language=EN&searchType=Publisher&lang=EN&searchStr={isbn}', 'utf-8', 'GET'),
        (False, 'Mobipocket for Title',           '', False, 'stip_mobi.png',      'http://www.mobipocket.com/en/eBooks/searchebooks.asp?Language=EN&searchType=Title&lang=EN&searchStr={tittle}', 'utf-8', 'GET'),
        (False, '', '', False, '', '', '', 'GET'),
        (False, 'NYTimes for Author',             '', False, 'stip_nyt.png',       'http://query.nytimes.com/search/sitesearch?query={author}&more=date_all',' utf-8'),
        (False, 'NYTimes for Book',               '', False, 'stip_nyt.png',       'http://query.nytimes.com/search/sitesearch?query={author}+{title}&more=date_all',' utf-8'),
        (False, 'NYTimes for Title',              '', False, 'stip_nyt.png',       'http://query.nytimes.com/search/sitesearch?query={title}&more=date_all',' utf-8'),
        (False, '', '', False, '', '', '', 'GET'),
        (False, 'SimilarAuthors like Author',     '', False, 'stip_simauth.png',   'http://www.similarauthors.com/search.php?author={author}', 'utf-8', 'GET'),
        (False, '', '', False, '', '', '', 'GET'),
        (False, 'Sony for Author',                '', False, 'stip_sony.png',      'http://ebookstore.sony.com/search?keyword={author}', 'utf-8', 'GET'),
        (False, 'Sony for Book',                  '', False, 'stip_sony.png',      'http://ebookstore.sony.com/search?keyword={author}+{title}', 'utf-8', 'GET'),
        (False, 'Sony for ISBN',                  '', False, 'stip_sony.png',      'http://ebookstore.sony.com/search?keyword={isbn}', 'utf-8', 'GET'),
        (False, 'Sony for Title',                 '', False, 'stip_sony.png',      'http://ebookstore.sony.com/search?keyword={title}', 'utf-8', 'GET'),
        (False, '', '', False, '', '', '', 'GET'),
        (False, 'Waterstones for Author',         '', False, 'stip_wstones.png',   'http://www.waterstones.com/waterstonesweb/advancedSearch.do?buttonClicked=1&title=&author={author}', 'utf-8', 'GET'),
        (False, 'Waterstones for Book',           '', False, 'stip_wstones.png',   'http://www.waterstones.com/waterstonesweb/advancedSearch.do?buttonClicked=1&title={title}&author={author}', 'utf-8', 'GET'),
        (False, 'Waterstones for ISBN',           '', False, 'stip_wstones.png',   'http://www.waterstones.com/waterstonesweb/advancedSearch.do?buttonClicked=2&isbn={isbn}', 'utf-8', 'GET'),
        (False, 'Waterstones for Title',          '', False, 'stip_wstones.png',   'http://www.waterstones.com/waterstonesweb/advancedSearch.do?buttonClicked=1&title={title}', 'utf-8', 'GET'),
        (False, '', '', False, '', '', '', 'GET'),
        (False, 'WhatShouldIReadNext for ISBN',   '', False, 'stip_wsirn.png',     'http://www.whatshouldireadnext.com/wsirn.php?isbn={isbn}', 'utf-8', 'GET'),
        (True,  '', '', False,  '', '', ''),
        (True,  'Wikipedia for Author',           '', False, 'stip_wikipedia.png', 'http://en.wikipedia.org/w/index.php?title=Special%3ASearch&search={author}', 'utf-8', 'GET'),
        (False, 'Wikipedia for Book',             '', False, 'stip_wikipedia.png', 'http://en.wikipedia.org/w/index.php?title=Special%3ASearch&search={author}+{title}', 'utf-8', 'GET'),
        (False, 'Wikipedia for Title',            '', False, 'stip_wikipedia.png', 'http://en.wikipedia.org/w/index.php?title=Special%3ASearch&search={title}', 'utf-8', 'GET'),
        (False, '', '', False, '', '', '', 'GET'),
        (False, 'Amazon.ca for Book',             '', False, 'stip_amazon.png',    'http://www.amazon.ca/s/ref=nb_sb_noss?url=search-alias%3Dstripbooks&field-keywords={author}+{title}', 'latin-1', 'GET'),
        (False, 'Amazon.cn for Book',             '', False, 'stip_amazon.png',    'http://www.amazon.cn/s/ref=nb_sb_noss?url=search-alias%3Dstripbooks&field-keywords={author}+{title}', 'latin-1', 'GET'),
        (False, 'Amazon.co.jp for Book',          '', False, 'stip_amazon.png',    'http://www.amazon.co.jp/s/ref=nb_sb_noss?url=search-alias%3Dstripbooks&field-keywords={author}+{title}', 'latin-1', 'GET'),
        (False, 'Amazon.de for Book',             '', False, 'stip_amazon.png',    'http://www.amazon.de/s/ref=nb_sb_noss?url=search-alias%3Dstripbooks&field-keywords={author}+{title}', 'latin-1', 'GET'),
        (False, 'Amazon.it for Book',             '', False, 'stip_amazon.png',    'http://www.amazon.it/s/ref=nb_sb_noss?url=search-alias%3Dstripbooks&field-keywords={author}+{title}', 'latin-1', 'GET'),
        (False, 'Amazon.fr for Book',             '', False, 'stip_amazon.png',    'http://www.amazon.fr/s/ref=nb_sb_noss?url=search-alias%3Dstripbooks&field-keywords={author}+{title}', 'latin-1', 'GET'),
        (False, 'bol.de for Author',              '', False, 'stip_bol.png',       'http://www.bol.de/shop/buecher/suche/?sa={author}&forward=weiter&sswg=BUCH', 'latin-1', 'GET'),
        (False, 'bol.de for Book',                '', False, 'stip_bol.png',       'http://www.bol.de/shop/buecher/suche/?st={title}&sa={author}&forward=weiter&sswg=BUCH', 'latin-1', 'GET'),
        (False, 'bol.de for Title',               '', False, 'stip_bol.png',       'http://www.bol.de/shop/buecher/suche/?st={title}&forward=weiter&sswg=BUCH', 'latin-1', 'GET'),
        (False, 'Chapitre for Title',             '', False, 'stip_chapitre.png',  'http://www.chapitre.com/CHAPITRE/fr/search/Default.aspx?optSearch=BOOKS&titre={title}', 'utf-8', 'GET'),
        (False, 'Chapters.ca for Author',         '', False, 'stip_chapters.png',  'http://www.chapters.indigo.ca/home/search/?keywords={author}', 'utf-8', 'GET'),
        (False, 'Chapters.ca for Book',           '', False, 'stip_chapters.png',  'http://www.chapters.indigo.ca/home/search/?keywords={author}+{title}', 'utf-8', 'GET'),
        (False, 'Chapters.ca for ISBN',           '', False, 'stip_chapters.png',  'http://www.chapters.indigo.ca/home/search/?keywords={isbn}', 'utf-8', 'GET'),
        (False, 'Chapters.ca for Title',          '', False, 'stip_chapters.png',  'http://www.chapters.indigo.ca/home/search/?keywords={title}', 'utf-8', 'GET'),
        (False, 'Fnac for Author',                '', False, 'stip_fnac.png',      'http://recherche.fnac.com/Search/SearchResult.aspx?SCat=2&Search={author}', 'utf-8', 'GET'),
        (False, 'Fnac for Book',                  '', False, 'stip_fnac.png',      'http://recherche.fnac.com/Search/SearchResult.aspx?SCat=2&Search={author}+{title}', 'utf-8', 'GET'),
        (False, 'Fnac for Title',                 '', False, 'stip_fnac.png',      'http://recherche.fnac.com/Search/SearchResult.aspx?SCat=2&Search={title}', 'utf-8', 'GET'),
        (False, 'Google.de for Book',             '', False, 'stip_google.png',    'http://www.google.de/#sclient=psy&q=%22{author}%22+%22{title}%22', 'utf-8', 'GET'),
        (False, 'Google.es for Book',             '', False, 'stip_google.png',    'http://www.google.es/#sclient=psy&q=%22{author}%22+%22{title}%22', 'utf-8', 'GET'),
        (False, 'Google.fr for Book',             '', False, 'stip_google.png',    'http://www.google.fr/#sclient=psy&q=%22{author}%22+%22{title}%22', 'utf-8', 'GET'),
        (False, 'Google.it for Book',             '', False, 'stip_google.png',    'http://www.google.it/#sclient=psy&q=%22{author}%22+%22{title}%22', 'utf-8', 'GET'),
        (False, 'libri.de for Author',            '', False, 'stip_libri.png',     'http://www.libri.de/shop/action/advancedSearch?action=search&nodeId=-1&binderType=Alle&languageCode=DE&person={author}', 'utf-8', 'GET'),
        (False, 'libri.de for Book',              '', False, 'stip_libri.png',     'http://www.libri.de/shop/action/advancedSearch?action=search&nodeId=-1&binderType=Alle&languageCode=DE&title={title}&person={author}', 'utf-8', 'GET'),
        (False, 'libri.de for Title',             '', False, 'stip_libri.png',     'http://www.libri.de/shop/action/advancedSearch?action=search&nodeId=-1&binderType=Alle&languageCode=DE&title={title}', 'utf-8', 'GET'),
        (False, 'Wikipedia.de for Author',        '', False, 'stip_wikipedia.png', 'http://de.wikipedia.org/w/index.php?title=Special%3ASearch&search={author}', 'utf-8', 'GET'),
        (False, 'Wikipedia.de for Book',          '', False, 'stip_wikipedia.png', 'http://de.wikipedia.org/w/index.php?title=Special%3ASearch&search={author}+{title}', 'utf-8', 'GET'),
        (False, 'Wikipedia.de for Title',         '', False, 'stip_wikipedia.png', 'http://de.wikipedia.org/w/index.php?title=Special%3ASearch&search={title}', 'utf-8', 'GET'),
        (False, 'Wikipedia.es for Author',        '', False, 'stip_wikipedia.png', 'http://es.wikipedia.org/w/index.php?title=Special%3ASearch&search={author}', 'utf-8', 'GET'),
        (False, 'Wikipedia.es for Book',          '', False, 'stip_wikipedia.png', 'http://es.wikipedia.org/w/index.php?title=Special%3ASearch&search={author}+{title}', 'utf-8', 'GET'),
        (False, 'Wikipedia.es for Title',         '', False, 'stip_wikipedia.png', 'http://es.wikipedia.org/w/index.php?title=Special%3ASearch&search={title}', 'utf-8', 'GET'),
        (False, 'Wikipedia.fr for Author',        '', False, 'stip_wikipedia.png', 'http://fr.wikipedia.org/w/index.php?title=Sp%E9cial%3ARecherche&search={author}', 'utf-8', 'GET'),
        (False, 'Wikipedia.fr for Book',          '', False, 'stip_wikipedia.png', 'http://fr.wikipedia.org/w/index.php?title=Special%3ASearch&search={author}+{title}', 'utf-8', 'GET'),
        (False, 'Wikipedia.fr for Title',         '', False, 'stip_wikipedia.png', 'http://fr.wikipedia.org/w/index.php?title=Sp%E9cial%3ARecherche&search={title}', 'utf-8', 'GET'),
        (False, 'Wikipedia.it for Author',        '', False, 'stip_wikipedia.png', 'http://it.wikipedia.org/w/index.php?title=Special%3ASearch&search={author}', 'utf-8', 'GET'),
        (False, 'Wikipedia.it for Book',          '', False, 'stip_wikipedia.png', 'http://it.wikipedia.org/w/index.php?title=Special%3ASearch&search={author}+{title}', 'utf-8', 'GET'),
        (False, 'Wikipedia.it for Title',         '', False, 'stip_wikipedia.png', 'http://it.wikipedia.org/w/index.php?title=Special%3ASearch&search={title}', 'utf-8', 'GET')]

STORE_MENUS_NAME = 'SearchMenus'
MENUS_KEY = 'Menus'
COL_WIDTH_KEY = 'UrlColWidth'
DEFAULT_MENU_STORE = {
    MENUS_KEY: None,
    COL_WIDTH_KEY: -1
}

STORE_TEST_NAME = 'TestData'
TEST_VALUES_KEY = 'Values'
TEST_LAST_BOOK_KEY = 'LastBookIndex'
DEFAULT_TEST_STORE = {
    TEST_LAST_BOOK_KEY: 0,
    TEST_VALUES_KEY: [{ 'display': 'English Book 1',   'title': 'To Kill a Mockingbird ',          'author': 'Harper Lee',         'publisher': 'Harper Perennial Modern Classics', 'isbn': '9780061120084'},
                      { 'display': 'English Book 2',   'title': 'Hyperion',                        'author': 'Dan Simmons',        'publisher': 'Gollancz',                         'isbn': '9780575081147'},
                      { 'display': 'English Book 3',   'title': 'Les Misérables',                  'author': 'Victor Hugo',        'publisher': 'Barnes & Noble Classics',          'isbn': '9781593080662'},
                      { 'display': 'French Book',      'title': 'De l\'inconvénient d\'être né',   'author': 'E. M. Cioran',       'publisher': 'French & European Pubns',          'isbn': '9780785928089'},
                      { 'display': 'German Book',      'title': 'Schändung',                       'author': 'Jussi Adler-Olsen',  'publisher': 'dtv',                              'isbn': '9783423247870'}]
}

# This is where all preferences for this plugin will be stored
plugin_prefs = JSONConfig('plugins/Search The Internet')

# Set defaults
plugin_prefs.defaults[STORE_MENUS_NAME] = DEFAULT_MENU_STORE
plugin_prefs.defaults[STORE_TEST_NAME] = DEFAULT_TEST_STORE

def get_default_icon_names():
    # Build a distinct set of icon names to pass to load_resources, including our top level icon
    icon_names = PLUGIN_ICONS
    for id, val in enumerate(DEFAULT_MENU_SET):
        icon = val[4]
        if icon is not None and icon not in icon_names:
            icon_names.append(icon)
    return icon_names

def fix_legacy_url(url):
    # Will fix a corrupt version of the LoveReading.co.uk url from v1.4
    if url == 'http://www.lovereading.co.uk/authorrec/{author_spaced)/gd}':
        url = 'http://www.lovereading.co.uk/authorrec/{author:re(\\+, )}'
    # This is a fix added to v1.5 to ensure that any url's that used to use the old
    # approach of xxx_spaced tokens instead uses the template processor function
    url = url.replace('_spaced}', ':re(\\+, )}')
    return url

def show_help():
    open_url(QUrl(HELP_URL))

def get_menus_as_dictionary(config_menus=None):
    # Menu items wil be stored in a config dictionary in the JSON configuration file
    # However if no menus defined (like first time user) we build a default dictionary set.
    if config_menus is None:
        # No menu items are defines so populate with the default set of menu items
        config_menus = [dict(list(zip(COL_NAMES, tup))) for tup in DEFAULT_MENU_SET]
    return config_menus

def get_pathed_icon(icon_name):
    '''
    We prefix our icons for two reasons:
    
    1. If they really are built-in icons from this zip file, then they sit in the zip subfolder 'images'
    2. If they were instead user-added images, they will sit in the folder: resources\images\Search The Internet\
        however the logic in get_pixmap() would not look for them there due to the if statement that says
        anything not prefixed with 'images/' is assumed to be a calibre built-in icon.
    
    Note that this is only a problem for calibre < 6.2.0 get_icon_old)), the new get_icon_6_2_plus() is fine.
    but does no harm to still include the prefix as it tries without images/ first anyway.
    '''
    return 'images/'+icon_name


class TestDataComboBox(QComboBox):

    def __init__(self, parent, data_items):
        QComboBox.__init__(self, parent)
        self.populate_combo(data_items)

    def populate_combo(self, data_items):
        self.clear()
        for i, data in enumerate(data_items):
            self.insertItem(i, data['display'])


class PickTestBookDialog(QDialog):

    def __init__(self, parent=None):
        QDialog.__init__(self, parent)
        self.setWindowTitle(_('Select test data'))
        layout = QVBoxLayout(self)
        self.setLayout(layout)

        c = plugin_prefs[STORE_TEST_NAME]
        selected_idx = c[TEST_LAST_BOOK_KEY]
        self.data_items = c[TEST_VALUES_KEY]

        combo_layout = QHBoxLayout()
        lbl_choose = QLabel(_('&Select test book:'), self)
        lbl_choose.setMinimumSize(100, 0)
        combo_layout.addWidget(lbl_choose, 0, Qt.AlignLeft)
        self._book_combo = TestDataComboBox(self, self.data_items)
        self._book_combo.currentIndexChanged.connect(self.combo_index_changed)
        lbl_choose.setBuddy(self._book_combo)
        self._book_combo.setMinimumSize(200, 0)
        combo_layout.addWidget(self._book_combo, 1, Qt.AlignLeft)
        layout.addLayout(combo_layout)

        group_box = QGroupBox(self)
        f = QFormLayout()
        self._title_edit = QLineEdit('')
        f.addRow(QLabel(_('Title:')), self._title_edit)
        self._author_edit = QLineEdit('')
        f.addRow(QLabel(_('Author:')), self._author_edit)
        self._publisher_edit = QLineEdit('')
        f.addRow(QLabel(_('Publisher:')), self._publisher_edit)
        self._isbn_edit = QLineEdit('')
        f.addRow(QLabel('ISBN:'), self._isbn_edit)
        group_box.setLayout(f)
        layout.addWidget(group_box)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.ok_clicked)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        self.resize(self.sizeHint())
        self._book_combo.setCurrentIndex(selected_idx)
        # Force the display of the currently selected item in case index changed event not fired
        self.combo_index_changed()

    def ok_clicked(self):
        # Persist the test data and selected index into the JSON file
        test_data = {}
        test_data[TEST_LAST_BOOK_KEY] = self._book_combo.currentIndex()
        data_row = self.data_items[self._book_combo.currentIndex()]
        data_row['author'] = unicode(self._author_edit.text()).strip()
        data_row['title'] = unicode(self._title_edit.text()).strip()
        data_row['publisher'] = unicode(self._publisher_edit.text()).strip()
        data_row['isbn'] = unicode(self._isbn_edit.text()).strip()
        test_data[TEST_VALUES_KEY] = self.data_items
        plugin_prefs[STORE_TEST_NAME] = test_data
        self.accept()

    def combo_index_changed(self):
        # Update the dialog contents with metadata for the selected item
        selected_idx = self._book_combo.currentIndex()
        data_item = self.data_items[selected_idx]
        self._author_edit.setText(data_item['author'])
        self._title_edit.setText(data_item['title'])
        self._publisher_edit.setText(data_item['publisher'])
        self._isbn_edit.setText(data_item['isbn'])


class PickImageDialog(QDialog): # {{{

    def __init__(self, parent=None, resources_dir='', image_names=[]):
        QDialog.__init__(self, parent)
        self.resources_dir = resources_dir
        self.image_names = image_names
        self.setWindowTitle(_('Add New Image'))
        v = QVBoxLayout(self)

        group_box = QGroupBox(_('&Select image source'), self)
        v.addWidget(group_box)
        grid = QGridLayout()
        self._radio_web = QRadioButton(_('From &web domain favicon'), self)
        self._radio_web.setChecked(True)
        self._web_domain_edit = QLineEdit(self)
        self._radio_web.setFocusProxy(self._web_domain_edit)
        grid.addWidget(self._radio_web, 0, 0)
        grid.addWidget(self._web_domain_edit, 0, 1)
        grid.addWidget(QLabel('e.g. www.amazon.com'), 0, 2)
        self._radio_file = QRadioButton(_('From .png &file'), self)
        self._input_file_edit = QLineEdit(self)
        self._input_file_edit.setMinimumSize(200, 0)
        self._radio_file.setFocusProxy(self._input_file_edit)
        pick_button = QPushButton('...', self)
        pick_button.setMaximumSize(24, 20)
        pick_button.clicked.connect(self.pick_file_to_import)
        grid.addWidget(self._radio_file, 1, 0)
        grid.addWidget(self._input_file_edit, 1, 1)
        grid.addWidget(pick_button, 1, 2)
        group_box.setLayout(grid)

        save_layout = QHBoxLayout()
        lbl_filename = QLabel(_('&Save as filename:'), self)
        lbl_filename.setMinimumSize(155, 0)
        self._save_as_edit = QLineEdit('', self)
        self._save_as_edit.setMinimumSize(200, 0)
        lbl_filename.setBuddy(self._save_as_edit)
        lbl_ext = QLabel('.png', self)
        save_layout.addWidget(lbl_filename, 0, Qt.AlignLeft)
        save_layout.addWidget(self._save_as_edit, 0, Qt.AlignLeft)
        save_layout.addWidget(lbl_ext, 1, Qt.AlignLeft)
        v.addLayout(save_layout)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.ok_clicked)
        button_box.rejected.connect(self.reject)
        v.addWidget(button_box)
        self.resize(self.sizeHint())
        self._web_domain_edit.setFocus()
        self.new_image_name = None

    @property
    def image_name(self):
        return self.new_image_name

    def pick_file_to_import(self):
        images = choose_files(None, 'menu icon dialog', _('Select a .png file for the menu icon'),
                             filters=[('PNG Image Files', ['png'])], all_files=False, select_only_single_file=True)
        if not images:
            return
        f = images[0]
        if not f.lower().endswith('.png'):
            return error_dialog(self, _('Cannot select image'),
                    _('Source image must be a .png file.'), show=True)
        self._input_file_edit.setText(f)
        self._save_as_edit.setText(os.path.splitext(os.path.basename(f))[0])

    def ok_clicked(self):
        # Validate all the inputs
        save_name = unicode(self._save_as_edit.text()).strip()
        if not save_name:
            return error_dialog(self, _('Cannot import image'),
                    _('You must specify a filename to save as.'), show=True)
        self.new_image_name = os.path.splitext(save_name)[0] + '.png'
        if save_name.find('\\') > -1 or save_name.find('/') > -1:
            return error_dialog(self, _('Cannot import image'),
                    _('The save as filename should consist of a filename only.'), show=True)
        if not os.path.exists(self.resources_dir):
            os.makedirs(self.resources_dir)
        dest_path = os.path.join(self.resources_dir, self.new_image_name)
        if save_name in self.image_names or os.path.exists(dest_path):
            if not question_dialog(self, _('Are you sure?'), '<p>'+
                    _('An image with this name already exists - overwrite it?'),
                    show_copy_button=False):
                return

        if self._radio_web.isChecked():
            domain = unicode(self._web_domain_edit.text()).strip()
            if not domain:
                return error_dialog(self, _('Cannot import image'),
                        _('You must specify a web domain url'), show=True)
            url = 'http://www.google.com/s2/favicons?domain=' + domain
            urlretrieve(url, dest_path)
            return self.accept()
        else:
            source_file_path = unicode(self._input_file_edit.text()).strip()
            if not source_file_path:
                return error_dialog(self, _('Cannot import image'),
                        _('You must specify a source file.'), show=True)
            if not source_file_path.lower().endswith('.png'):
                return error_dialog(self, _('Cannot import image'),
                        _('Source image must be a .png file.'), show=True)
            if not os.path.exists(source_file_path):
                return error_dialog(self, _('Cannot import image'),
                        _('Source image does not exist!'), show=True)
            shutil.copyfile(source_file_path, dest_path)
            return self.accept()


class EncodingComboBox(NoWheelComboBox):

    def __init__(self, parent, selected_text):
        NoWheelComboBox.__init__(self, parent)
        self.populate_combo(selected_text)

    def populate_combo(self, selected_text):
        self.addItems(['utf-8', 'latin-1'])
        idx = self.findText(selected_text)
        self.setCurrentIndex(idx)


class MethodComboBox(NoWheelComboBox):

    def __init__(self, parent, selected_text):
        NoWheelComboBox.__init__(self, parent)
        self.populate_combo(selected_text)

    def populate_combo(self, selected_text):
        self.addItems(['GET', 'POST'])
        idx = self.findText(selected_text)
        self.setCurrentIndex(idx)


class ImageComboBox(NoWheelComboBox):

    def __init__(self, parent, image_names, images, selected_text):
        NoWheelComboBox.__init__(self, parent)
        self.populate_combo(image_names, images, selected_text)

    def populate_combo(self, image_names, images, selected_text):
        self.clear()
        for i, image in enumerate(image_names):
            self.insertItem(i, images[i], image)
        idx = self.findText(selected_text)
        self.setCurrentIndex(idx)
        self.setItemData(0, idx)


class MenuTableWidget(QTableWidget):
    COMBO_IMAGE_ADD = _('Add New Image')+'...'

    def __init__(self, data_items, *args):
        QTableWidget.__init__(self, *args)
        self.populate_table(data_items)
        self.cellChanged.connect(self.cell_changed)

    def url_column_width(self):
        if self.columnCount() > 4:
            return self.columnWidth(5)
        else:
            c = plugin_prefs[STORE_MENUS_NAME]
            return c.get(COL_WIDTH_KEY, -1)

    def read_image_combo_names(self):
        # Read all of the images that are contained in the zip file
        image_names = get_default_icon_names()
        # Remove all the images that do not have the stip_ prefix
        image_names = [x for x in image_names if x.startswith('stip_')]
        # Now read any images from the config\resources\images directory if any
        self.resources_dir = get_local_images_dir('Search The Internet')

        if os.path.exists(self.resources_dir):
            # Get the names of any .png images in this directory
            for f in os.listdir(self.resources_dir):
                if f.lower().endswith('.png'):
                    image_names.append(os.path.basename(f))

        image_names.sort()
        # Add a blank item at the beginning of the list, and a blank then special 'Add" item at end
        image_names.insert(0, '')
        image_names.append('')
        image_names.append(self.COMBO_IMAGE_ADD)
        self.image_names = image_names
        self.images = [get_icon(get_pathed_icon(x)) for x in image_names]

    def populate_table(self, data_items):
        self.read_image_combo_names()
        last_url_column_width = self.url_column_width()
        self.clear()
        self.setAlternatingRowColors(True)
        self.setRowCount(len(data_items))
        header_labels = ['', _('Title'), _('Submenu'), _('Open Group'),
                         _('Image'), _('Url'), _('Encoding'), _('Method')]
        self.setColumnCount(len(header_labels))
        self.setHorizontalHeaderLabels(header_labels)
        self.verticalHeader().setDefaultSectionSize(24)

        for row, data in enumerate(data_items):
            self.populate_table_row(row, data)

        self.resizeColumnsToContents()
        # Special sizing for the URL column as it tends to dominate the dialog
        if last_url_column_width != -1:
            self.setColumnWidth(5, last_url_column_width)
        self.setSortingEnabled(False)
        self.setMinimumSize(800, 0)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.selectRow(0)

    def populate_table_row(self, row, data):
        self.blockSignals(True)
        icon_name = data['image']
        menu_text = data['menuText']
        self.setItem(row, 0, CheckableTableWidgetItem(data['active']))
        self.setItem(row, 1, TextIconWidgetItem(menu_text, get_icon(get_pathed_icon(icon_name))))
        self.setItem(row, 2, QTableWidgetItem(data['subMenu']))
        if menu_text:
            self.set_editable_cells_in_row(row, open_group=data['openGroup'], image=icon_name,
                        url=fix_legacy_url(data['url']), encoding=data['encoding'],
                        method=data.get('method', 'GET'))
        else:
            # Make all the later column cells non-editable
            self.set_noneditable_cells_in_row(row)
        self.blockSignals(False)

    def append_data(self, data_items):
        for data in reversed(data_items):
            row = self.currentRow() + 1
            self.insertRow(row)
            self.populate_table_row(row, data)

    def get_data(self):
        data_items = []
        for row in range(self.rowCount()):
            data_items.append(self.convert_row_to_data(row))
        # Remove any blank separator row items from the end as unneeded.
        while len(data_items) > 0 and len(data_items[-1]['menuText']) == 0:
            data_items.pop()
        return data_items

    def get_selected_data(self):
        data_items = []
        for row in self.selectionModel().selectedRows():
            data_items.append(self.convert_row_to_data(row.row()))
        return data_items

    def get_selected_urls_to_test(self):
        rows = self.selectionModel().selectedRows()
        for row in rows:
            url = unicode(self.item(row.row(), 5).text()).strip()
            if url:
                encoding = unicode(self.cellWidget(row.row(), 6).currentText()).strip()
                method = unicode(self.cellWidget(row.row(), 7).currentText()).strip()
                yield url, encoding, method

    def convert_row_to_data(self, row):
        data = self.create_blank_row_data()
        data['active'] = self.item(row, 0).checkState() == Qt.Checked
        data['menuText'] = unicode(self.item(row, 1).text()).strip()
        data['subMenu'] = unicode(self.item(row, 2).text()).strip()
        if data['menuText']:
            data['openGroup'] = self.item(row, 3).checkState() == Qt.Checked
            data['image'] = unicode(self.cellWidget(row, 4).currentText()).strip()
            data['url'] = unicode(self.item(row, 5).text()).strip()
            data['encoding'] = unicode(self.cellWidget(row, 6).currentText()).strip()
            data['method'] = unicode(self.cellWidget(row, 7).currentText()).strip()
        return data

    def cell_changed(self, row, col):
        if col == 1:
            menu_text = unicode(self.item(row, col).text()).strip()
            if menu_text:
                # Make sure that the other columns in this row are enabled if not already.
                if not self.item(row, 5).flags() & Qt.ItemIsEditable:
                    # We need to make later columns in this row editable
                    self.set_editable_cells_in_row(row)
            else:
                # Blank menu text so treat it as a separator row
                self.set_noneditable_cells_in_row(row)

    def set_editable_cells_in_row(self, row, open_group=False, image='', url='', encoding='utf-8', method='GET'):
        self.setItem(row, 3, CheckableTableWidgetItem(open_group))
        image_combo = ImageComboBox(self, self.image_names, self.images, image)
        image_combo.currentIndexChanged.connect(partial(self.image_combo_index_changed, image_combo, row))
        self.setCellWidget(row, 4, image_combo)
        self.setItem(row, 5, QTableWidgetItem(url))
        self.setCellWidget(row, 6, EncodingComboBox(self, encoding))
        self.setCellWidget(row, 7, MethodComboBox(self, method))

    def set_noneditable_cells_in_row(self, row):
        for col in range(3,8):
            if self.cellWidget(row, col):
                self.removeCellWidget(row, col)
            item = QTableWidgetItem()
            item.setFlags(Qt.ItemIsSelectable|Qt.ItemIsEnabled)
            self.setItem(row, col, item)
        self.item(row, 1).setIcon(QIcon())

    def create_blank_row_data(self):
        data = {}
        data['active'] = True
        data['menuText'] = ''
        data['subMenu'] = ''
        data['openGroup'] = False
        data['image'] = ''
        data['url'] = ''
        data['encoding'] = ''
        data['method'] = ''
        return data

    def display_add_new_image_dialog(self, select_in_combo=False, combo=None):
        add_image_dialog = PickImageDialog(self, self.resources_dir, self.image_names)
        add_image_dialog.exec_()
        if add_image_dialog.result() == QDialog.Rejected:
            # User cancelled the add operation or an error - set to previous value
            if select_in_combo and combo:
                prevIndex = combo.itemData(0)
                combo.blockSignals(True)
                combo.setCurrentIndex(prevIndex)
                combo.blockSignals(False)
            return
        # User has added a new image so we need to repopulate every combo with new sorted list
        self.read_image_combo_names()
        for update_row in range(self.rowCount()):
            cellCombo = self.cellWidget(update_row, 4)
            if cellCombo:
                cellCombo.blockSignals(True)
                cellCombo.populate_combo(self.image_names, self.images, cellCombo.currentText())
                cellCombo.blockSignals(False)
        # Now select the newly added item in this row if required
        if select_in_combo and combo:
            idx = combo.findText(add_image_dialog.image_name)
            combo.blockSignals(True)
            combo.setCurrentIndex(idx)
            combo.blockSignals(False)

    def image_combo_index_changed(self, combo, row):
        if combo.currentText() == self.COMBO_IMAGE_ADD:
            # Special item in the combo for choosing a new image to add to Calibre
            self.display_add_new_image_dialog(select_in_combo=True, combo=combo)
        # Regardless of new or existing item, update image on the title column
        title_item = self.item(row, 1)
        title_item.setIcon(combo.itemIcon(combo.currentIndex()))
        # Store the current index as item data in index 0 in case user cancels dialog in future
        combo.setItemData(0, combo.currentIndex())

    def add_row(self):
        self.setFocus()
        # We will insert a blank row below the currently selected row
        row = self.currentRow() + 1
        self.insertRow(row)
        self.populate_table_row(row, self.create_blank_row_data())
        self.select_and_scroll_to_row(row)

    def delete_rows(self):
        self.setFocus()
        selrows = self.selectionModel().selectedRows()
        selrows = sorted(selrows, key=lambda x: x.row())
        if len(selrows) == 0:
            return
        message = _('Are you sure you want to delete this menu item?')
        if len(selrows) > 1:
            message = _('Are you sure you want to delete the selected {0} menu items?').format(len(selrows))
        if not question_dialog(self, _('Are you sure?'), '<p>'+message, show_copy_button=False):
            return
        first_sel_row = selrows[0].row()
        for selrow in reversed(selrows):
            self.model().removeRow(selrow.row())
        if first_sel_row < self.model().rowCount(QModelIndex()):
            self.setCurrentIndex(self.model().index(first_sel_row, 0))
            self.select_and_scroll_to_row(first_sel_row)
        elif self.model().rowCount(QModelIndex()) > 0:
            self.setCurrentIndex(self.model().index(first_sel_row - 1, 0))
            self.select_and_scroll_to_row(first_sel_row - 1)

    def move_rows_up(self):
        self.setFocus()
        rows = self.selectionModel().selectedRows()
        if len(rows) == 0:
            return
        first_sel_row = rows[0].row()
        if first_sel_row <= 0:
            return
        # Workaround for strange selection bug in Qt which "alters" the selection
        # in certain circumstances which meant move down only worked properly "once"
        selrows = []
        for row in rows:
            selrows.append(row.row())
        selrows.sort()
        for selrow in selrows:
            self.swap_row_widgets(selrow - 1, selrow + 1)
        scroll_to_row = first_sel_row - 1
        if scroll_to_row > 0:
            scroll_to_row = scroll_to_row - 1
        self.scrollToItem(self.item(scroll_to_row, 0))

    def move_rows_down(self):
        self.setFocus()
        rows = self.selectionModel().selectedRows()
        if len(rows) == 0:
            return
        last_sel_row = rows[-1].row()
        if last_sel_row == self.rowCount() - 1:
            return
        # Workaround for strange selection bug in Qt which "alters" the selection
        # in certain circumstances which meant move down only worked properly "once"
        selrows = []
        for row in rows:
            selrows.append(row.row())
        selrows.sort()
        for selrow in reversed(selrows):
            self.swap_row_widgets(selrow + 2, selrow)
        scroll_to_row = last_sel_row + 1
        if scroll_to_row < self.rowCount() - 1:
            scroll_to_row = scroll_to_row + 1
        self.scrollToItem(self.item(scroll_to_row, 0))

    def swap_row_widgets(self, src_row, dest_row):
        self.blockSignals(True)
        self.insertRow(dest_row)
        for col in range(0,3):
            self.setItem(dest_row, col, self.takeItem(src_row, col))
        menu_text = unicode(self.item(dest_row, 1).text()).strip()
        if menu_text:
            for col in range(3,8):
                if col == 4:
                    # Image column has a combobox we have to recreate as cannot move widget (Qt crap)
                    icon_name = self.cellWidget(src_row, col).currentText()
                    image_combo = ImageComboBox(self, self.image_names, self.images, icon_name)
                    image_combo.currentIndexChanged.connect(partial(self.image_combo_index_changed, image_combo, dest_row))
                    self.setCellWidget(dest_row, col, image_combo)
                elif col == 6:
                    # Encoding column has a combo box we also have to recreate
                    encoding = self.cellWidget(src_row, col).currentText()
                    self.setCellWidget(dest_row, col, EncodingComboBox(self, encoding))
                elif col == 7:
                    # Method column has a combo box we also have to recreate
                    method = self.cellWidget(src_row, col).currentText()
                    self.setCellWidget(dest_row, col, MethodComboBox(self, method))
                else:
                    # Any other column we transfer the TableWidgetItem
                    self.setItem(dest_row, col, self.takeItem(src_row, col))
        else:
            # This is a separator row
            self.set_noneditable_cells_in_row(dest_row)
        self.removeRow(src_row)
        self.blockSignals(False)

    def select_and_scroll_to_row(self, row):
        self.selectRow(row)
        self.scrollToItem(self.currentItem())

    def move_active_to_top(self):
        # Select all of the inactive items and move them to the bottom of the list
        if self.rowCount() == 0:
            return
        self.setUpdatesEnabled(False)
        last_row = self.rowCount()
        row = 0
        for count in range(last_row):
            active = self.item(row, 0).checkState() == Qt.Checked
            if active:
                # Move on to the next row
                row = row + 1
            else:
                # Move this row to the bottom of the grid
                self.swap_row_widgets(row, last_row)
        self.setUpdatesEnabled(True)


class ConfigWidget(QWidget):

    def __init__(self, plugin_action):
        QWidget.__init__(self)
        self.plugin_action = plugin_action
        layout = QVBoxLayout(self)
        self.setLayout(layout)

        c = plugin_prefs[STORE_MENUS_NAME]
        data_items = get_menus_as_dictionary(c[MENUS_KEY])

        heading_layout = QHBoxLayout()
        layout.addLayout(heading_layout)
        heading_label = QLabel(_('Select and configure the menu items to display:'), self)
        heading_layout.addWidget(heading_label)

        # Add a horizontal layout containing the table and the buttons next to it
        table_layout = QHBoxLayout()
        layout.addLayout(table_layout)

        # Create a table the user can edit the data values in
        self._table = MenuTableWidget(data_items, self)
        heading_label.setBuddy(self._table)
        table_layout.addWidget(self._table)

        # Add a vertical layout containing the the buttons to move up/down etc.
        button_layout = QVBoxLayout()
        table_layout.addLayout(button_layout)
        move_up_button = QToolButton(self)
        move_up_button.setToolTip(_('Move row up'))
        move_up_button.setIcon(QIcon(I('arrow-up.png')))
        button_layout.addWidget(move_up_button)
        spacerItem = QSpacerItem(20, 40, qSizePolicy_Minimum, qSizePolicy_Expanding)
        button_layout.addItem(spacerItem)

        add_button = QToolButton(self)
        add_button.setToolTip(_('Add menu item row'))
        add_button.setIcon(QIcon(I('plus.png')))
        button_layout.addWidget(add_button)
        spacerItem2 = QSpacerItem(20, 40, qSizePolicy_Minimum, qSizePolicy_Expanding)
        button_layout.addItem(spacerItem2)

        delete_button = QToolButton(self)
        delete_button.setToolTip(_('Delete menu item row'))
        delete_button.setIcon(QIcon(I('minus.png')))
        button_layout.addWidget(delete_button)
        spacerItem1 = QSpacerItem(20, 40, qSizePolicy_Minimum, qSizePolicy_Expanding)
        button_layout.addItem(spacerItem1)

        reset_button = QToolButton(self)
        reset_button.setToolTip(_('Reset to defaults'))
        reset_button.setIcon(get_icon('clear_left'))
        button_layout.addWidget(reset_button)
        spacerItem3 = QSpacerItem(20, 40, qSizePolicy_Minimum, qSizePolicy_Expanding)
        button_layout.addItem(spacerItem3)

        move_down_button = QToolButton(self)
        move_down_button.setToolTip(_('Move row down'))
        move_down_button.setIcon(QIcon(I('arrow-down.png')))
        button_layout.addWidget(move_down_button)

        move_up_button.clicked.connect(self._table.move_rows_up)
        move_down_button.clicked.connect(self._table.move_rows_down)
        add_button.clicked.connect(self._table.add_row)
        delete_button.clicked.connect(self._table.delete_rows)
        reset_button.clicked.connect(self.reset_to_defaults)

        keyboard_layout = QHBoxLayout()
        layout.addLayout(keyboard_layout)
        keyboard_shortcuts_button = QPushButton(' '+_('Keyboard shortcuts')+'... ', self)
        keyboard_shortcuts_button.setToolTip(_('Edit the keyboard shortcuts associated with this plugin'))
        keyboard_shortcuts_button.clicked.connect(self.edit_shortcuts)
        keyboard_layout.addWidget(keyboard_shortcuts_button)

        help_button = QPushButton(' '+_('&Help'), self)
        help_button.setIcon(get_icon('help.png'))
        help_button.clicked.connect(show_help)
        keyboard_layout.addWidget(help_button)
        keyboard_layout.insertStretch(-1)

        # Define a context menu for the table widget
        self.create_context_menu()
        # Build a list of all the active unique names
        self.orig_unique_active_menus = self.get_active_unique_names(data_items)
        self.orig_open_group_visible = self.is_open_group_visible(data_items)

    def save_settings(self):
        # Invoked when user clicks ok in preferences dialog. Persist new configuration data.
        search_menus = {}
        search_menus[MENUS_KEY] = self._table.get_data()
        search_menus[COL_WIDTH_KEY] = self._table.url_column_width()
        plugin_prefs[STORE_MENUS_NAME] = search_menus

        # For each menu that was visible but now is not, we need to unregister any
        # keyboard shortcut associated with that action.
        menus_changed = False
        kb = self.plugin_action.gui.keyboard
        new_unique_active_menus = self.get_active_unique_names(search_menus[MENUS_KEY])
        for raw_unique_name in list(self.orig_unique_active_menus.keys()):
            if raw_unique_name not in new_unique_active_menus:
                unique_name = menu_action_unique_name(self.plugin_action, raw_unique_name)
                if unique_name in kb.shortcuts:
                    kb.unregister_shortcut(unique_name)
                    menus_changed = True
        # We also need to check for the situation of the Open Group menu item, which might
        # have existed previously but no longer will be visible.
        if self.orig_open_group_visible and not self.is_open_group_visible(search_menus[MENUS_KEY]):
            unique_name = menu_action_unique_name(self.plugin_action, _('Open Group'))
            kb.unregister_shortcut(unique_name)
            menus_changed = True
        if menus_changed:
            self.plugin_action.gui.keyboard.finalize()
        self.orig_unique_active_menus = new_unique_active_menus

    def get_active_unique_names(self, data_items):
        active_unique_names = {}
        for data in data_items:
            if data['active']:
                unique_name = data['menuText']
                active_unique_names[unique_name] = data['menuText']
        return active_unique_names

    def is_open_group_visible(self, data_items):
        for data in data_items:
            if data['active'] and data['openGroup']:
                return True
        return False

    def create_context_menu(self):
        table = self._table
        table.setContextMenuPolicy(Qt.ActionsContextMenu)
        act_add_image = QAction(get_icon('images/image_add.png'), _('Add image')+'...', table)
        act_add_image.triggered.connect(table.display_add_new_image_dialog)
        table.addAction(act_add_image)
        act_open = QAction(get_icon('document_open.png'), _('Open images folder'), table)
        act_open.triggered.connect(partial(self.open_images_folder, table.resources_dir))
        table.addAction(act_open)
        sep1 = QAction(table)
        sep1.setSeparator(True)
        table.addAction(sep1)
        act_move = QAction(get_icon('images/move_to_top.png'), _('Move active to top'), table)
        act_move.triggered.connect(table.move_active_to_top)
        table.addAction(act_move)
        sep2 = QAction(table)
        sep2.setSeparator(True)
        table.addAction(sep2)
        act_test1 = QAction(get_icon('images/internet.png'), _('Test url'), table)
        act_test1.setShortcut(_('Ctrl+T'))
        act_test1.triggered.connect(self.test_search)
        table.addAction(act_test1)
        act_test2 = QAction(get_icon('images/internet.png'), _('Test url using')+'...', table)
        act_test2.setShortcut(_('Ctrl+Shift+T'))
        act_test2.triggered.connect(self.test_search_via_dialog)
        table.addAction(act_test2)
        sep3 = QAction(table)
        sep3.setSeparator(True)
        table.addAction(sep3)
        act_import = QAction(get_icon('images/import.png'), _('Import')+'...', table)
        act_import.triggered.connect(self.import_menus)
        table.addAction(act_import)
        act_export = QAction(get_icon('images/export.png'), _('Export')+'...', table)
        act_export.triggered.connect(self.export_menus)
        table.addAction(act_export)

    def reset_to_defaults(self):
        if not question_dialog(self, _('Are you sure?'), '<p>'+
                _('Are you sure you want to reset to the plugin default menu?') + '<br>' +
                _('Any modified configuration and custom menu items will be discarded.'),
                show_copy_button=False):
            return
        self._table.populate_table(get_menus_as_dictionary())

    def open_images_folder(self, path):
        if not os.path.exists(path):
            if not question_dialog(self, _('Are you sure?'), '<p>' +
                    _('Folder does not yet exist. Do you want to create it?') +
                    '<br>{0}'.format(path),
                    show_copy_button=False):
                return
            os.makedirs(path)
        open_local_file(path)

    def test_search_via_dialog(self):
        dialog = PickTestBookDialog()
        dialog.exec_()
        if dialog.result() == QDialog.Rejected:
            return
        # Go ahead an display the webpage using the last selected test book
        self.test_search()

    def test_search(self):
        # Check we are not on a separator row
        test_rows = list(self._table.get_selected_urls_to_test())
        if len(test_rows) == 0:
            return error_dialog(self, _('Cannot test'),
                                _('You must select a menu item with a url to test it.'), show=True)
        for tokenised_url, encoding, method in test_rows:
            c = plugin_prefs[STORE_TEST_NAME]
            selected_idx = c.get(TEST_LAST_BOOK_KEY)
            test_data_items = c.get(TEST_VALUES_KEY)
            test_data_item = test_data_items[selected_idx]
            mi = Metadata(test_data_item['title'], [test_data_item['author']])
            mi.publisher = test_data_item['publisher']
            mi.isbn = test_data_item['isbn']
            self.plugin_action.open_tokenised_url(tokenised_url, encoding, method, mi)

    def import_menus(self):
        table = self._table
        archive_path = self.pick_archive_name_to_import()
        if not archive_path:
            return
        # Write the whole file contents into the resources\images directory
        if not os.path.exists(table.resources_dir):
            os.makedirs(table.resources_dir)
        with ZipFile(archive_path, 'r') as zf:
            contents = zf.namelist()
            if 'stip_menus.json' not in contents:
                return error_dialog(self, _('Import Failed'),
                                    _('This is not a valid STIP export archive'), show=True)
            for resource in contents:
                fs = os.path.join(table.resources_dir,resource)
                with open(fs,'wb') as f:
                    f.write(zf.read(resource))
        json_path = os.path.join(table.resources_dir,'stip_menus.json')
        try:
            # Read the .JSON file to add to the menus then delete it.
            archive_config = JSONConfig('resources/images/stip_menus')
            menus_config = archive_config.get(STORE_MENUS_NAME).get(MENUS_KEY)
            # Now insert the menus into the table
            table.append_data(menus_config)
            info_dialog(self, _('Import completed'), _('{0} menu items added').format(len(menus_config)),
                        show=True, show_copy_button=False)
        finally:
            if os.path.exists(json_path):
                os.remove(json_path)

    def export_menus(self):
        table = self._table
        data_items = table.get_selected_data()
        if len(data_items) == 0:
            return error_dialog(self, _('Cannot export'),
                                _('No menu items selected to export.'), show=True)
        archive_path = self.pick_archive_name_to_export()
        if not archive_path:
            return
        # Build our unique list of images that need to be exported
        image_names = {}
        for data in data_items:
            image_name = data['image']
            if image_name and image_name not in image_names:
                image_path = os.path.join(table.resources_dir, image_name)
                if os.path.exists(image_path):
                    image_names[image_name] = image_path
        # Write our menu items out to a json file
        if not os.path.exists(table.resources_dir):
            os.makedirs(table.resources_dir)
        archive_config = JSONConfig('resources/images/stip_menus')
        export_menus = {}
        export_menus[MENUS_KEY] = data_items
        archive_config.set(STORE_MENUS_NAME, export_menus)
        json_path = os.path.join(table.resources_dir,'stip_menus.json')

        try:
            # Create the zip file archive
            with ZipFile(archive_path, 'w') as archive_zip:
                archive_zip.write(json_path, os.path.basename(json_path))
                # Add any images referred to in those menu items that are local resources
                for image_name, image_path in list(image_names.items()):
                    archive_zip.write(image_path, os.path.basename(image_path))
            info_dialog(self, _('Export completed'),
                        '{0} menu items exported to'.format(len(data_items)) + 
                        '<br>{0}'.format(archive_path),
                        show=True, show_copy_button=False)
        finally:
            if os.path.exists(json_path):
                os.remove(json_path)

    def pick_archive_name_to_import(self):
        archives = choose_files(self, 'stip archive dialog', _('Select a menu file archive to import'),
                             filters=[('STIP Files', ['stip','zip'])], all_files=False, select_only_single_file=True)
        if not archives:
            return
        f = archives[0]
        return f

    def pick_archive_name_to_export(self):
        fd = FileDialog(name='stip archive dialog', title='Save archive as', filters=[('STIP Files', ['zip'])],
                        parent=self, add_all_files_filter=False, mode=QFileDialog.AnyFile)
        fd.setParent(None)
        if not fd.accepted:
            return None
        return fd.get_files()[0]

    def edit_shortcuts(self):
        self.save_settings()
        # Force the menus to be rebuilt immediately, so we have all our actions registered
        self.plugin_action.rebuild_menus()
        d = KeyboardConfigDialog(self.plugin_action.gui, self.plugin_action.action_spec[0])
        if d.exec_() == d.Accepted:
            self.plugin_action.gui.keyboard.finalize()
