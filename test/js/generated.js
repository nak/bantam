
class bantam {};
bantam.test = class {};
bantam.test.test_js = class {}

bantam.test.test_js.RestAPIExample = class {
      constructor(site){this.site = site;}

      /*
      Some sort of doc
      
      @param {function(string) => null} onsuccess callback inoked, passing in response from server on success
      @param {function(int, str) => null}  onerror  callback upon error, passing in response code and status text
      @param {{number [int]}} param1
      @param {{boolean}} param2
      @param {{number [float]}} param3
      @param {{string}} param4
      */
      api_get_basic(onsuccess, onerror, param1, param2, param3, param4) {

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
         let buffered = null;
         request.onreadystatechange = function() {
            if(request.readyState == XMLHttpRequest.DONE && (request.status < 200 || request.status > 299)){
                onerror(request.status, request.statusText + ": " + request.responseText);
            } else if (request.readyState >= XMLHttpRequest.DONE) {
                
                var converted = request.response.substr(request.seenBytes);
                if ((typeof converted == 'number') && isNaN(converted)){
                   onerror(-1, "Unable to convert '" + val + "' to expected type");
                }
               onsuccess(converted, request.readyState == XMLHttpRequest.DONE); 
               request.seenBytes = request.response.length;
            }
         }
         request.send();
      }

      /*
      Some sort of doc
      
      @param {function({string [optional]}, bool) => null} onreceive callback invoked on each chunk received from server 
      @param {function(int, str) => null}  onerror  callback upon error, passing in response code and status text
      @param {{number [int]}} param1
      @param {{boolean}} param2
      @param {{number [float]}} param3
      @param {{{string [optional]}}} param4
      
      @return {{function(int) => null}} callback to send streamed chunks to server
      */
      api_get_stream(onreceive, onerror, param1, param2, param3, param4) {

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
         let buffered = null;
         request.onreadystatechange = function() {
            if(request.readyState == XMLHttpRequest.DONE && (request.status < 200 || request.status > 299)){
                onerror(request.status, request.statusText + ": " + request.responseText);
            } else if (request.readyState >= 3) {
                
             let vals = request.response.substr(request.seenBytes).trim().split('\n');
             request.seenBytes = 0; 
             for (var i = 0; i < vals.length; ++i) {
                let val = vals[i];
                let done = (i == vals.length -1) && (request.readyState == XMLHttpRequest.DONE);
                if (val !== ''){
                   if (buffered != null){onreceive(buffered, false); buffered = null;}
                   buffered = parseInt(val);
                   if (typeof buffered === 'numbered' && isNaN(buffered)){
                      buffered = null;
                      onerror(-1, "Unable to convert server response '" + val + "' to expected type");
                      break;
                   }
                }
             }
             if (buffered !== null && request.readyState == XMLHttpRequest.DONE){onreceive(buffered, true);}
             request.seenBytes = request.response.length;
            }
         }
         request.send();
      }

      /*
      Some sort of doc
      
      @param {function({string [optional]}, bool) => null} onreceive callback invoked on each chunk received from server 
      @param {function(int, str) => null}  onerror  callback upon error, passing in response code and status text
      @param {{number [int]}} param1
      @param {{boolean}} param2
      @param {{number [float]}} param3
      @param {{{string [optional]}}} param4
      
      @return {{function(str) => null}} callback to send streamed chunks to server
      */
      api_get_stream_text(onreceive, onerror, param1, param2, param3, param4) {

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
         request.open("GET", this.site + "/RestAPIExample/api_get_stream_text" + params);
         request.setRequestHeader('Content-Type', "text/json");
         let buffered = null;
         request.onreadystatechange = function() {
            if(request.readyState == XMLHttpRequest.DONE && (request.status < 200 || request.status > 299)){
                onerror(request.status, request.statusText + ": " + request.responseText);
            } else if (request.readyState >= 3) {
                
                var converted = request.response.substr(request.seenBytes);
                if ((typeof converted == 'number') && isNaN(converted)){
                   onerror(-1, "Unable to convert '" + val + "' to expected type");
                }
               onreceive(converted, request.readyState == XMLHttpRequest.DONE); 
               request.seenBytes = request.response.length;
            }
         }
         request.send();
      }

      /*
      Some sort of doc
      
      @param {function({string [optional]}, bool) => null} onreceive callback invoked on each chunk received from server 
      @param {function(int, str) => null}  onerror  callback upon error, passing in response code and status text
      @param {{number [int]}} param1
      @param {{boolean}} param2
      @param {{number [float]}} param3
      @param {{{string [optional]}}} param4
      
      @return {{function(str) => null}} callback to send streamed chunks to server
      */
      api_post_stream_text(onreceive, onerror, param1, param2, param3, param4) {

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
         request.open("GET", this.site + "/RestAPIExample/api_post_stream_text" + params);
         request.setRequestHeader('Content-Type', "text/json");
         let buffered = null;
         request.onreadystatechange = function() {
            if(request.readyState == XMLHttpRequest.DONE && (request.status < 200 || request.status > 299)){
                onerror(request.status, request.statusText + ": " + request.responseText);
            } else if (request.readyState >= 3) {
                
                var converted = request.response.substr(request.seenBytes);
                if ((typeof converted == 'number') && isNaN(converted)){
                   onerror(-1, "Unable to convert '" + val + "' to expected type");
                }
               onreceive(converted, request.readyState == XMLHttpRequest.DONE); 
               request.seenBytes = request.response.length;
            }
         }
         request.send();
      }

      /*
      <<No API documentation provided>>
      
      @param {function(<<unrecognized>>) => null} onsuccess callback inoked, passing in response from server on success
      @param {function(int, str) => null}  onerror  callback upon error, passing in response code and status text
      
      */
      publish_result(onsuccess, onerror, result) {

         let request = new XMLHttpRequest();
         let params = "";
         let c = '?';
         let map = {"result": result};
         for (var param of ["result"]){
             if (typeof map[param] !== 'undefined'){
                 params += c + param + '=' + map[param];
                 c= ';';
             }
         }
         request.open("GET", this.site + "/RestAPIExample/publish_result" + params);
         request.setRequestHeader('Content-Type', "text/plain");
         let buffered = null;
         request.onreadystatechange = function() {
            if(request.readyState == XMLHttpRequest.DONE && (request.status < 200 || request.status > 299)){
                onerror(request.status, request.statusText + ": " + request.responseText);
            } else if (request.readyState >= XMLHttpRequest.DONE) {
                
                var converted = null;
                if ((typeof converted == 'number') && isNaN(converted)){
                   onerror(-1, "Unable to convert '" + val + "' to expected type");
                }
               onsuccess(converted, request.readyState == XMLHttpRequest.DONE); 
               request.seenBytes = request.response.length;
            }
         }
         request.send();
      }

      /*
      Some sort of doc
      
      @param {function(string) => null} onsuccess callback inoked, passing in response from server on success
      @param {function(int, str) => null}  onerror  callback upon error, passing in response code and status text
      @param {{number [int]}} param1
      @param {{boolean}} param2
      @param {{number [float]}} param3
      @param {{{string [optional]}}} param4
      */
      api_post_basic(onsuccess, onerror, param1, param2, param3, param4) {

         
         let params = {
            "param1": param1,
            "param2": param2,
            "param3": param3,
            "param4": param4
         };
         let request = new XMLHttpRequest();
         request.seenBytes = 0;
         request.open("POST", this.site + "/RestAPIExample/api_post_basic" + "");
         request.setRequestHeader('Content-Type', "text/json");
         let buffered = null;
         request.onreadystatechange = function() {
            if (request.readyState == XMLHttpRequest.DONE && (request.status > 299 || request.status < 200)) {
                onerror(request.status, request.statusText + ': ' + request.responseText);
            } else if(request.readyState >= XMLHttpRequest.DONE) {
               
                var val = request.response.substr(request.seenBytes);
                var converted = request.response.substr(request.seenBytes);
                if ((typeof converted == 'number') && isNaN(converted)){
                   onerror(-1, "Unable to convert '" + val + "' to expected type");
                }
                onsuccess(converted, request.readyState == XMLHttpRequest.DONE);
               request.seenBytes = request.response.length;
            }
         }
         request.send(JSON.stringify(params));
         
      }

      /*
      Some sort of doc
      
      @param {function(string, bool) => null} onreceive callback invoked on each chunk received from server 
      @param {function(int, str) => null}  onerror  callback upon error, passing in response code and status text
      @param {{number [int]}} param1
      @param {{boolean}} param2
      @param {{number [float]}} param3
      @param {{string}} param4
      
      @return {{function(int) => null}} callback to send streamed chunks to server
      */
      api_post_stream(onreceive, onerror, param1, param2, param3, param4) {

         
         let params = {
            "param1": param1,
            "param2": param2,
            "param3": param3,
            "param4": param4
         };
         let request = new XMLHttpRequest();
         request.seenBytes = 0;
         request.open("POST", this.site + "/RestAPIExample/api_post_stream" + "");
         request.setRequestHeader('Content-Type', "text/json");
         let buffered = null;
         request.onreadystatechange = function() {
            if (request.readyState == XMLHttpRequest.DONE && (request.status > 299 || request.status < 200)) {
                onerror(request.status, request.statusText + ': ' + request.responseText);
            } else if(request.readyState >= 3) {
               
             // TODO: Can we clean this up a little? 
             let vals = request.response.substr(request.seenBytes).trim().split('\n');
             request.seenBytes = 0; 
             for (var i = 0; i < vals.length; ++i) {
                let val = vals[i];
                let done = (i == vals.length -1) && (request.readyState == XMLHttpRequest.DONE);
                if (val !== ''){
                   if (buffered != null){onreceive(buffered, false); buffered = null;}
                   buffered = parseInt(val);
                   if (typeof buffered === 'numbered' && isNaN(buffered)){
                      buffered = null;
                      onerror(-1, "Unable to convert server response '" + val + "' to expected type");
                      break;
                   }
                }
             }
             if (buffered !== null && request.readyState == XMLHttpRequest.DONE){onreceive(buffered, true);}
             request.seenBytes = request.response.length;
            }
         }
         request.send(JSON.stringify(params));
         
      }

      /*
      Some sort of doc
      
      @param {function(<<unspecified>>, bool) => null} onreceive callback invoked on each chunk received from server 
      @param {function(int, str) => null}  onerror  callback upon error, passing in response code and status text
      @param {{number [int]}} param1
      @param {{boolean}} param2
      @param {{number [float]}} param3
      @return {{function(str) => null}} callback to send streamed chunks to server
      */
      api_post_streamed_req_and_resp(onreceive, onerror, param1, param2, param3, param4) {

         
         let params = "";
         let c = '?';
         let map = {"param1": param1,"param2": param2,"param3": param3,"param4": param4};
         for (var param of ["param1", "param2", "param3", "param4"]){
             if (typeof map[param] !== 'undefined'){
                 params += c + param + '=' + map[param];
                 c= ';';
             }
         }
         let request = new XMLHttpRequest();
         request.seenBytes = 0;
         request.open("POST", this.site + "/RestAPIExample/api_post_streamed_req_and_resp" + params);
         request.setRequestHeader('Content-Type', "text/plain");
         let buffered = null;
         request.onreadystatechange = function() {
            if (request.readyState == XMLHttpRequest.DONE && (request.status > 299 || request.status < 200)) {
                onerror(request.status, request.statusText + ': ' + request.responseText);
            } else if(request.readyState >= 3) {
               
                var val = request.response.substr(request.seenBytes);
                var converted = request.response.substr(request.seenBytes);
                if ((typeof converted == 'number') && isNaN(converted)){
                   onerror(-1, "Unable to convert '" + val + "' to expected type");
                }
                onreceive(converted, request.readyState == XMLHttpRequest.DONE);
               request.seenBytes = request.response.length;
            }
         }
         request.send();
         
         var onchunkready = function(chunk){
             request.send(chunk);
         }
         return onchunkready;

      }
};
