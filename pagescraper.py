#!/usr/bin/env python
"""Single webpage scraper"""

from lxml import html
from html.parser import HTMLParser
import collections
import requests
import copy
import string
import re

# Sklearn deprecation warnings won't shut up
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

import juntdb as db
import scorer

TECHNICAL_TOKENS = ['python', 'scala', 'css', 'hadoop', 'java', 'b', 'sc', 'ph', 'd', 'r', 'objectoriented', 'zsh', 'msc', 'phd', 'meng', 'eng', 'html', 'javascript', 'jquery', 'api', 'php', 'unix', 'linuxunix', 'sql', 'mysql', 'sqlite', 'kaggle']


TECHNICAL_TOKENS += [str(x) for x in range(100)] # Such that years of experience get included
TECHNICAL_TOKENS = set(TECHNICAL_TOKENS)

# Mostly HTML remnants
USELESS_TOKENS = ['bold', 'color', 'margin', 'left', 'background', 'dash', 'true', 'fals', 'transpar', 'visibl', 'hidden', 'border', 'none', 'pad', 'solid', 'height', 'posit', 'display', 'member', 'width', 'follow', 'inwrap', 'label', 'function', 'absol', 'right', 'close', 'relat', 'outlin', 'job', 'ga', 'reach', 'el', 'search', 'subhead', 'center', 'return', 'locat', 'find', 'mmiddle', 'underlin'
]
    

#-------------------
class PageScraper:
    """Basic class for all website-specific page scrapers"""
    scraped = False
    def __init__(self, url):
        if type(url) != type(str()):
            raise Exception('Url should be a string')
        self.url = url

    def get_source(self):
        """Gets the source for the scraper's URL"""
        page = requests.get(self.url)
        self.pagetree = html.fromstring(page.content)
        self.body = self.pagetree.body
        self.bodytext = list(self.body.itertext())

    def build_bodystring(self):
        """Builds a single string out of the bodytext"""
        self.bodystring = '\n'.join(self.bodytext)

    def get_scrape_date(self):
        """Returns the current date"""
        self.date_scrape = db.build_timestamp_id()

    def scrape(self):
        """Scrapes and partially processes the text foundi n the URL"""
        self.get_source()
        self.get_scrape_date()
        self.build_bodystring()
        self.scraped = True

class PSsmartrecruiters(PageScraper):
    """Page scraper specific to the SmartRecruiters website"""
    def build_bodystring(self):
        self.bodystring = '\n'.join(self.bodytext[:-12])

class PSindeed(PageScraper):
    """Page scraper for the Indeed website"""
    multiscrape_maxcount = 10
    def build_bodystring(self):
        """Builds a single string out of the bodytext"""
        self.bodystring = '\n'.join(self.bodytext[96:-148])
    def get_source(self):
        """Scrapes multiple times, as Indeed.com is known to have variable output"""
        sourcelist = []
        bodytext_lengths = []
        # get the source many times
        for k in range(self.multiscrape_maxcount):
            super(PSindeed, self).get_source()
            bodytext_lengths.append(len(self.bodytext))
            sourcelist.append(copy.copy(self.pagetree))

        # Pick the outputs with the most common length ob bodytext
        b = collections.Counter(bodytext_lengths)
        best_len = b.most_common()[0][0]
        best_source_idx = bodytext_lengths.index(best_len)
        best_source = sourcelist[best_source_idx]
        del sourcelist

        self.pagetree = best_source
        self.body = self.pagetree.body
        self.bodytext = list(self.body.itertext())

class MLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.reset()
        self.fed = []
    def handle_data(self, d):
        self.fed.append(d)
    def get_data(self):
        return ''.join(self.fed)

class Jentry:
    """Job entry object"""
    def __init__(self, obj):
        """Jentry initializes itself from the input object"""
        if isinstance(obj, PageScraper):
            self.scored = False
            if not obj.scraped:
                raise Exception('Input PageScraper has not been scraped yet')
            self.date = obj.date_scrape
            self.bodystring = obj.bodystring
        elif isinstance(obj, dict):
            self.__dict__ = obj
        else:
            raise Exception('Unknown input class')
    def __iter__(self):
        """Iterates over all the non-callable, non-hidden attributes"""
        for key, value in self.__dict__.items():
            if not callable(value) and not key.startswith('__'):
                yield key, value
    def pre_process_bodystring(self):
        """Processes the bodystring to recover the relevant information in it"""
        # Remove html tags
        text = strip_html_tags(self.bodystring)
        
        # Remove punctuation
        regex = re.compile('[%s]' % re.escape(string.punctuation))
        text = regex.sub('', text)

        # only accept words that beegin with an alphabet or a number. outputs lowercase tokens
        tokenizer = RegexpTokenizer('[A-Za-z1-9]\w+')
        tokens = word_tokenize(text.lower())

        # Remove non english words
        linux_words = set(line.strip() for line in open('linuxwords')).union(TECHNICAL_TOKENS)
        english_vocab = set(w.lower() for w in words.words()).union(linux_words)
        english_tokens = [token for token in tokens if token in english_vocab]
        
        # Remove non-stop words and HTML remnants. Also clear different version of the same word (e.g. water vs watered)
        stemmer = SnowballStemmer("english")
        stemmed_tokens = [stemmer.stem(token) for token in english_tokens]
        unwanted_set = stopwords.words('english') + USELESS_TOKENS
        self.processed_tokens = " ".join([token for token in stemmed_tokens if token not in unwanted_set])
    def score(self):
        """Scores the final tokens"""
        self.score, self.score_hits = scorer.score(self.processed_tokens)
        

    def write_db(self):
        """Stores the Jentry in the database. Creates a new db entry if necessary"""
        existing_date = db.fetch_matching({'date':self.date})
        new_data = False
        if not existing_date:
            new_data = True
        db.add(dict(self), new_data=new_data)

def strip_html_tags(html):
    s = MLStripper()
    s.feed(html)
    return s.get_data()




if __name__ == '__main__':

    url = [
    'http://www.indeed.ca/cmp/Mate1-Inc/jobs/Devop-Engineer-a156a3304e6193bc?sjdu=vQIlM60yK_PwYat7ToXhk-E4ENgV3fnJw6x45fMqWb1lojM6yJ0NlafcC4cBp_yEgc5kHZrkOD2NvIrrHdP2HgNJCpsGTgvMW68enfhuWXU',
    'http://www.indeed.ca/cmp/SPORTLOGiQ/jobs/Senior-Back-End-Developer-ada2b84d0a7a860b?sjdu=vQIlM60yK_PwYat7ToXhk1EQcCGKPDd26qp_pQ6XvqM0lUnG7VyC2oe4B-SBpLeg7xoFLmPGxIPXcns4tOAb8-ciw3T5Q1hDbUXoLn1XxwY',
    'http://www.vigilantglobal.com/en/careers/junior-software-developer',
    'http://sunlifefinancial.taleo.net/careersection/global/jobdetail.ftl?job=508864&src=JB-11348',
    'https://www.smartrecruiters.com/Ludia/95985523-intermediate-data-analyst?idpartenaire=136'
]
    #scraper = PSindeed(url)
    scraper = PageScraper(url[4])
    #scraper = PSsmartrecruiters(url)
    scraper.scrape()
    entry = Jentry(scraper)
    entry.pre_process_bodystring()
    entry.score()
    print(entry.score)
    print(entry.score_hits)
    print(entry.processed_tokens)





















