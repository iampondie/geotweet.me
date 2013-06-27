function prevSearchCntl($scope, $http) {
    //Set up table on  first load

    function cleanUp(arr) {
        for (var i = 0; i < arr.searches.length; i++) {
            var myDate = moment(arr.searches[i].Created['$date']);
            arr.searches[i].Created = myDate.format("DD/MM/YYYY HH:mm:ss")
            var terms = arr.searches[i].Terms[0];
            arr.searches[i].Terms = terms
        } 
    }

    $http.get('/api/search/previous').success(
        function(data){
            $scope.searches = data.results; 
            //clean up dates, and term list
            cleanUp($scope);

            //Setup table headers
            $scope.headers = data.headers;
            
            //default ordering
            $scope.order = 'Created';
            $scope.reverse = true;
          
            $scope.toggleSort = function(sort) {
                $scope.order = sort;
                $scope.reverse = !$scope.reverse
            }
    }).error(function(data) { 
        console.log("Failed retrieving previous searches");
        console.log(data);
    });

    setInterval(function () {
        $scope.$apply(function () {
            $http.get('/api/search/previous').success(
                function(data){
                $scope.searches = data.results; 
                //clean up dates
                cleanUp($scope);
                $scope.headers = data.headers;
                }).error(function(data) {
                    console.log("Failed retrieving previous searches");
                    console.log(data);  
                });
            });
        
    }, 1000);
    
    //$scope.$watch('searches', function(newval, oldval) {
    //    console.log($scope.searches.length);
    //    for (var i = 0; i < newval.length; i++) {
    //        if (newval[i].Tweets != oldval[i].Tweets) {
    //            //Set correct search to flash
    //            for (var j = 0; j < $scope.searches.length; j++) {

    //                console.log($scope.searches[j].Terms);
    //                console.log(newval.searches[i].Terms);
    //                if (newval.searches[i].Terms == $scope.searches[j].Terms) {
    //                    $scope.searches[j].tweet_css = "fadeUpdate";
    //                }
    //            }
    //        } else {
    //            $scope.searches[i].tweet_css = "";
    //        }
    //    }
    //});
}
