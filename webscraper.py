#!/usr/bin/env python
"""Search engine scraper"""

import scrapy
import logging
import sys
import traceback
from scrapy.utils.log import configure_logging
from scrapy.crawler import CrawlerProcess
from scrapy.settings import Settings
from pydispatch import dispatcher
from datetime import datetime

import juntdb
from pagescraper import scrape_job_posting



class SpiderIndeedCa(scrapy.Spider):
    """Job search aggregator for Indeed.ca"""
    name = 'indeed.ca'
    main_url_prefix = 'http://www.indeed.ca'
    search_url_prefix = '/jobs?'
    get_request = ['as_and=', '&as_phr=', '&as_any=', '&as_not=', '&as_ttl=', '&as_cmp=', '&jt=all', '&st=', '&salary=', '&radius=50',  '&l=','&fromage=', '&limit=', '&sort=date', '&psf=advsrch' 
            ]
    pagination_finish_text = 'Next\xa0»'

    def __init__(self, match_all, match_any='', location='Montréal%2C+QC', views_per_page=20 ,max_age=15):
        """
        match_all:      search for all these words in a single page
        location:       string containing the desired city in which the shearch should be done
        viwes_per_page: total number of job postings per result page
        max_age:        integer, maximum age in days of the job posting. Values accepted: 1, 3, 7, 15"""
        query = self.main_url_prefix + self.search_url_prefix + self.get_request[0] + match_all.replace(' ', '+')
        query += self.get_request[1] + match_any.replace(' ', '+')
        query += ''.join(self.get_request[2:10])
        query += self.get_request[10] + location
        query += self.get_request[11] + str(max_age)
        query += self.get_request[12] + str(views_per_page)
        query += ''.join(self.get_request[-2:])
        self.location = location
        self.name = 'IndeedCa' + location
        self.start_urls = [query]
        self.search_page_index = 0
        self.jentries = []
        dispatcher.connect(self.quit, scrapy.signals.spider_closed)
        logging.log(21, 'Scraping ' + self.name)

    def parse(self, response):
        """Parses all the job postings present in a result page page. Proceeds until there are no more pages or the age limit is reached"""
        # Grab all the job posting urls
        for sel in response.xpath('//h2[@class="jobtitle"]'):
            posting_url, job_location = self.get_selection_info(sel)
            try:
                self.jentries.append(scrape_job_posting(posting_url, loc=job_location))
            except Exception:
                logging.error("Unexpected error with website:" + posting_url)
                traceback.print_exc()
        # Goto next page up to the end of the pagination div
        try:
            url, url_text = self.get_pagination_info(sel, response)
            if url_text == self.pagination_finish_text:
                self.search_page_index += 1
                logging.log(21, self.name + 'Processing page ' + str(self.search_page_index+1))
                yield scrapy.Request(url)
        except IndexError:
            pass

    def get_selection_info(self, sel):
        """Posting url for indeed.ca. Outputs the job post url and the job location"""
        posting_url = self.main_url_prefix + sel.xpath('a/@href').extract()[0]
        job_location = sel.xpath('..//span[@itemprop="addressLocality"]/text()').extract()[0]
        return posting_url, job_location
    
    def get_pagination_info(self, sel, response):
        """Pagination info for indeed.ca. Outputs the rightmost pagination url and its text"""
        rightmost_a = response.xpath('//div[@class="pagination"]/a')[-1]
        a_text = rightmost_a.xpath('span//text()').extract()[0]
        url = response.urljoin(rightmost_a.xpath('@href').extract()[0])
        return url, a_text
    
    def quit(self):
        """Executed at the end of the crawl. Add all non-dupplicates to db"""
        # Add all Jentr to db
        logging.log(21, self.name + ' finished after ' + str(self.search_page_index) + 'pages')

        conn = juntdb.connect()
        try:
            true_urls = list(list(zip(* juntdb.fetch_last_n(99999, collist=['url'], conn=conn)))[1])
        except IndexError:
            logging.info('Detected empty database; assuming there are no pre-existing URLS')
            true_urls = []

        dupp_count = 0
        for jentry in self.jentries:
            if jentry.url in true_urls:
                dupp_count += 1
                continue
            true_urls.append(jentry.url)
            jentry.write_db(conn)

        if dupp_count:
            logging.log(21, str(dupp_count) + ' dupplicates')
        conn.close()

class SpiderCareerjetCa(SpiderIndeedCa):
    """Web search aggregator for careerjet.ca"""

    main_url_prefix = 'http://www.careerjet.ca'
    search_url_prefix = '/wsearch/jobs?'
    get_request = ['s=',  '&l=', '&sort=date']

    def __init__(self, match_all, location='Montreal%2C+QC', max_age=3):
        """
        match_all:  search for all these words in a single page
        location:   string containing the desired city in which the shearch should be done
        max_aage:   integer, maximum time (in days) the job posting was posted
        """
        query = self.main_url_prefix + self.search_url_prefix + self.get_request[0] + match_all.replace(' ', '+')
        query += self.get_request[1] + location
        query += ''.join(self.get_request[2:])
        self.name = 'CareerjetCa' + location
        self.start_urls = [query]
        self.jentries = []
        self.max_age = max_age
        self.search_page_index = 0
        dispatcher.connect(self.quit, scrapy.signals.spider_closed)
        logging.log(21, 'Scraping ' + self.name)

    def parse(self, response):
        """Parses all the job postings present in a result page page. Proceeds until there are no more pages or the age limit is reached"""
        # Grab all the job posting urls
        reached_max_age = False
        for sel in response.xpath('//div[@class="job"]'):
            # Find if job too old
            full_date = sel.xpath('p//span[@class="date_compact"]/script/text()').extract()[0][19:-3]
            if date_age(full_date) > self.max_age:
                reached_max_age = True
                break
            posting_url = response.urljoin(sel.xpath('h2/a/@href').extract()[0])
            job_location = sel.xpath('p//a[@class="locations_compact"]/text()').extract()[0]
            try:
                self.jentries.append(scrape_job_posting(posting_url, loc=job_location))
            except Exception:
                logging.error("Unexpected error with website:" + posting_url)
                traceback.print_exc()
                

        # Goto next page up to the end of the pagination div
        try:
            rightmost_a = response.xpath('//p[@class="browse"]/a')[-1]
            a_text = rightmost_a.xpath('text()').extract()[0]
            url = response.urljoin(rightmost_a.xpath('@href').extract()[0])
            if a_text == ' >>' and not reached_max_age:
                self.search_page_index += 1
                logging.log(21, self.name + 'Processing page ' + str(self.search_page_index+1))
                yield scrapy.Request(url)
        except IndexError:
            pass

def crawl_one(SpiderCls, *args, **kwargs):
    """Simple wrapper to crawl the desired website"""
    crawler = CrawlerProcess({
       'USER_AGENT': 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1)',
       'LOG_LEVEL':'WARNING'
    })
    crawler.crawl(SpiderCls, *args, **kwargs)
    crawler.start() # the script will block here until the crawling is finished

def crawl_many(input_list):
    """Simple wrapper to crawl the desired website"""
    crawler = CrawlerProcess({
       'USER_AGENT': 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1)',
       'LOG_LEVEL':logging.INFO
    })
    for spidercls, args, kwargs in input_list:
        crawler.crawl(spidercls, *args, **kwargs)
    crawler.start() # the script will block here until the crawling is finished

def date_age(datestr):
    """Input: date string
    Output: age with respect to current date. Max 1 year diff"""
    year = datetime.today().year
    yday_today =  datetime.today().timetuple().tm_yday
    yday_input =  datetime.strptime(str(year) + ' ' + datestr, '%Y %B %d').timetuple().tm_yday
    diff = yday_today -  yday_input
    if diff < 0:
        diff += 365
        # TODO: leap years. If the span between input & today contains feb
        # in a leap year, then add 1
    return diff

    

if __name__ == '__main__':
    pass
    #crawl(SpiderIndeedCa, 'data python analyst panda')


    input_list = [
            #(SpiderIndeedCa, ('data python analyst panda',), {})
            (SpiderCareerjetCa, ('data python',), {})
            ]
    crawl_many(input_list)




























