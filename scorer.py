#!/usr/bin/env python
"""Contains the necessary tools to score a tokenized job posting. It consists of checking the occurrence of certains words, and ajdusting the score accordingly"""

import csv
import re
import juntdb


# nltk deprecation warnings won't shut up
import imp
import warnings
def warn(*args, **kwargs):
    pass
warnings.warn = warn
from nltk import pos_tag, word_tokenize
from nltk.stem.snowball import SnowballStemmer
from nltk.tokenize import RegexpTokenizer
from nltk.corpus import stopwords, words
imp.reload(warnings)

# The following non-english words will not be discarded
TECHNICAL_TOKENS = ['python', 'scala', 'css', 'hadoop', 'java', 'b', 'sc', 'ph', 'd', 'r', 'objectoriented', 'zsh', 'msc', 'phd', 'meng', 'eng', 'html', 'javascript', 'jquery', 'api', 'php', 'unix', 'linuxunix', 'sql', 'mysql', 'sqlite', 'kaggle']
TECHNICAL_TOKENS += [str(x) for x in range(100)] # Such that years of experience get included
TECHNICAL_TOKENS = set(TECHNICAL_TOKENS)

# The following tokens will always be discarded
USELESS_TOKENS = ['bold', 'color', 'margin', 'left', 'background', 'dash', 'true', 'fals', 'transpar', 'visibl', 'hidden', 'border', 'none', 'pad', 'solid', 'height', 'posit', 'display', 'member', 'width', 'follow', 'inwrap', 'label', 'function', 'absol', 'right', 'close', 'relat', 'outlin', 'job', 'ga', 'reach', 'el', 'search', 'subhead', 'center', 'return', 'locat', 'find', 'mmiddle', 'underlin'
]

LINUX_WORDS = set(line.strip() for line in open('linuxwords')).union(TECHNICAL_TOKENS)
ENGLISH_VOCAB = set(w.lower() for w in words.words()).union(LINUX_WORDS)
UNWANTED_SET = stopwords.words('english') + USELESS_TOKENS

# File of regex entries
SCOREFILE = "scorefile.csv"


def score(text, final_score=0):
    """Scores the input text by checking the occurence of words in module.SCOREFILE
    text:  input string to score
    score: initial for the score. Default is 0
    
    returns: score of the input text"""
    hit_list = []
    for regex, regex_string, score in REGEX_LIST:
        matchlist = regex.findall(text)
        if matchlist:
            final_score += score
            hit_list.append((regex_string, score))

    return final_score, hit_list

def stem_and_discard(input_tokens, delim_char=' '):
    """Discards non-english words and stems the remainder
    input_tokens: tokens to process
    delim_char:   string to put between the final tokens. Default is ' '
    
    returns: string containg the non-discarded roots of the input tokens"""
    stemmer = SnowballStemmer("english")
    output_str = ''
    for token in input_tokens:
        if token not in ENGLISH_VOCAB:
            pass
        stemmed_token = stemmer.stem(token)
        if stemmed_token not in UNWANTED_SET:
            output_str += stemmed_token + delim_char
    return output_str

def preprocess_scorefile(filename, disp=False):
    """Preprocesses the scoretext into regex entries, one for each row in the scorefile
    filename: string ote filename
    disp:     If true, displays the tokenized version of the scorefile
    
    returns: list of compiled regex parsers"""
    with open(SCOREFILE) as f:
        r = csv.reader(f)
        raw_read = [tuple(row) for row in r if row]

    # remove comments and stem tokens
    entry_list = []
    for x in raw_read:
        if x[0][0] == '#':
            continue
        
        tokenized = stem_and_discard(x[0].split('|'), delim_char='|')[:-1]
        if disp:
            print(tokenized + ',' +x[1])

        # Add parenthesis and word delimiters \b to all entries
        tmp = '\\b' # Enclosing chars
        left = '(' + tmp
        right = tmp + ')'
        regex_string = left + (right+'|'+left).join(tokenized.split('|')) + right
        entry_list.append((re.compile(regex_string), x[0], float(x[1])))

    return entry_list



    
# Load the scorefile once per module import. Converts it into a list of regex to be used later
REGEX_LIST = preprocess_scorefile(SCOREFILE)




if __name__ == '__main__':
    preprocess_scorefile(SCOREFILE, disp=True)



