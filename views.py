from flask import render_template, request, session, flash, redirect, url_for, jsonify, Response
from . import app, db
from tweepy import Cursor, parsers, TweepError
from redis import InvalidResponse
import uuid
import json
import threading
import time
import pprint
from datetime import datetime
import requests
from bson import json_util

PREFIX = "tweets_"
app.searches = []

#TODO remove stream_search
#TODO valid app.searchs.remove()
def stream_search(uuid, search_term):
    app.logger.debug("UUID %s : Search Term: %s" % (uuid, search_term))
    try: 
        start = datetime.now()
        total_tweets = 0
        total_tweets_geo = 0
        for tweets in Cursor(app.twitter_api.search,q=search_term).pages():
            if len(tweets.get('results')) == 0 and tweets.get('page') == 1:
                app.logger.debug("UUID %s: ZERO Results" % (uuid, ))
                app.redis.sadd("".join((PREFIX, uuid)), "No Results found")
                break
            elif len(tweets.get('results')) == 0:
                app.logger.debug("No more results")
                break
            else:
                for tweet in tweets.get('results'):
                    total_tweets += 1
                    if (tweet.get('geo')):
                        total_tweets_geo += 1
                        try:
                            app.redis.sadd("".join((PREFIX, uuid)), json.dumps(tweet))
                        except InvalidResponse:
                            app.logger.debug("Invalid redis response")
                            break
        app.logger.debug("UUID %s: Completed" % (uuid,)) 
        app.logger.debug("Time Taken %s" % (str(datetime.now() - start),))
        app.logger.debug("Total Tweets %s --- Total GEO tweets %s" % (total_tweets, total_tweets_geo))
        app.searches.remove(uuid)
        app.logger.debug("removed uuid");   
    except TweepError:
        app.searches.remove(uuid)
        app.redis.sadd("".join((uuid, PREFIX)),  "Invalid Query")
        app.logger.debug("TweepError, Invalid Query")


@app.route("/api/search", methods=["GET"])
def api_search():
    print request.args
    try:
        terms = request.args["q"]
    except KeyError:
        return Response(status=400, response="No Search Term Provided")
    try:
        geocode = request.args["geocode"]
        print request.args["geocode"]
    except KeyError:
        return Response(status=400)
        pass

    session['id'] = str(uuid.uuid4())
    app.redis.lpush("searches", session.get('id'))
    app.redis.hmset(session.get('id'), 
                    {"search_terms":request.form.get("Melbourne"),
                    "uuid":session.get('id'),
                    })
    # TODO: Pass the data to redis set, load back out using session id
    print session.get('id')

    app.searches.append(session.get('id'))

    threading.Thread(target=stream_search, args=(session.get('id'),terms)).start()

    return Response(status=200, response=session.get('id')) 


#Actual API stuff
@app.route("/api/<uuid>")
def search_tweets(uuid):
    if uuid in app.searches:
        return jsonify({'results':list(app.redis.smembers("".join((PREFIX, uuid)))), 'completed':'false'})
    else:
        return jsonify({'results':list(app.redis.smembers("".join((PREFIX, uuid)))), 'completed':'true'})

#Ajax stuff
#Todo move to into seperate 'api' views and correctly use GET/POST
@app.route("/api/searches/<int:num_searches>", methods=["GET"])
def get_searchs(num_searches):
    print num_searches
    return json.dumps(app.redis.lrange("searches", 0, num_searches))

@app.route("/api/searches/all")
def all_searches():
    return json.dumps(app.redis.lrange("searches", 0, -1))

@app.route("/api/search/<string:uuid>")
def get_search(uuid):
    return json.dumps(list(app.redis.smembers("".join((PREFIX, uuid)))))

@app.route("/api/data/<string:uuid>")
def get_details(uuid):
    return json.dumps(app.redis.hgetall(uuid))
#@app.route

@app.route("/test/session")
def test_session():
    return json.dumps({"session":session.get('id', None)})

#Use wtforms 
@app.route("/")
def root():
    return render_template("map.html")

#TODO use wtforms for  validation, and move this to root.  check if its POST
@app.route("/search", methods=["POST"])
def search(): 
    session['id'] = str(uuid.uuid4())
    app.redis.lpush("searches", session.get('id'))
    app.redis.hmset(session.get('id'), 
                    {"search_terms":request.form.get("search_terms"),
                    "location":request.form.get("location"),
                    "radius":request.form.get("radius"),
                    "uuid":session.get('id'),
                    })
    threading.Thread(target=stream_search, args=(session.get('id'), 
                                                request.form.get('search_terms'),
                                                request.form.get('location'),
                                                request.form.get('radius'),)).start()
    flash("Searching Twitter")
    return redirect(url_for("root"))

@app.route("/test")
def test():
    return render_template("heat.html")


@app.route("/lat")
def search_location():
    locations = []
    for data in db.stream_tweets.find({"geo.coordinates": {"$maxDistance":10, "$near":[37, 144]}}):
        locations.append(data)
    return json.dumps(locations, default=json_util.default)


@app.route("/kapper")
def kapper():
   req = requests.get("http://www.research.iampondie.com/apiGetTweets.php?id=8&sm=&sd=&sy=&em=&ed=&ey=&o=&l=50000&from_user=&text=&lang=")
   return req.text
