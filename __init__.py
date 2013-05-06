from flask import Flask, send_from_directory, render_template, redirect, url_for
from . import settings
import tweepy, redis
from tweepy import parsers
import logging

FORMAT = "%(asctime)-15s %(levelname)s %(name)-8s %(message)s"
logging.basicConfig(format=FORMAT, level=logging.DEBUG)

logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config.from_object(settings)

auth = tweepy.OAuthHandler(app.config.get("CONSUMER_KEY"), app.config.get("CONSUMER_SECRET"))
auth.set_access_token(app.config.get("ACCESS_TOKEN"), app.config.get("ACCESS_TOKEN_SECRET"))

app.twitter_api = tweepy.API(auth, parser=parsers.JSONParser())
app.redis = redis.StrictRedis(host=app.config.get("REDIS_HOST"), port=app.config.get("REDIS_PORT"))

#Todo
#Set correct redis values and add prefixs to config

import views
