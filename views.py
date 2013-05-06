from flask import render_template, request, session, flash, redirect, url_for
from . import app
from tweepy import Cursor, parsers, TweepError
from redis import InvalidResponse
import uuid
import json
import threading
import time
import pprint

PREFIX = "tweets_"

#move redis call to only once in each iteration
#Check returned value from redis
def stream_search(uuid, search_term, location, radius):
    app.logger.debug("UUID %s : Search Term: %s" % (uuid, search_term))
    try: 
        for tweets in Cursor(app.twitter_api.search, q=search_term, rpp=90).pages():
            if len(tweets.get('results')) == 0 and tweets.get('page') == 1:
                app.logger.debug("UUID %s: ZERO Results" % (uuid, ))
                app.redis.sadd("".join((PREFIX, uuid)), "No Results found")
                break
            elif len(tweets.get('results')) == 0:
                app.logger.debug("No more results")
                break
            else:
                for tweet in tweets.get('results'):
                    try:
                        app.redis.sadd("".join((PREFIX, uuid)), tweet)
                        app.logger.debug("adding")
                    except InvalidResponse:
                        app.logger.debug("Invalid redis response")
                        break
        app.logger.debug("UUID %s: Completed" % (uuid,)) 

    except TweepError:
        app.redis.sadd("".join((uuid, PREFIX)),  "Invalid Query")
        app.logger.debug("TweepError, Invalid Query")


@app.route("/api/search", methods=["GET"])
def api_search():
    print request.args
    try:
        terms = request.args["q"]
    except KeyError:
        return json.dumps({"errors":[{"message":"No search terms provided","code":400}]})
    try:
        geocode = request.args["geocode"]
        print request.args["geocode"]
    except KeyError:
        pass

    return terms




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
    return render_template("get_test.html")

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
    return render_template("app.html")

