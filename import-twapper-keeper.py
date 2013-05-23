#Dirty script to rip data from phils twapper keeper into mongo docs to be used by the UI
import _mysql as my
import datetime
from email.utils import parsedate
from mongokit import *
import models
import pymongo
import sys
import time

def num(s):
    try:
        return int(s)
    except ValueError:
        return float(s)

def to_datetime(value):
    return datetime.datetime.fromtimestamp(int(time.mktime(parsedate(value))))  

con = my.connect('localhost', 'root', '', 'yourtwapperkeeper')
#, (id needed as yourtwapper uses tables z_id)
tables = [(3, "nswfloods"), (6, "melbourne"), (7, "#melbourne"), (8, "boston"), (9, "waterton"), (10, "watertown")]

for table in tables:
    db = getattr(models.connection.yourtwapperkeeper, table[1])
    db.create_index([('geo.coordinates', pymongo.GEO2D), ('created_at', 1)])
    query = "SELECT * from z_%d" % table[0]
    con.query(("SELECT * from z_%d" % table[0]))
    result = con.use_result()
    row = result.fetch_row()
    i = 0
    while row:
        d = {}
        if row[0][9]:
            try:
                d['text'] = unicode(row[0][1])
            except UnicodeDecodeError:
                d['text'] = unicode(table[1])
            d['id'] = unicode(row[0][4])
            d['geo'] = {}
            d['geo']['type'] = unicode(row[0][9])
            d['geo']['coordinates'] = (num(row[0][10]), num(row[0][11]))
            d['created_at'] = to_datetime(row[0][12])
            t = db.TwapperKeeper(d)
            t.save()
            i += 1
        row = result.fetch_row()
        print i

