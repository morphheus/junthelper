#!/usr/bin/env python
"""Single webpage scraper"""

import scrapy
import logging
from scrapy.utils.log import configure_logging
from scrapy.crawler import CrawlerProcess
from scrapy.settings import Settings
from pydispatch import dispatcher

import juntdb
from pagescraper import scrape_job_posting

logger = logging.getLogger() # New local logger
handler = logging.StreamHandler()
handler.setLevel(21)
formatter = logging.Formatter('[%(asctime)s %(name)s][%(levelname)-8s] %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


class SpiderIndeedCa(scrapy.Spider):
    """Web search aggregator for Indeed.ca"""

    name = 'indeed.ca'
    main_url_prefix = 'http://www.indeed.ca'
    search_url_prefix = '/jobs?'
    get_request = ['as_and=', '&as_phr=', '&as_any=', '&as_not=', '&as_ttl=', '&as_cmp=', '&jt=all', '&st=', '&salary=', '&radius=50',  '&l=','&fromage=', '&limit=', '&sort=date', '&psf=advsrch' 
            ]

    def __init__(self, match_all, match_any='', location='Montr%C3%A9al%2C+QC', views_per_page=20 ,max_age=15):
        """
        match_all:  search for all these words in a single page
        match_any:  search for any of these words in a single pasge
        max_age:    integer, maximum age in days of the job posting. Values accepted: 1, 3, 7, 15"""
        query = self.main_url_prefix + self.search_url_prefix + self.get_request[0] + match_all.replace(' ', '+')
        query += self.get_request[1] + match_any.replace(' ', '+')
        query += ''.join(self.get_request[2:10])
        query += self.get_request[10] + location
        query += self.get_request[11] + str(max_age)
        query += self.get_request[12] + str(views_per_page)
        query += ''.join(self.get_request[-2:])
        self.start_urls = [query]
        self.search_page_index = 1
        self.jentries = []
        dispatcher.connect(self.quit, scrapy.signals.spider_closed)
        logger.log(21, 'Scraping ' + self.name + ' ' + location)
    def parse(self, response):
        """Parses the responses"""
        # Grab all the job posting urls
        for sel in response.xpath('//h2[@class="jobtitle"]'):
            posting_url = self.main_url_prefix + sel.xpath('a/@href').extract()[0]
            self.jentries.append(scrape_job_posting(posting_url))

        # Goto next page up to the end of the pagination div
        pagination_hrefs = response.xpath('//div[@class="pagination"]').xpath('a/@href').extract()
        if self.search_page_index < len(pagination_hrefs):
            next_link = pagination_hrefs[self.search_page_index]
            self.search_page_index += 1
            url = response.urljoin(next_link)
            yield scrapy.Request(url)# callback=self.parse_dir_contents)
    def quit(self):
        """Executed at the end of the crawl"""
        # Add all Jentry to db
        conn = juntdb.connect()
        true_urls =list(zip(* juntdb.fetch_last_n(99999, collist=['url'], conn=conn)))[1]
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


def crawl(SpiderCls, *args, **kwargs):
    """Simple wrapper to crawl the desired website"""
    crawler = CrawlerProcess({
       'USER_AGENT': 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1)',
       'LOG_LEVEL':'WARNING'
    })
    crawler.crawl(SpiderCls, *args, **kwargs)
    crawler.start() # the script will block here until the crawling is finished



if __name__ == '__main__':
    pass
    crawl(SpiderIndeedCa, 'data python analyst panda')


























