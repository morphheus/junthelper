#!/usr/bin/env python
"""Single webpage scraper"""

from lxml import html
from html.parser import HTMLParser
from urllib.parse import urlparse
import collections
import requests
import string
import copy
import re
import logging
import sys

import juntdb as db
import scorer

    
# nltk deprecation warnings won't shut up
import imp
import warnings
def warn(*args, **kwargs):
    pass
warnings.warn = warn
from nltk import pos_tag, word_tokenize
from nltk.tokenize import RegexpTokenizer
imp.reload(warnings)

#-------------------
class PageScraper:
    """Basic class for all website-specific page scrapers"""
    scraped = False

    def __init__(self, url, tree):
        """Initializes the pagescraper object
        url:  srtring of the url to scrape
        tree: xml tree of the url"""
        if type(url) != type(str()):
            raise Exception('Url should be a string')
        self.url = url
        self.tree = tree

    def build_bodystring(self):
        """Builds a single string out of the, according to self.process_tree()"""
        # process_tree should ideally be redefined by subclasses. If the subclass definiton fails, revert to default.
        try:
            self.process_tree()
        except Exception:
            if self.__class__.__name__ == 'PageScraper':
                raise
            logging.error('Unexpected error in ' + self.__class__.__name__ + ' for ' + self.url + '. Reverting to default process_tree method')
            self.def_process_tree()

    def process_tree(self):
        """To be overwritten by a subclass"""
        self.def_process_tree()
    
    def def_process_tree(self):
        """Blindly grabs all normal text in the body of the html source. It never fails, but is likely to grab unwanted text, especially if no html body can be found"""
        try:
            bodytext = list(self.tree.body.itertext())
        except IndexError:
            bodytext = list(self.tree.itertext())
        self.bodystring = '\n'.join(bodytext)

    def get_scrape_date(self):
        """Returns the current date"""
        self.date_scrape = db.build_timestamp_id()

    def scrape(self):
        """Wrapper function, scraping all information off the job posting"""
        self.get_scrape_date()
        self.build_bodystring()
        self.scraped = True

class PSsmartrecruiters(PageScraper):
    """Page scraper specific to the SmartRecruiters website"""
    def process_tree(self):
        """Builds a single string out of the bodytext"""
        bodytext = self.tree.xpath('//h1[@class="job-title"]/text()')
        bodytext += self.tree.xpath('//div[@class="job-sections"]//text()')
        self.bodystring = '\n'.join(bodytext)

class PSindeedCa(PageScraper):
    """Page scraper for the Indeed website"""
    def process_tree(self):
        """Processes the tree to extract the job posting string"""
        bodytext = self.tree.xpath('//b[@class="jobtitle"]//text()')
        bodytext = self.tree.xpath('//span[@id="job_summary"]//text()')
        self.bodystring = '\n'.join(bodytext)

class MLStripper(HTMLParser):
    """Container class for the html parser"""
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
    def __init__(self, obj, loc=None):
        """Jentry initializes itself from the input object
        obj:  PageScraper or Dict object to instantiates Jentry from
        loc:  location of the job posting. Default: None"""
        if isinstance(obj, PageScraper):
            self.viewed = False
            self.dead = False
            if not obj.scraped:
                raise Exception('Input PageScraper has not been scraped yet')
            self.date = obj.date_scrape
            self.url = obj.url
            self.bodystring = obj.bodystring
            self.loc = loc
        elif isinstance(obj, dict):
            self.__dict__ = obj
        else:
            raise Exception('Unknown input class')

    def __iter__(self):
        """Iterates over all the non-callable, non-hidden attributes"""
        for key, value in self.__dict__.items():
            if not callable(value) and not key.startswith('__'):
                yield key, value

    def preprocess_bodystring(self):
        """Processes the job posting string to recover the relevant information in it"""
        # Remove html tags
        text = strip_html_tags(self.bodystring)

        # Change commas for space
        regex = re.compile(',')
        text = regex.sub('', text)

        # Remove all other punctuation
        regex = re.compile('[%s]' % re.escape(string.punctuation))
        text = regex.sub('', text)

        # only accept words that beegin with an alphabet or a number. outputs lowercase tokens
        tokenizer = RegexpTokenizer('[A-Za-z1-9]\w+')
        tokens = word_tokenize(text.lower())
        
        self.processed_tokens = scorer.stem_and_discard(tokens)

    def compute_score(self):
        """Scores the job entry as defined in scorefile.csv"""
        self.preprocess_bodystring()
        self.score, self.score_hits = scorer.score(self.processed_tokens)

    def write_db(self, conn=False):
        """Stores the Jentry in the database. Creates a new db entry if necessary
        conn: db connection to use. If False, a new sqlite connection is created"""
        existing_date = db.fetch_matching({'date':[self.date]})
        new_data = False
        if not existing_date:
            new_data = True
        db.add(dict(self), new_data=new_data, conn=conn)

def strip_html_tags(html):
    """Strips the html tags from the input
    html: string of a webpage

    returns: input string without the html tags"""
    s = MLStripper()
    s.feed(html)
    return s.get_data()

def scrape_job_posting(url, **kwargs):
    """Scrapes a Jentry from the job posting url. It first assigns the appropriate page scraper object, then builds a Jentry objet out of it.
    url:    string of the url of the job posting to scrape
    kwargs: kwargs to pass to the Jentry constructor
    
    returns: Jentry built from the input url"""
    r = requests.get(url, allow_redirects=True)
    true_url = r.url
    tree = html.fromstring(r.content)

    # Use domain-appropriate scraper
    domain = urlparse(true_url).hostname
    if domain in ['www.indeed.ca', 'www.indeed.com']:
        scraper_cls = PSindeedCa
    elif domain in ['www.smartrecruiters.ca', 'www.smartrecruiters.com']:
        scraper_cls = PSsmartrecruiters
    else:
        scraper_cls = PageScraper
    scraper = scraper_cls(true_url, tree)
    scraper.scrape()
    return Jentry(scraper, **kwargs)
    



if __name__ == '__main__':
    """Testing stuff"""
    url = [
    'http://www.indeed.ca/cmp/Mate1-Inc/jobs/Devop-Engineer-a156a3304e6193bc?sjdu=vQIlM60yK_PwYat7ToXhk-E4ENgV3fnJw6x45fMqWb1lojM6yJ0NlafcC4cBp_yEgc5kHZrkOD2NvIrrHdP2HgNJCpsGTgvMW68enfhuWXU',
    'https://www.smartrecruiters.com/Ludia/95985523-intermediate-data-analyst?idpartenaire=136'
]
    #scraper = PSindeed(url)
    entry = scrape_job_posting(url[1])
    entry.compute_score()
    print(entry.score)
    print(entry.score_hits)
    print(entry.processed_tokens)





















