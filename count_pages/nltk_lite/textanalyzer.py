# -*- coding: utf-8 -*-
# Sets the encoding to utf-8 to avoid problems with æøå

import pickle
try:
    from . import syllables_en
except ImportError:
    import calibre_plugins.count_pages.nltk_lite.syllables_en
try:
    from regexp import RegexpTokenizer
except ImportError:
    from calibre_plugins.count_pages.nltk_lite.regexp import RegexpTokenizer
import six
from six import text_type as unicode

class TextAnalyzer(object):

    tokenizer = RegexpTokenizer('(?u)\W+|\$[\d\.]+|\S+')
    special_chars = ['.', ',', '!', '?']

    def __init__(self, eng_tokenizer_pickle):
        self.eng_tokenizer = pickle.loads(eng_tokenizer_pickle)

    def analyzeText(self, text=''):
        words = self.getWords(text)
        charCount = self.getCharacterCount(words)
        wordCount = len(words)
        sentences = self.getSentences(text)
        sentenceCount = len(sentences)
        syllableCount = self.countSyllables(words)
        complexwordsCount = self.countComplexWords(text, sentences, words)
        averageWordsPerSentence = wordCount/sentenceCount
        print('\tResults of NLTK text analysis:')
        print('\t  Number of characters: ' + str(charCount))
        print('\t  Number of words: ' + str(wordCount))
        print('\t  Number of sentences: ' + str(sentenceCount))
        print('\t  Number of syllables: ' + str(syllableCount))
        print('\t  Number of complex words: ' + str(complexwordsCount))
        print('\t  Average words per sentence: ' + str(averageWordsPerSentence))
        analyzedVars = {}
        analyzedVars['words'] = words
        analyzedVars['charCount'] = float(charCount)
        analyzedVars['wordCount'] = float(wordCount)
        analyzedVars['sentenceCount'] = float(sentenceCount)
        analyzedVars['syllableCount'] = float(syllableCount)
        analyzedVars['complexwordCount'] = float(complexwordsCount)
        analyzedVars['averageWordsPerSentence'] = float(averageWordsPerSentence)
        return analyzedVars

    def getCharacterCount(self, words):
        characters = 0
        for word in words:
            #Grant
            #word = self._setEncoding(word)
            characters += len(word)#.decode("utf-8"))
        return characters

    def getWords(self, text=''):
        #Grant
        #text = self._setEncoding(text)
        words = self.tokenizer.tokenize(text)
        filtered_words = []
        for word in words:
            if word in self.special_chars or word == " ":
                pass
            else:
                new_word = word.replace(",","").replace(".","")
                new_word = new_word.replace("!","").replace("?","")
                filtered_words.append(new_word)
        #print('Filtered words:', filtered_words)
        return filtered_words

    def getSentences(self, text=''):
        sentences = self.eng_tokenizer.tokenize(text)
        return sentences

    def countSyllables(self, words = []):
        syllableCount = 0
        syllableCounter = {}
        syllableCounter['eng'] = syllables_en.count
        for word in words:
            syllableCount += syllableCounter['eng'](word)

        return syllableCount

    #This method must be enhanced. At the moment it only
    #considers the number of syllables in a word.
    #This often results in that too many complex words are detected.
    def countComplexWords(self, text='', sentences=[], words=[]):
        if not sentences:
            sentences = self.getSentences(text)
        if not words:
            words = self.getWords(text)
        complexWords = 0
        found = False;
        #Just for manual checking and debugging.
        #cWords = []
        curWord = []

        for word in words:
            curWord.append(word)
            if self.countSyllables(curWord)>= 3:

                #Checking proper nouns. If a word starts with a capital letter
                #and is NOT at the beginning of a sentence we don't add it
                #as a complex word.
                if not(word[0].isupper()):
                    complexWords += 1
                    #cWords.append(word)
                else:
                    for sentence in sentences:
                        if str(sentence).startswith(word):
                            found = True
                            break

                    if found:
                        complexWords+=1
                        found = False

            curWord.remove(word)
        #print(cWords)
        return complexWords

    def _setEncoding(self,text):
        try:
            text = unicode(text, "utf8").encode("utf8")
        except UnicodeError:
            try:
                text = unicode(text, "iso8859_1").encode("utf8")
            except UnicodeError:
                text = unicode(text, "ascii", "replace").encode("utf8")
        return text
