#!/usr/bin/env python
"""Various routines to control junthelper"""

import juntdb
import viewer
from pagescraper import Jentry






def fetch_scored_jentries(min_score, filter_viewed=True, filter_dead=True, conn=False):
    """Fetches the high scoring entries
    min_score:   minimum score to fetch
    is_unviewed: only fetch unviewed entries. If false, disregards the "viewed" field in juntdb
    is_alive:    only fetch non-dead entries. If false, disregards the "dead" field in juntdb
    """
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
        sorting_list = [(x.__dict__[attribute], x) for x in lst]
        sorting_list.sort()
        _, sorted_namedtuples = zip(*sorting_list)
        return list(sorted_namedtuples)
    else:
        return lst


def score_db(conn=False):
    """Processes all unscored entries in db"""
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

    for jentry in jentries:
        jentry.compute_score()
        jentry.write_db(conn)

    if close_conn:
        conn.close()

def row2jentry(data):
    """Converts the output of the juntdb into Jentry objects"""
    return [Jentry(dict(zip(['date'] + juntdb.DEF_COL_NAMES, x))) for x in data]

def print_sensible_jentries(min_score, sorting='score'):
    """Output to terminal the sensible entries that the user should apply to, according to min_score"""
    jentries = fetch_scored_jentries(min_score)
    sorted_jentries = sort_by_attribute(jentries, sorting)
    sorted_jentries.reverse()

    max_score_len = 10
    tmp = 'score'
    remaining_spaces = lambda x: ' '*(max_score_len + 2 - len(x))
    print(tmp + remaining_spaces(tmp) + 'URL')
    for jentry in sorted_jentries:
        str_score = str(jentry.score)
        if len(str_score) > max_score_len:
            str_score = str_score[:max_score_len-1]
        print( str_score + remaining_spaces(str_score) + jentry.url)


if __name__ == '__main__':
    print_sensible_jentries(0)

