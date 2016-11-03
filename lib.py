#!/usr/bin/env python
"""Various routines to interface with junthelper"""

import juntdb
import webscraper as webs
import webbrowser
import logging
from pagescraper import Jentry





def exec_crawl(input_query, max_age, location):
    """Crawls the job aggregation websites job postings that matches the input parameters
    input_query:  string or list of strings to search in crawled website
    max_age:      maximum age (in days) of the job postings to save to disk
    location:     string of the city or other geographical location to search for
    """

    if type(input_query) != type(list()):
        querylist = [input_query]
    else:
        querylist = input_query

    input_list = []
    for query in querylist: 
        input_list += [
                (webs.SpiderIndeedCa, (query,), {'max_age':max_age, 'location':location}),
                (webs.SpiderCareerjetCa, (query,), {'max_age':max_age, 'location':location})
                ]
    webs.crawl_many(input_list)

def fetch_scored_jentries(min_score, filter_viewed=True, filter_dead=True, conn=False):
    """Fetches the high scoring entries
    min_score:   minimum score to fetch
    is_unviewed: only fetch unviewed entries. If false, disregards the "viewed" field in juntdb
    is_alive:    only fetch non-dead entries. If false, disregards the "dead" field in juntdb

    returns: list of sqlite rows matching the input parameters"""
    close_conn = False
    if conn == False: 
        conn = juntdb.connect()
        closeconn = True

    c = conn.cursor()

    # Build query string
    query = "SELECT * FROM " + juntdb.DEF_TABLE + " WHERE (score >= "+ str(min_score)
    if filter_viewed: query += ' AND viewed=0 '
    if filter_dead:   query += ' AND dead=0 '
    query += ')'

    cursor = c.execute(query)
    
    if close_conn:
        conn.close()

    return row2jentry(cursor.fetchall())

def sort_by_attribute(lst, attribute):
    """Sort the list of namedtuples by the specified attibute
    attribute: string of the sorting attribute"""
    if len(lst) > 1:
        sorting_list = sorted([(x.__dict__[attribute], x) for x in lst], key=lambda x: x[0])
        _, sorted_namedtuples = zip(*sorting_list)
        return list(sorted_namedtuples)
    else:
        return lst

def score_db(conn=False):
    """Scores all unscored entries in db
    conn: sqlite connection object to use. If False, a new connection is made"""
    # TODO: this is a really inefficient way to score
    # it typecasts the sqlite output to a Jentry, then scores that, instead of scoring the sqlite row directly
    close_conn = False
    if conn == False: 
        conn = juntdb.connect()
        closeconn = True

    c = conn.cursor()
    string = "SELECT * FROM " + juntdb.DEF_TABLE + " WHERE (score IS NULL AND dead=0)"
    c.execute(string)
    jentries = row2jentry(c.fetchall())
    if not jentries:
        print('No entries to score')
    else:
        print('Scoring ' + str(len(jentries))  +' job postings')

    for jentry in jentries:
        jentry.compute_score()
        jentry.write_db(conn)

    if close_conn:
        conn.close()

def row2jentry(data):
    """Converts the output of sqlite into Jentry objects
    data:  iterable of juntdb row outputs
    
    returns: list of Jentry object built from the input"""
    return [Jentry(dict(zip(['date'] + juntdb.DEF_COL_NAMES, x))) for x in data]

def get_sensible_jentries(min_score, sorting='score', disp=True):
    """Output to terminal a list of Jentry objects
    min_score:  minumim score of Jentry to display
    sorting:    sort the output by the specified attribute
    disp:       if true, prints the Jentry objects to terminal
    
    Returns a list of Jentry objects"""

    jentries = fetch_scored_jentries(min_score)
    sorted_jentries = sort_by_attribute(jentries, sorting)
    sorted_jentries.reverse()

    dprint = lambda x : print(x) if disp else None

    max_score_len = 10
    tmp = 'score'
    remaining_spaces = lambda x: ' '*(max_score_len + 2 - len(x))
    dprint(tmp + remaining_spaces(tmp) + 'URL')
    for jentry in sorted_jentries:
        str_score = str(jentry.score)
        if len(str_score) > max_score_len:
            str_score = str_score[:max_score_len-1]
        dprint( str_score + remaining_spaces(str_score) + jentry.url)

    return sorted_jentries

def open_in_browser(jentries, mark_as_viewed=True):
    """Opens the jentries in browser
    jentries:       iterable of Jentry objects
    mark_as_viewed: if true, marks the Jentry as viewed in the db file"""
    conn = juntdb.connect() 
    for jentry in jentries:
        webbrowser.open(jentry.url)
        if mark_as_viewed:
            jentry.viewed = True
            jentry.write_db()
    conn.close()

