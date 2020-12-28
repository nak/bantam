
class bantam {};
bantam.test = class {};
bantam.test.test_js = class {}

bantam.test.test_js.RestAPIExample = class {
      constructor(site){this.site = site;}

      /*
            
      Some sort of doc
      @param param1:
      @param param2:
      @param param3:
      @param param4:
      @response: String for test_api_basic
      

      @param {(str, bool) => Any} onsuccess callback invoked on successful response, 
          with the first parambeing the response from the server (typed according to underlying Python API),
          and the second indicating  whether  the response is completed (for streamed responses)
      @param {(int, str) => null}  onerror  callback upon error, passing in response code and status text
      */
      api_get_basic( onsuccess, onerror, param1, param2, param3, param4) {

         let request = new XMLHttpRequest();
         let params = "";
         let c = '?';
         let map = {"param1": param1,"param2": param2,"param3": param3,"param4": param4};
         for (var param of ["param1", "param2", "param3", "param4"]){
             if (typeof map[param] !== 'undefined'){
                 params += c + param + '=' + map[param];
                 c= ';';
             }
         }
         request.open("GET", this.site + "/RestAPIExample/api_get_basic" + params);
         request.setRequestHeader('Content-Type', "text/plain");
         request.onreadystatechange = function() {
            if(request.readyState == XMLHttpRequest.DONE && (request.status < 200 || request.status > 299)){
                onerror(request.status, request.statusText + ": " + request.responseText);
            } else if (request.readyState >= XMLHttpRequest.DONE) {
                onsuccess((request.response), request.readyState == XMLHttpRequest.DONE);
            }
         }
         request.send();
      }

      /*
            
      Some sort of doc
      @param param1:
      @param param2:
      @param param3:
      @param param4:
      @response: stream of int
      

      @param {(bytes, bool) => Any} onreceive callback invoked on successful response, 
          with the first parambeing the response from the server (typed according to underlying Python API),
          and the second indicating  whether  the response is completed (for streamed responses)
      @param {(int, str) => null}  onerror  callback upon error, passing in response code and status text
      */
      api_get_stream( onsuccess, onerror, param1, param2, param3, param4) {

         let request = new XMLHttpRequest();
         let params = "";
         let c = '?';
         let map = {"param1": param1,"param2": param2,"param3": param3,"param4": param4};
         for (var param of ["param1", "param2", "param3", "param4"]){
             if (typeof map[param] !== 'undefined'){
                 params += c + param + '=' + map[param];
                 c= ';';
             }
         }
         request.open("GET", this.site + "/RestAPIExample/api_get_stream" + params);
         request.setRequestHeader('Content-Type', "text/json");
         request.onreadystatechange = function() {
            if(request.readyState == XMLHttpRequest.DONE && (request.status < 200 || request.status > 299)){
                onerror(request.status, request.statusText + ": " + request.responseText);
            } else if (request.readyState >= 3) {
                onreceive((request.response), request.readyState == XMLHttpRequest.DONE);
            }
         }
         request.send();
      }

      /*
            
      Some sort of doc
      @param param1:
      @param param2:
      @param param3:
      @param param4:
      @response: stream of int
      

      @param {(str, bool) => Any} onreceive callback invoked on successful response, 
          with the first parambeing the response from the server (typed according to underlying Python API),
          and the second indicating  whether  the response is completed (for streamed responses)
      @param {(int, str) => null}  onerror  callback upon error, passing in response code and status text
      */
      api_post_stream(param1, param2, param3, param4, onreceive, onerror) {

         let request = new XMLHttpRequest();
         let params = "";
         let c = '?';
         let map = {"param1": param1,"param2": param2,"param3": param3,"param4": param4};
         for (var param of ["param1", "param2", "param3", "param4"]){
             if (typeof map[param] !== 'undefined'){
                 params += c + param + '=' + map[param];
                 c= ';';
             }
         }
         request.seenBytes = 0;
         request.open("POST", this.site + "/RestAPIExample/api_post_stream");
         request.setRequestHeader('Content-Type', "text/json");
         request.onreadystatechange = function() {
            if (request.readyState == XMLHttpRequest.DONE && (request.status > 299 || request.status < 200)) {
                onerror(request.status, request.statusText);
            } else if(request.readyState >= 3) {
                var newData = request.responseText.substr(xhr.seenBytes);
                onreceive((newData), request.readyState == XMLHttpResponse.DONE);
            }
         }
         request.send(JSON.stringify(params));
      }

      /*
            
      Some sort of doc
      @param param1:
      @param param2:
      @param param3:
      @param param4:
      @response: stream of int
      

      @param {(str, bool) => Any} onreceive callback invoked on successful response, 
          with the first parambeing the response from the server (typed according to underlying Python API),
          and the second indicating  whether  the response is completed (for streamed responses)
      @param {(int, str) => null}  onerror  callback upon error, passing in response code and status text
      */
      api_post_streamed_req_and_resp(param1, param2, param3, param4, onreceive, onerror) {

         let request = new XMLHttpRequest();
         let params = "";
         let c = '?';
         let map = {"param1": param1,"param2": param2,"param3": param3,"param4": param4};
         for (var param of ["param1", "param2", "param3", "param4"]){
             if (typeof map[param] !== 'undefined'){
                 params += c + param + '=' + map[param];
                 c= ';';
             }
         }
         request.seenBytes = 0;
         request.open("POST", this.site + "/RestAPIExample/api_post_streamed_req_and_resp");
         request.setRequestHeader('Content-Type', "text/plain");
         request.onreadystatechange = function() {
            if (request.readyState == XMLHttpRequest.DONE && (request.status > 299 || request.status < 200)) {
                onerror(request.status, request.statusText);
            } else if(request.readyState >= 3) {
                var newData = request.responseText.substr(xhr.seenBytes);
                onreceive((newData), request.readyState == XMLHttpResponse.DONE);
            }
         }
         request.send(JSON.stringify(params));
      }
};
