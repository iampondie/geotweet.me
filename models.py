import datetime
from . import db
from mongokit import *

connection = Connection()

@connection.register
class Tweet(Document):
    __collection__ = 'stream_tweets'
    __database__ = 'geo_tweet_me'
    use_schemaless = True
    structure = {
        'text':unicode,
        'id':int,
        'created_at': datetime.datetime, 
        'lang':unicode, #parse its a valid code (shouldbe)
        'coordinates': { 
                    'type':unicode,
                    'coordinates': (OR(float, int), OR(float, int)), 
                    },
        'geo': { 
                    'type':unicode,
                    'coordinates': (OR(float, int), OR(float, int)), 
                    },

        'entities': {
                    'hashtags':list,
                    },

        'user': {
                    'id':int,
                    'verified': bool,
                    'location':unicode,
                    'created_at':datetime.datetime,
                    },
        'geotweetme': {
                    'active':bool,
            }
        }
    indexes = [
        {
            'fields':[('created_at', INDEX_ASCENDING), ('geo.coordinates', INDEX_GEO2D)],
        },
    ]

@connection.register
class Search(Document):
    __collection__ = 'searches'
    __database__ = 'geo_tweet_me'

    structure = {
        'created_at': datetime.datetime,
        'terms': list,
        'tweets': list,
    }
    default_values = {'created_at': datetime.datetime.now}


@connection.register
class TwapperKeeper(Document):
    structure = {
        'text':unicode,
        'id':unicode,
        'geo': {
                'type':unicode,
                'coordinates':(OR(float, int), OR(float, int)),
                },
        'created_at': datetime.datetime,
    }
    indexes = [
        {
            'fields':[('created_at', INDEX_ASCENDING), ('geo.coordinates', INDEX_GEO2D)],
        },
    ]

db.register([Search, Tweet])

if __name__ == "__main__":
    d = connection.Tweet({"text":"TEXT", "id":"1213", "created_at":"12112"})
    print d
    d.validate()
    d.save()




