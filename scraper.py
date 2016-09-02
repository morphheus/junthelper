#!/usr/bin/env python

from lxml import html
import collections
import requests
import copy
#from sklearn.feature_extraction.text import TfidfVectorizer

import juntdb as db



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



#-------------------
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
            pass
        else:
            raise Exception('Unknown input class')

    def __iter__(self):
        """Iterates over all the non-callable, non-hidden attributes"""
        for key, value in self.__dict__.items():
            if not callable(value) and not key.startswith('__'):
                yield key, value
    
    def process_bodystring(self):
        pass


    def write_db(self):
        """Stores the Jentry in the database. Creates a new db entry if necessary"""
        existing_date = db.fetch_matching({'date':self.date})
        new_data = False
        if not existing_date:
            new_data = True
        db.add(dict(self), new_data=new_data)

if __name__ == '__main__':
    #url = 'https://www.smartrecruiters.com/BehaviourInteractive/95739274-business-analyst-programmer?bid=326'
    url= 'https://www.smartrecruiters.com/Ludia/95985523-intermediate-data-analyst?idpartenaire=136'
    #url = 'http://www.indeed.ca/viewjob?jk=7bf8b6d706199bea&q=data+analyst+python&l=Montr%C3%A9al%2C+QC&tk=1arjtk3815ou79au&from=web'

    #scraper = PSindeed(url)
    scraper = PSsmartrecruiters(url)
    scraper.scrape()
    entry = Jentry(scraper)
    db.pprint_date(entry.date)
    entry.process_bodystring()
    #print(dict(entry))
    ##print(scraper.bodystring)
    #print(scraper.date)


















