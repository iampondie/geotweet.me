var searchLocked = false;
var isOn = true;
var searchHeight = "75px";
var searchWidth = "125px"
var geoTweets = new Array();

$(document).ready( function(){
    $('#searchModal').on('hidden', function () {
        console.log("Search Modal Hidden");
    })
    $('#searchModal').on('show', function () {
        console.log("Search Modal Shown");
    })

    $("#searchbar-icon").click(function() {
        $('#searchModal').modal({
            backdrop: true,
            keyboard: true,
        }, 'toggle');
    });

    //console.log($("#searchbar").width());
    $("#searchbar-icon").hover(function() {
        //var val = $("#searchbar").css("width");
        //console.log(val);
            $(this).css('cursor', 'pointer');
            $(this).addClass('hover');
        }, function() {
            $(this).css('cursor', 'pointer');
            $(this).removeClass('hover');
    });

    $("#progress").hide();
    $("#tweet-data").hide();
});

function finishedAnimation() {
    console.log("finished!!");
}

function twitter_search() {
            console.log("get_search called");
            //Validate form
            console.log($("#searchform").serializeArray());
            var searchData = $("#searchform").serializeArray();
            console.log(searchData[0].value);
            $.ajax({
                type: "GET",
                contentType: "application/json; charset=utf-8",
                url: "/api/search",
                data: {"q":searchData[0].value, "geocode":"127.001,-21.003,10km"},
                success: function (msg) {
                    console.log("search GET request completed");
                },
                statusCode: {
                    200: function(xhr) {parse_tweets(xhr);},
                    400: function() {console.log("failed")},
                }
            });
        $("#searchModal").modal('hide');
    }; 


function parse_tweets(uuid) {
    console.log("parse tweet called");
    console.log("uuid: "+ uuid);
    $("#progress").html("<p>Searching...</p>");
    $("#progress").show()
    $("#progress").addClass("twinkle");
    getTweets(uuid);
}

function load_twapper_tweets() {
    var url = $("#twapper-url").val();
    console.log(url);
    
    $.ajax({
        url: "/kapper",
        success: function(data) {
            getKapperTweets(data);
        },
        complete: function() {
            console.log("complete");
        },});
}

function getKapperTweets(data) {
    var tweetObj = $.parseJSON(data);
    for (var i = 0; i<tweetObj.tweets.length; i++) {
        if (tweetObj.tweets[i].geo_type) {

            console.log(tweetObj.tweets[i].geo_coordinates_0);
        };
        //if (tweetObj.tweets[i].get_coordinates_0 == "0 ") {
        //    console.log("matched");
        //} else {
        //    console.log("no matched");
        //    console.log(tweetObj.tweets[i].geo_coordinates_0);
        //    console.log(tweetObj.tweets[i].geo_type);
            //console.log(typeof(tweetObj.tweets[i].geo_coordinates_0));
        //};
    };
}

function getTweets(uuid) {
    var keepRequesting = true;
    var totalTweets = 0;
    var tweetData;
    $.ajax({
        url: "/api/"+uuid,
        success: function(data) {
            if (data['completed'] == "true") {
                keepRequesting = false;
            };
            $("#progress").html("<p>SEARCHING - "+data.results.length+" Tweets</p>");
            totalTweets = data.results.length;
            console.log(data);
            tweetData = data;
            //if (console.log(data['completed']) === "true") {
            //    keepRequesting = false;
            //};
            //console.log("keep requesting...");
            //console.log(keepRequesting);
        },
        complete: function() { 
                if (keepRequesting){
                    setTimeout(function() {
                        getTweets(uuid);
                    }, 1000);
                } else {
                    $("#progress").removeClass("twinkle");
                    $("#progress").html("<p>"+totalTweets+" Tweets Found!</p>");
                    createTweetMarkers(tweetData);
                }
        },});
}

var pinColor;
var pinImage
var pinShadow;

function createTweetMarker(obj) {
        var tweet = $.parseJSON(obj);
        var marker = new google.maps.Marker({
            position: new google.maps.LatLng(tweet.geo.coordinates[0],tweet.geo.coordinates[1]),
            map: map,
            icon: pinImage,
            shadow: pinShadow
        });
        google.maps.event.addListener(marker, 'click', function() {
            console.log(tweet.text);
            $("#tweet-data p:first").html("<strong>Text: </strong>" + tweet.text);
            $("#tweet-data p:last").html("<strong>Created at: </strong>" + tweet.created_at);  
            $("#tweet-data").show();
        });
    }
function createTweetMarker_latLng(lat, lng, text, created_at) {
        var marker = new google.maps.Marker({
            position: new google.maps.LatLng(lat,lng),
            map: map,
            icon: pinImage,
            shadow: pinShadow
        });
        google.maps.event.addListener(marker, 'click', function() {
            console.log(text);
            $("#tweet-data p:first").html("<strong>Text: </strong>" + tweet.text);
            $("#tweet-data p:last").html("<strong>Created at: </strong>" + tweet.created_at);  
            $("#tweet-data").show();
        });
    }




function createTweetMarkers(obj) {
        //create different color markers
        var pinColor = get_random_color();
        pinImage = new google.maps.MarkerImage("http://chart.apis.google.com/chart?chst=d_map_pin_letter&chld=%E2%80%A2|" + pinColor,
            new google.maps.Size(21, 34),
            new google.maps.Point(0,0),
            new google.maps.Point(10, 34));
        pinShadow = new google.maps.MarkerImage("http://chart.apis.google.com/chart?chst=d_map_pin_shadow",
            new google.maps.Size(40, 37),
            new google.maps.Point(0, 0),
            new google.maps.Point(12, 35));

        console.log("createTweetMarkser called");
        for (var i=0; i<obj.results.length; i++) {
            createTweetMarker(obj.results[i]);
           }
    }
function get_random_color() {
//http://stackoverflow.com/questions/1484506/random-color-generator-in-javascript
    var letters = '0123456789ABCDEF'.split('');
    var color = '';
    for (var i = 0; i < 6; i++ ) {
        color += letters[Math.round(Math.random() * 15)];
    }
    return color;
}
