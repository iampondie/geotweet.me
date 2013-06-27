function statusCntl($scope, $http) {   
    $http.get('/api/status').success(
        function(data){
            $scope.headers = data.headers;        
            $scope.services = data.results;
            console.log(data.results);
            for (var i = 0; i < data.results.length; i++) {
                if (data.results[i].state == 20) {
                    $scope.services[i].css = "statusrunning";
                } else if (data.results[i].state == 10) {
                    $scope.services[i].css = "statuserror";
                } else {
                    $scope.services[i].css = "statusnominal";
                }
           }
    });

    $http.get('/api/tweets/total').success(
        function(data) {
            $scope.totalTweets = data.results;
        }).error(
        function(data) {    
            console.log("Failed retrieveing total tweets");
            console.log(data);
        });

    setInterval(function () {
        $scope.$apply(function () {
            $http.get('/api/tweets/total').success(
                function(data){
                    $scope.totalTweets = data.results; 
                    $scope.tweet_css = "";
                //clean up dates
                }).error(function(data) {
                    console.log("Failed retrieving total tweets");
                    console.log(data);  
                });
            });
        
    }, 1000);

    $scope.$watch('totalTweets', function(newval, oldval) {
        $scope.tweet_css = "fadeUpdate";
    });


}
