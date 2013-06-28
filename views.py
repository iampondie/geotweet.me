from flask import render_template, request, session, flash, redirect, url_for, jsonify, Response, make_response
from . import app, db
from tweepy import Cursor, parsers, TweepError
import uuid
import json
import threading
import time
import pprint
from datetime import datetime, timedelta
import requests
from bson import json_util
from . import models
from mongokit import ObjectId
import shlex

#stuff for supervisor
import xmlrpclib
from xmlrpclib import ResponseError
import socket

con = app.connection.geo_tweet_me

def add_search_term(terms, search_id):
    terms_doc = con.Terms.fetch().next()
    _terms = terms_doc['terms']
    _terms.append((terms, search_id))
    terms_doc.update({"terms":_terms})
    terms_doc.save()

#@app.route("/older")
def greater_10days():
    date = datetime.now() - timedelta(10)
    #for record in db.stream_tweets.find({"created_at": {"$gt": date }}):
    db.stream_tweets.remove({"created_at": {"$gt": date }, "geotweetme":{"active": False}})

    return json.dumps(db.stream_tweets.find({"created_at": {"$gt": date }, "geotweetme":{"active":False}}).count())
    #db.posts.find({author: "Mike", created_on: {$gt: start, $lt: end}});


def complete_search(search_id, terms):
    app.logger.debug("Starting  Search with Terms: %s" % (terms))
    total_tweets = con.stream_tweets.count()
    for tweet in con.stream_tweets.text(terms, limit=total_tweets).get('results'):
        _tweet = con.Tweet.find_one({"_id":ObjectId(tweet.get('obj').get('_id'))})

        #handle for documents that don't have the latest model
        try:
            _geotweet = _tweet.get("geotweetme")
            searches = _geotweet["searches"]
        except AttributeError:
            searches = []
        except KeyError:
            searches = []
        except TypeError:
            searches = []
        searches.append(ObjectId(search_id))

        _tweet.update({"geotweetme":{"active":True, "searches":searches}})
        _tweet.save()
        #con.stream_tweets.find_and_modify({"_id":_id}, {"$set": { 'geotweetme.active': True }})
        con.searches.find_and_modify({"_id":ObjectId(search_id)}, {"$push":{"tweets":tweet}})
    app.logger.debug("Search Complete with Terms: %s" % (terms))


@app.route("/", methods=["GET"])
def index_search():
    if request.args:
        try:
            if not request.args['q']:
                flash("No search term provided", category="error")
                return redirect(url_for("index_search"))

            #lower all search terms, we lower the twitter text (PEoPLE writE RUBBish!11)
            terms = request.args['q'].lower()
            #Check that this hasnt already been searched
            if con.searches.find_one({"terms":[terms]}):
                flash("Search Already Exists", category="error")
                return redirect(url_for("index_search"))

            new_search = con.Search() #init to set default values
            new_search.update({"tweets":[], "terms":[unicode(terms)]})
            new_search.save()

            add_search_term(shlex.split(terms), new_search['_id'])

            #spin up a new thread so we don't lock the user
            threading.Thread(target=complete_search, args=(new_search['_id'],terms)).start()

            flash("Success - Search Created", category="success")
            return redirect(url_for("index_search"))
        except KeyError:
            flash("Failed - KeyError", category="error")
            return redirect(url_for("index_search"))
    else:
        return render_template("search.html")
    

#API routes, all should return JSON with a resonably similar syntax
#eg results{}
@app.route("/api/search/previous")
def previous_searches():
    searches = []
    for search in con.searches.find():
        _dict = {}
        try:
            _dict["Tweets"] = len(search['tweets'])
            _dict["Created"] = search["created_at"]
            _dict["Terms"] = search["terms"]
            _dict["_id"] = search["_id"]
        except KeyError:
            return Response(status=501, response="KeyError when building previous search results")
        searches.append(_dict)
    return json.dumps({'results':searches, 'headers':['Terms', 'Tweets', 'Created']}, default=json_util.default)


def remove_terms(_id):
    search_id = ObjectId(_id)
    terms_doc = con.Terms.fetch().next()
    terms_list = terms_doc['terms']
    for search in terms_list:
        if search[1] == search_id:
            terms_list.remove(search)
    terms_doc.update({"terms":terms_list})
    terms_doc.save()

def inactivate_tweets(search_object):
    for tweet in search_object.get("tweets"):
        try:
            _tweet = con.Tweet.find_one({"_id":ObjectId(tweet.get('obj').get('_id'))})
        except AttributeError:
            _tweet = con.Tweet.find_one({"_id":ObjectId(tweet.get('_id'))})
        #only if search list is 0/None will we inactivate it
        if not (_tweet.get('geotweetme').get('searches')):
            _tweet.update({"geotweetme":{"active":False}})
            _tweet.save()


@app.route("/api/search/<_id>/delete")
def delete_search(_id):
    remove_terms(_id)
    inactivate_tweets(con.Search.find_one({"_id":ObjectId(_id)}))
    con.searches.remove({"_id":ObjectId(_id)})
    return redirect(url_for('index_search'))

@app.route("/api/search/<_id>/json")
def json_search(_id):
    tweets = []
    filename = "".join((str(int(time.time())), "_tweets", ".json"))
    for tweet in con.searches.find({"_id":ObjectId(_id)},{"tweets":"1"}):
        tweets.append(tweet)
    return Response(json.dumps(tweets, default=json_util.default), mimetype="text/plain", headers={"Content-Disposition":"attachment;filename="+filename})

@app.route("/api/search/<_id>")
def json_search(_id):
    tweets = []
    terms = con.Search.find({"_id":ObjectId(_id)}, {"terms":1}).next().get('terms')
    for tweet in con.searches.find({"_id":ObjectId(_id)},{"tweets":"1"}).sort("_id", 1):
        tweets.append(tweet)
    return json.dumps({'results':tweets, 'terms':terms}, default=json_util.default)

@app.route("/api/search/<_id>/view")
def view_search(_id):
    pass

@app.route("/live")
def live():
    return render_template("live.html")

@app.route("/status")
def status():
    return render_template("status.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/api/status")
def get_supervisor_status():
    return json.dumps({'results':app.supervisor.supervisor.getAllProcessInfo(), 'headers':['Name', 'State', 'Description']})

@app.route("/api/tweets/total")
def get_total_tweets():
    return json.dumps({'results':con.stream_tweets.count()})

@app.route("/api/latest/tweets/<time>")
def latest_tweets(time):
    #remove +10 hours - mongo has no timezone - TODO fix this
    date = datetime.fromtimestamp(float(time)) - timedelta(0,36000)
    tweets = []
    for tweet in con.Tweet.find({"created_at":{"$gt":date }}).sort("_id",1):
        tweets.append(tweet)
    return json.dumps({"results":tweets}, default=json_util.default)


@app.route("/search/<_id>/view")
def view_search(_id):
    return render_template("view_search.html")

