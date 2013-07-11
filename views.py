from flask import render_template, request, session, flash, redirect, url_for, jsonify, Response, make_response
from werkzeug import secure_filename
from . import app, db
from tweepy import Cursor, parsers, TweepError
import uuid
import os
import json
import threading
import time
import pprint
from datetime import datetime, timedelta
import dateutil.parser
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


@app.route("/", methods=["GET", "POST"])
def index_search():
    if request.method == 'GET':
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
    elif request.method == 'POST':
        _file = request.files['file']
        if not _file:
            flash("No data in upload", "error")
            return render_template("search.html")
        
        filename = secure_filename(_file.filename)
        _file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        #Handling twapperkeeper - expect {"archive_info" at begining of file
        try:
            with open(os.path.join(app.config['UPLOAD_FOLDER'], filename), "r") as f:
                if not f.read(15) == '{"archive_info"':
                    os.remove(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    flash("Invalid twitter data, unable to import", "error")
                    return render_template("search.html")
                f.seek(0)
                json.load(f)
        except IOError:
            flash("IOError, unable to upload", "error")
            return redirect(url_for('index_search'))
        except ValueError:
            flash("Malformed data, unable to upload", "error")
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            return redirect(url_for('index_search'))

        #Spin up thread to import data
        threading.Thread(target=import_tweets, args=(filename,)).start()
        flash("Data uploaded, importing now", "success")
        return redirect(url_for('index_search'))
    else:
        render_template("search.html")

def import_tweets(filename):
    app.logger.debug("Starting Tweet imports")
    with open(os.path.join(app.config['UPLOAD_FOLDER'], filename), "r") as f:
        _dict = json.load(f)

    terms = _dict.get("archive_info").get("keyword")

    new_search = con.Search() #init to set default values
    new_search.update({"tweets":[], "terms":[unicode(terms)]})
    new_search.save()

    tweets = []

    for tweet in _dict.get("tweets"):
        i = 0
        data = {}
        for key, val in con.Tweet.structure.iteritems():
            if key == 'created_at':
                data[key] = dateutil.parser.parse(tweet.get(key))
            elif key == 'lang':
                data[key] = u'en'
            elif key == 'id':
                data[key] = long(tweet.get(key))
            elif key == 'geo':
                if tweet.get('geo_coordinates_0') != '0' and tweet.get('geo_coordinates_1') != '0':
                    data[key] = {'type':u'Point', 'coordinates':((float(tweet.get('geo_coordinates_0'))), float(tweet.get('geo_coordinates_1')))}
                    data['geotweetme'] = {'geotagged':True, 'active':True, 'searches':[new_search['_id']]}
                else:
                    data['geotweetme'] = {'geotagged':False, 'active':True, 'searches':[new_search['_id']]}
                    data[key] = {'type':u'Point', 'coordinates':((0,0))}
            elif key == 'entities':
               data[key] = {} 
            elif key == 'user':
                data[key] = {'id':long(tweet.get('id')), 'location':u'None', 'verified':False}
            #elif key == 'geotweetme':
            #    data[key] = {'active':True, 'searches':new_search['_id']}
            else:
            #    print tweet.get(key)
                data[key] = tweet.get(key)

        new_tweet = con.Tweet(data)
        new_tweet.save()
        tweets.append(new_tweet['_id'])

    con.searches.find_and_modify({"_id":ObjectId(new_search['_id'])}, {"$set":{'tweets':tweets}})
    #con.stream_tweets.find_and_modify({"_id":_id}, {"$set": { 'geotweetme.active': True }})
    app.logger.debug("Import Completed")
    #new_search = con.Search() #init to set default values

    #new_search.update({"tweets":[], "terms":[unicode(terms)]})
    #new_search.save()


    #if search term already exists add to current, otherwise create a new
    #set tweets that are imported to geotweetme.twapperkeeper = True
    #add to search record that twapperkeeper used with created_at from timestamp
    #print _dict.get("archive_info")
    #print _dict.get("tweets")[0]


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

def inactivate_tweets(_id):
    search_object = con.Search.find_one({"_id":ObjectId(_id)})
    con.searches.remove({"_id":ObjectId(_id)})
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
    threading.Thread(target=inactivate_tweets, args=(_id,)).start()
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
    print "search"
    tweets = []
    
    terms = con.Search.find({"_id":ObjectId(_id)}, {"terms":1}).next().get('terms')

    _tweets = con.stream_tweets.find({"geotweetme.searches":{"$in":[ObjectId(_id)]}}).sort("created_at", 1)

    for tweet in _tweets: #con.searches.find({"_id":ObjectId(_id)},{"tweets":"1"}).sort("_id", 1):
        tweets.append(tweet)
    return json.dumps({'results':tweets, 'terms':terms}, default=json_util.default)

@app.route("/api/search/<_id>/date/<_from>/<_to>")
def json_date_search(_id, _from, _to):
    _tweets = []
    start = datetime.fromtimestamp(int(_from))    
    end = datetime.fromtimestamp(int(_to))

    tweets = con.stream_tweets.find({"geotweetme.searches" : {"$in": [ObjectId(_id)]}, "created_at":{"$gt":start, "$lte":end}}).sort("_id", 1)
    
    #tweets = con.searches.aggregate([{"$match":{"_id":ObjectId(_id)}}, {"$unwind":"$tweets"}, {"$match":{"created_at":{"$gte":start, "$lt":end}}}, {"$project" : {"tweets": 1}}])
    for tweet in tweets:
        _tweets.append(tweet)
    return json.dumps({'results':_tweets}, default=json_util.default)


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

