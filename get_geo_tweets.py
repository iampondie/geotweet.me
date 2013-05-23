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

class TwitterRecorder(StreamListener):
    def __init__(self):
        self.total = 0 #Read tweet db size
        models.connection.geo_tweet_me.stream_tweets.create_index([('geo.coordinates', pymongo.GEO2D), ('created_at', 1)])


    def to_datetime(self, value):
        #return datetime object from created_at sting
        return datetime.datetime.fromtimestamp(int(time.mktime(parsedate(value))))  


    def handle_coordinates(self, data):
        json_data = json.loads(data)
        if json_data.get('geo'):
            needed_data = {} 
            for key, value in models.Tweet.structure.iteritems():
                if key == "created_at":
                    needed_data[key] = self.to_datetime(json_data.get(key))
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


out = TwitterRecorder()
consumer_key="JZsM9vWaCoxA0ERi6nszQ"
consumer_secret="O2jQADMGmFHxxQQutEuzMXNlX1XJiVfVhV2pSGykl4"
access_token="245598959-GvIQR0S6f33EtZLqrpndBXdQHE8goTsNUEf3swo"
access_token_secret="qNOxGgtsx47L5FevMQvXrwlamTAQtqjh5vI8lud8S0"
auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
auth.set_access_token(access_token, access_token_secret)

api = tweepy.API(auth)
print api.me().name

#temp to get index created


stream = tweepy.Stream(auth, out)
stream.sample()

