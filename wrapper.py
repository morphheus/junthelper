#!/usr/bin/env python


import lib

max_age = 7
#location = Toronto%2C+ON
#location = 'Montreal%2C+QC'

search_strings = ['data python', 'software', 'machine learning']

for s in search_strings:
    lib.exec_crawl(s, max_age=max_age)

#lib.exec_crawl('data python', max_age=max_age)
lib.exec_crawl('software', max_age=max_age)
#lib.exec_crawl('machine learning', max_age=max_age)
lib.score_db()

jentries = lib.get_sensible_jentries(15)
#lib.open_in_browser(jentries, True)
































































