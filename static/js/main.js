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
function getTweets(uuid) {
    var keepRequesting = true;
    var totalTweets = 0;
    var tweetData;
    $.ajax({
        url: "http://localhost:5000/api/"+uuid,
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

function createTweetMarker(obj) {
        var tweet = $.parseJSON(obj);
        var marker = new google.maps.Marker({
            position: new google.maps.LatLng(tweet.geo.coordinates[0],tweet.geo.coordinates[1]),
            map: map,
        });
        google.maps.event.addListener(marker, 'click', function() {
            console.log(tweet.text);
            $("#tweet-data p:first").html("<strong>Text: </strong>" + tweet.text);
            $("#tweet-data p:last").html("<strong>Created at: </strong>" + tweet.created_at);  
            $("#tweet-data").show();
        });
    }


function createTweetMarkers(obj) {
        console.log("createTweetMarkser called");
        for (var i=0; i<obj.results.length; i++) {
            createTweetMarker(obj.results[i]);
           }
    }

