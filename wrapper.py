#!/usr/bin/env python


import lib



max_age = 7
#location = 'Toronto%2C+ON'
location = 'Montreal%2C+QC'
#location = 'Quebec'

#search_strings = ['data python', 'software', 'machine learning']
search_strings = ['python', 'machine learning']

#lib.exec_crawl(search_strings, max_age=max_age, location=location); lib.score_db()

#lib.score_db()
jentries = lib.get_sensible_jentries(20)
lib.open_in_browser(jentries, True)


































































