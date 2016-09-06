#!/usr/bin/env python
"""Contains the necessary tools to score a tokenized job posting. It consists of checking the occurrence of certains words, and ajdusting the score accordingly"""

import csv
import re


# Load the scorefile once per module import. Converts it into a list of regex to be used later
SCOREFILE = "scorefile.csv"
with open(SCOREFILE) as f:
        r = csv.reader(f)
        raw_read = [tuple(row) for row in r if row]
        # remove commens, Add parenthesis and word delimiters \b to all entries
        REGEX_LIST = []
        for x in raw_read:
            if x[0][0] == '#':
                continue
            tmp = '\\b' # Enclosing chars
            left = '(' + tmp
            right = tmp + ')'
            regex_string = left + (right+'|'+left).join(x[0].split('|')) + right
            REGEX_LIST.append((re.compile(regex_string), x[0], float(x[1])))


def score(text, final_score=0):
    """Scores the input text by checking the occurence of words in module.SCOREFILE
    text:  input string to score
    score: initial score to use
    
    outout: score of the text"""
    hit_list = []
    for regex, regex_string, score in REGEX_LIST:
        matchlist = regex.findall(text)
        if matchlist:
            final_score += score
            hit_list.append((regex_string, score))

    return final_score, hit_list


