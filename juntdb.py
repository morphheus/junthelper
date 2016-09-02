#!/usr/bin/env python
"""Simple and easy way to shove data into a single SQLite table."""

import numpy as np
import time
import sqlite3
import io
import inspect
import types


# Default values
DEF_TABLE = 'joblist'
DEF_DB = 'juntdb.sqlite'
DEF_ASSOC_TABLE = 'type_assoc'

__PRIMARY = 'date'
__PRIMARY_TYPE = 'INTEGER'


#---------------------------
def build_timestamp_id():
    """Builds a timestamp from the local clock"""
    now = time.time()
    localtime = time.localtime(now)
    tstr = time.strftime('%Y%m%d%H%M%S', localtime)
    msstr = "%03d"%((now%1)*1000)
    return tstr + msstr

def pprint_date(date):
    """Pretty prints the dateid"""
    datestr = str(date)

    tmp = np.array([0,4,2,2,2,2,2,3]).cumsum() # Array of slice notation endpoints
    slicelst = [slice(tmp[k],tmp[k+1]) for k in range(len(tmp)-1)]
    part = [datestr[x] for x in slicelst]
    part.reverse()

    msg = 'dbase ID: ' + part.pop() + '/' + part.pop() + '/' + part.pop() + ' ' + \
          part.pop() + 'h' + part.pop() + 'm' + part.pop() + '.' +  part.pop() + 's'
    print(msg)

#---------------------
def adapt_array(arr):
    """
    http://stackoverflow.com/a/31312102/190597 (SoulNibbler)
    """
    out = io.BytesIO()
    np.save(out, arr)
    out.seek(0)
    return sqlite3.Binary(out.read())

def adapt_list(lst):
    bin_list = bytes(repr(lst), 'ascii')
    return sqlite3.Binary(bin_list)

def adapt_dict(dct):
    bin_list = bytes(repr(fct), 'ascii')
    return sqlite3.Binary(bin_list)

def adapt_bool(boolean):
    if boolean:
        return 1
    else:
        return 0

def adapt_float64(number):
    return float(number)

def adapt_function(fct):
    fct_str = inspect.getmodule(fct).__name__ + '.' + fct.__name__
    return fct_str


#----------------------
def convert_array(text):
    out = io.BytesIO(text)
    out.seek(0)
    return np.load(out)

def convert_list(text):
    return(eval(text))

def convert_dict(text):
    return exec(text)

def convert_bool(boolean):
    if boolean == b'1':
        return True
    else:
        return False

def convert_float64(number):
    return np.float64(number)

def convert_function(text):
    return text.decode("utf-8")

#----------------------
def connect(dbase_file=DEF_DB):
    sqlite3.register_adapter(np.ndarray, adapt_array)
    sqlite3.register_adapter(list, adapt_list)
    sqlite3.register_adapter(dict, adapt_dict)
    sqlite3.register_adapter(bool, adapt_bool)
    sqlite3.register_adapter(np.float64, adapt_float64)
    sqlite3.register_adapter(types.FunctionType, adapt_function)

    sqlite3.register_converter("ARRAY", convert_array)
    sqlite3.register_converter("LIST", convert_list)
    sqlite3.register_converter("DICT", convert_dict)
    sqlite3.register_converter("BOOL", convert_bool)
    sqlite3.register_converter("FLOAT64", convert_float64)
    sqlite3.register_converter("FUNCTION", convert_function)

    conn = sqlite3.connect(dbase_file, detect_types=sqlite3.PARSE_DECLTYPES)
    return conn

def clear_table(tn=DEF_TABLE, dbase_file=DEF_DB, conn=False):
    close_conn = False
    if conn == False: 
        conn = connect(dbase_file)
        closeconn = True

    field_name = __PRIMARY
    field_type = __PRIMARY_TYPE
    c = conn.cursor()

    c.execute('DROP TABLE '+tn)
    c.execute('CREATE TABLE {tn} ({fn} {ft} PRIMARY KEY)'\
              .format(tn=tn, fn=field_name, ft=field_type))
    conn.commit()

    if close_conn:
        conn.close()

def init(dbase_file=DEF_DB, table_name=DEF_TABLE):
    conn = sqlite3.connect(dbase_file)
    c = conn.cursor()

    field_name = __PRIMARY
    field_type = __PRIMARY_TYPE
    
    #Initiate the default table, usually sim_result
    c.execute('CREATE TABLE {tn} ({fn} {ft} PRIMARY KEY)'\
              .format(tn=table_name, fn=field_name, ft=field_type))



    type_assoc = {\
                  'int':'INTEGER',\
                  'bool':'BOOL',\
                  'str':'TEXT',\
                  'ndarray':'ARRAY',\
                  'float':'REAL',\
                  'float64':'FLOAT64',\
                  'list':'LIST',\
                  'dict':'DICT',\
                  'function':'FUNCTION'\
             }
    
    c.execute("CREATE TABLE {} (ptype TEXT PRIMARY KEY, stype TEXT)"\
              .format(DEF_ASSOC_TABLE))


    for key, val in type_assoc.items():
        c.execute("INSERT INTO {} (ptype, stype)VALUES(?,?)".\
                  format(DEF_ASSOC_TABLE), [key, val])

    
    
    conn.commit()
    conn.close()

def get_type_assoc(conn, tn_assoc=DEF_ASSOC_TABLE):
    c = conn.cursor()
    cursor = c.execute('select * from ' + tn_assoc)
    return dict(cursor.fetchall())

#-------------------------
def add(data, tn=DEF_TABLE, dbase_file=DEF_DB, conn=False, new_data=True):
    """Adds the data dictionary as one row. If new columns are added, older entries will be appropriately initiated"""
    close_conn = False
    if conn == False: 
        conn = connect(dbase_file)
        closeconn = True

    c = conn.cursor()
    cursor = c.execute('select * from ' + tn)
    dbcols = [x[0] for x in cursor.description]
    datacols = list(data.keys())
    type_assoc = get_type_assoc(conn)

    # Exceptions in input data dict
    if not __PRIMARY in datacols:
        raise AttributeError('The data dict is missing the ' + __PRIMARY + ' ID (Primary attribute)')
    elif len(str(data[__PRIMARY])) != len(str(build_timestamp_id())):
        raise ValueError("The date is of improper size. Did you use build_timestamp_id to make it?")

    # find and add nonexistant colums when necessary.
    toadd = []
    try:
        for x in datacols:
            if not x in dbcols:
                tmp = type(data[x]).__name__ # Extract python type
                toadd.append([x,type_assoc[tmp]]) # <--- [varname, sql_type]
    except KeyError as e:
        print(type_assoc)
        raise KeyError("Incompatible type "+str(e)+", type: "+str(tmp)+" for data entry '"+str(x) +"'")


    for x in toadd:
        c.execute("ALTER TABLE {tn} ADD COLUMN '{cn}' {ct}"\
                  .format(tn=tn, cn=x[0], ct=x[1]))
    

    
    # Attempt to changes data to db. Retry thrice if failure
    for k in range(4):
        try:
            conn.commit()
            break
        except Exception: 
            pass
        if k == 3:
            raise Exception('Failed to commit changes to db')


    #Actually add
    collist = []
    vallist = []
    for cn, val in data.items():
        # Convert booleans to integers
        if cn == __PRIMARY:
            continue

        if type(val) == type(dict()):
            val = list(val.items())

        collist.append(cn)
        vallist.append(val)


    def thing_that_goes_wrong():
        if new_data:
            c.execute("INSERT INTO {} ({}) VALUES ({})".format(tn, __PRIMARY, data[__PRIMARY]))
        for k in range(len(collist)):
            try:
                c.execute("UPDATE {} SET {}=(?) WHERE date={}".format(tn, collist[k], data[__PRIMARY])\
                        , (vallist[k],))
            except sqlite3.InterfaceError as e:
                raise type(e)('Error on ' + str(collist[k]) + ' with value ' + str(vallist[k]))

    #In the very rare case of collision, we pick another timestamp ID.
    done = False
    while not done:
        try:
            thing_that_goes_wrong()
            done = True
        except sqlite3.IntegrityError:
            data[__PRIMARY] = build_timestamp_id() # This should propagate to parent namespace


    # Attempt to commit data to db. Retry twice if failure
    for k in range(4):
        try:
            conn.commit()
            break
        except Exception: 
            pass
        if k == 3:
            raise Exception('Failed to commit changes to db')


    if close_conn:
        conn.close()

def del_rows(dates, tn=DEF_TABLE, dbase_file=DEF_DB, conn=False):
    """Deletes the rows matching the dates"""
    close_conn = False
    if conn == False: 
        conn = connect(dbase_file)
        closeconn = True

    c = conn.cursor()

    datestring = ','.join([str(x) for x in dates])
    string = "DELETE FROM " + tn + " WHERE date in (" + str(datestring) + ")"
    c.execute(string)
    conn.commit()
    
    if close_conn:
        conn.close()

def vacuum(tn=DEF_TABLE, dbase_file=DEF_DB, conn=False):
    """Vacuums the database"""
    close_conn = False
    if conn == False: 
        conn = connect(dbase_file)
        closeconn = True

    c = conn.cursor()
    string = "VACUUM"
    c.execute(string)
    conn.commit()
    
    if close_conn:
        conn.close()


#--------------------
# FETCHING FUNCTIONS
#--------------------

#------------------------
def fetch_jentries(input_dates, tn=DEF_TABLE, dbase_file=DEF_DB, conn=False):
    """Fetches a single, whole entry in table, and converts it to a Jentry
    Input
    dates: date or list of dates of the entries to grab from the db
    """
    # This allows is to passs a connection instead of always opening a new one.
    close_conn = False
    if conn == False: 
        conn = connect(dbase_file)
        closeconn = True

    if isinstance(dates, int):
        dates = [input_dates]
    elif isinstance(dates, (list,tuple)):
        dates = input_dates
    else:
        raise ValueError("Expected an int or a list of ints")

    string = "SELECT "+colstring+" FROM "+tn+" WHERE date BETWEEN "+str(lo)+" AND "+str(hi)
    
    
    if close_conn:
        conn.close()

    return output

def fetch_matching(entry_dict, collist=None, tn=DEF_TABLE, dbase_file=DEF_DB, conn=False, get_data=True):
    """Fetches the rows that matches the entry dict.
    If get_data = False, then it only outputs the dates (not the full row): """

    close_conn = False
    if conn == False: 
        conn = connect(dbase_file)
        closeconn = True

    c = conn.cursor()

    # Determine coluns to get
    if collist is None:
        colstring = '*'
    elif len(collist)==1:
        colstring = collist[0]
    else:
        colstring = ','.join(collist)

    # Build query string
    if get_data:
        string = "SELECT " + colstring + " FROM " + tn + " WHERE " 
    else:
        string = "SELECT date FROM " + tn + " WHERE " 



    # Build the execute string and data list
    data_list = []
    string += "("
    for key, val in list(entry_dict.items()):
        if len(val)==1:
            string += key + " in ('" + str(val[0]) + "')"
        else:
            string += key + " in " + str(tuple(val)) + ""
        string += " AND "
    string = string[:-5]
    string += ")"

    cursor = c.execute(string)

    
    if close_conn:
        conn.close()

    return cursor.fetchall()

def fetchone(date, column , tn=DEF_TABLE, dbase_file=DEF_DB, conn=False):
    return fetch_cols(date, [column] , tn=tn, dbase_file=dbase_file, conn=conn)[0]

def fetch_range(dates, collist , tn=DEF_TABLE, dbase_file=DEF_DB, conn=False):
    """Fetches the columns corresponding to the list of dates"""
    close_conn = False
    if conn == False: 
        conn = connect(dbase_file)
        closeconn = True

    c = conn.cursor()

    if collist is None:
        colstring = '*'
    elif len(collist)==1:
        colstring = collist[0]
    else:
        colstring = ','.join(collist)


    if len(dates) != 2:
        raise ValueError('Expected the first argument to be an iterable of length 2')
    
    lo = dates[0]
    hi = dates[1]
    string = "SELECT "+colstring+" FROM "+tn+" WHERE date BETWEEN "+str(lo)+" AND "+str(hi)
    cursor = c.execute(string)

    output = cursor.fetchall()

    
    if close_conn:
        conn.close()

    if len(output[0])==1:
        output = [x[0] for x in output]

    return output

def fetch_cols(date, collist , tn=DEF_TABLE, dbase_file=DEF_DB, conn=False):
    """Fetches the columns in collist"""
    close_conn = False
    if conn == False: 
        conn = connect(dbase_file)
        closeconn = True

    c = conn.cursor()

    colstring = ','.join(collist)
    string = "SELECT " + colstring + " FROM " + tn + " WHERE date = " + str(date)
    c.execute(string)
    
    if close_conn:
        conn.close()

    return c.fetchall()[0]

def fetch_last_n(n, collist=None, asdict=False, tn=DEF_TABLE, dbase_file=DEF_DB, conn=False):
    """Fetches the n most recent entries in the table"""
    close_conn = False
    if conn == False: 
        conn = connect(dbase_file)
        closeconn = True

    c = conn.cursor()

    if collist is None:
        colstring = '*'
    else:
        colstring = 'date'
        tmp = ','.join(collist)
        if tmp:
            colstring += ',' + tmp
    
    string = "SELECT " + colstring + " FROM " + tn + " ORDER BY date DESC LIMIT " + str(n)
    cursor = c.execute(string)

    if not asdict:
        output = cursor.fetchall()
    else:
        colname = [ d[0] for d in cursor.description ]
        output = [ dict(zip(colname, r)) for r in cursor.fetchall() ]

    
    if close_conn:
        conn.close()

    return output

def fetch_last_n_dates(n, **kwargs):
    """Fetches the last n dates"""
    db_out = fetch_last_n(n, [''])
    return [k[0] for k in db_out]

def fetch_dates(dates, tn=DEF_TABLE, dbase_file=DEF_DB, conn=False):
    """Grabs all the dates that are between the specified dates tuple (inclusively)"""
    if len(dates) != 2:
        raise Exception('Expected length 2 input')
    return fetch_range(sorted(dates), ['date'], tn=tn, dbase_file=dbase_file, conn=conn)



if __name__ == '__main__':
    print('hallo')
