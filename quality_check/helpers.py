from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2012, Grant Drake'


def get_formatted_author_initials(initials_mode, author):
    '''
    Given an author name, break it down looking for potential initials
    and if any found reformat them to the desired preference indicated
    by initials mode.
    '''
    ignore_words = ['von', 'van', 'jr', 'jr.', 'sr', 'sr.', 'st', 'st.',  
                    'ed', 'ed.', 'dr', 'dr.', 'phd', 'ph.d', 'ph.d.']
    ignore_upper_words = ['ii', 'iii']
    ignore_words_map = dict((k,True) for k in ignore_words)
    
    parts = author.split()
    new_parts = []
    append_to_previous = False
    for tok in parts:
        if len(tok) == 0:
            continue
        handled = False
        # We will only ignore these words if exact match and the
        # author does not have these in uppercase. i.e. JR should
        # be treated as author initials, but Jr or jr will be ignored 
        if tok.lower() in ignore_words_map and tok.upper() != tok:
            pass
        # Some ignore words are likely to be all uppercase. If there
        # was a genuine author with these initials then bad luck!
        # i.e. II or III will get treated as not initials.
        elif tok.lower() in ignore_upper_words:
            pass
        elif tok.isnumeric():
            pass
        # Any word which has a period or is in uppercase with two or less
        # characters will be considered an initial
        elif '.' in tok or (tok.upper() == tok and len(tok) <= 2):
            # Ok, we have something in the expression we will treat as an initial
            # Now figure out how to format it
            if initials_mode == 'A.B.':
                #print('Author',author,'Tok',tok)
                new_tok = ''
                for c in tok.replace('.',''):
                    new_tok += c + '.'
                if append_to_previous:
                    new_parts[-1] = new_parts[-1] + new_tok
                else:
                    new_parts.append(new_tok)
                    append_to_previous = True
            elif initials_mode == 'A. B.':
                new_tok = ''
                for c in tok.replace('.',''):
                    new_tok += c + '. '
                new_parts.append(new_tok.strip())
            elif initials_mode == 'A B':
                new_tok = ''
                for c in tok.replace('.',''):
                    new_tok += c + ' '
                new_parts.append(new_tok.strip())
            elif initials_mode == 'AB':
                new_tok = tok.replace('.','')
                if append_to_previous:
                    new_parts[-1] = new_parts[-1] + new_tok
                else:
                    new_parts.append(new_tok)
                    append_to_previous = True
            
            handled = True
        
        if not handled:
            new_parts.append(tok)
            append_to_previous = False
        
    return ' '.join(new_parts)


def get_title_authors_text(db, book_id):

    def authors_to_list(db, book_id):
        authors = db.authors(book_id, index_is_id=True)
        if authors:
            return [a.strip().replace('|',',') for a in authors.split(',')]
        return []

    title = db.title(book_id, index_is_id=True)
    authors = authors_to_list(db, book_id)
    from calibre.ebooks.metadata import authors_to_string
    return '%s / %s'%(title, authors_to_string(authors))


# calibre-debug -e helpers.py
if __name__ == '__main__':
    def test(initials_mode, author, expected):
        result = get_formatted_author_initials(initials_mode, author)
        if result != expected:
            print(('%s - (%s) => Expected: %s - Result: %s'%(author, initials_mode,
                                                           expected, result)))

    # Test some cases independent of the initials mode
    test('A.B.','Joe Bloggs','Joe Bloggs')
    test('A.B.','Bloggs, Joe','Bloggs, Joe')
    test('A.B.','JR Bloggs','J.R. Bloggs')
    test('A.B.','Joe Bloggs Jr','Joe Bloggs Jr')
    test('A.B.','Joe Bloggs Jr.','Joe Bloggs Jr.')
    test('A.B.','Joe Bloggs Ph.D','Joe Bloggs Ph.D')
    test('A.B.','Joe Bloggs Ph.D.','Joe Bloggs Ph.D.')
    test('A.B.','Joe Bloggs ii','Joe Bloggs ii')
    test('A.B.','Joe Bloggs iii','Joe Bloggs iii')
    
    test('A.B.','J. Bloggs','J. Bloggs')
    test('A.B.','J Bloggs','J. Bloggs')
    test('A.B.','Bloggs, J.','Bloggs, J.')
    test('A.B.','Bloggs, J','Bloggs, J.')
    test('A.B.','JA Bloggs','J.A. Bloggs')
    test('A.B.','Joe X Bloggs','Joe X. Bloggs')
    test('A.B.','J..A Bloggs','J.A. Bloggs')
    test('A.B.','J.A. Bloggs','J.A. Bloggs')
    test('A.B.','J. A. Bloggs','J.A. Bloggs')
   
    test('A. B.','J. Bloggs','J. Bloggs')
    test('A. B.','J Bloggs','J. Bloggs')
    test('A. B.','Bloggs, J.','Bloggs, J.')
    test('A. B.','Bloggs, J','Bloggs, J.')
    test('A. B.','JA Bloggs','J. A. Bloggs')
    test('A. B.','Joe X Bloggs','Joe X. Bloggs')
    test('A. B.','J..A Bloggs','J. A. Bloggs')
    test('A. B.','J.A. Bloggs','J. A. Bloggs')
    test('A. B.','J. A. Bloggs','J. A. Bloggs')
    
    test('A B','J. Bloggs','J Bloggs')
    test('A B','J Bloggs','J Bloggs')
    test('A B','Bloggs, J.','Bloggs, J')
    test('A B','Bloggs, J','Bloggs, J')
    test('A B','JA Bloggs','J A Bloggs')
    test('A B','Joe X Bloggs','Joe X Bloggs')
    test('A B','J..A Bloggs','J A Bloggs')
    test('A B','J.A. Bloggs','J A Bloggs')
    test('A B','J. A. Bloggs','J A Bloggs')
    
    test('AB','J. Bloggs','J Bloggs')
    test('AB','J Bloggs','J Bloggs')
    test('AB','Bloggs, J.','Bloggs, J')
    test('AB','Bloggs, J','Bloggs, J')
    test('AB','JA Bloggs','JA Bloggs')
    test('AB','Joe X Bloggs','Joe X Bloggs')
    test('AB','J..A Bloggs','JA Bloggs')
    test('AB','J.A. Bloggs','JA Bloggs')
    test('AB','J. A. Bloggs','JA Bloggs')
   