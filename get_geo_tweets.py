#!/usr/bin/env python2
import datetime
import  time
from email.utils import parsedate
import json, sys
import tweepy
from tweepy.streaming import StreamListener
from mongokit import *
import models
import pymongo
import settings
from tweepy import TweepError

class TwitterRecorder(StreamListener):
    def __init__(self):
        self.total = 0 #Read tweet db size
        print pymongo.version
        models.connection.geo_tweet_me.stream_tweets.create_index([
            ('geo.coordinates', pymongo.GEO2D), 
            ('created_at', 1),
        ])
        models.connection.geo_tweet_me.stream_tweets.create_index([
        ('text','text'),
        ])

    def to_datetime(self, value):
        #return datetime object from created_at string
        return datetime.datetime.fromtimestamp(int(time.mktime(parsedate(value))))  

    def handle_coordinates(self, data):
        json_data = json.loads(data)
        #we only want tweets, that are geotagged and english
        if json_data.get('geo') and json_data.get('lang') == 'en':
            needed_data = {} 
            for key, value in models.Tweet.structure.iteritems():
                if key == "created_at":
                    needed_data[key] = self.to_datetime(json_data.get(key))
                elif key == "geotweetme":
                    needed_data[key] = {}
                    needed_data[key]['active'] = False
                elif isinstance(value, dict):
                    needed_data[key] = {}
                    for _key, _value in value.iteritems():
                        if _key == "created_at":
                            needed_data[key][_key] = self.to_datetime(json_data.get(key).get(_key))
                        elif isinstance(_value, list):
                            _list = []
                            for x in json_data.get(key).get(_key):
                                _list.append(x)
                            needed_data[key][_key] = _list
                        else:
                            needed_data[key][_key] = json_data.get(key).get(_key)
                else:
                    needed_data[key] = json_data.get(key)

            #user logger
            new_tweet = models.connection.Tweet(needed_data)
            new_tweet.save()
            print "Added Tweet - total: %s" % self.total
            self.total += 1

    def on_data(self, data):
        self.handle_coordinates(data)
        return True
    
    def on_error(self, status):
        print "ERROR: %s" % str(status)

print settings.CONSUMER_KEY
print settings.CONSUMER_SECRET
print settings.ACCESS_TOKEN
print settings.ACCESS_TOKEN_SECRET

out = TwitterRecorder()
auth = tweepy.OAuthHandler(settings.CONSUMER_KEY, settings.CONSUMER_SECRET)
auth.set_access_token(settings.ACCESS_TOKEN, settings.ACCESS_TOKEN_SECRET)

try:
    api = tweepy.API(auth)
#   print api.me().name
except TweepError as e:
    print e
    sys.exit()

api = tweepy.API(auth)
stream = tweepy.Stream(auth, out)
stream.sample()

