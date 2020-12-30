
class bantam {};
bantam.salutations = class {};

bantam.salutations.Greetings = class {
      constructor(site){this.site = site;}

      /*
      Welcome someone
      The response will be provided as the (first) parameter passed into onsuccess
      
      @param {function(string) => null} onsuccess callback inoked, passing in response from server on success
      @param {function(int, str) => null}  onerror  callback upon error, passing in response code and status text
      @param {{string}} name name of person to greet
      */
      welcome(onsuccess, onerror, name) {

         let request = new XMLHttpRequest();
         let params = "";
         let c = '?';
         let map = {"name": name};
         for (var param of ["name"]){
             if (typeof map[param] !== 'undefined'){
                 params += c + param + '=' + map[param];
                 c= ';';
             }
         }
         request.open("GET", this.site + "/Greetings/welcome" + params);
         request.setRequestHeader('Content-Type', "text/html");
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
      Say goodbye by telling someone to have a day (of the given type)
      The response will be provided as the (first) parameter passed into onsuccess
      
      @param {function(string) => null} onsuccess callback inoked, passing in response from server on success
      @param {function(int, str) => null}  onerror  callback upon error, passing in response code and status text
      @param {{string}} type_of_day adjective describing type of day to have
      */
      goodbye(onsuccess, onerror, type_of_day) {

         let request = new XMLHttpRequest();
         let params = "";
         let c = '?';
         let map = {"type_of_day": type_of_day};
         for (var param of ["type_of_day"]){
             if (typeof map[param] !== 'undefined'){
                 params += c + param + '=' + map[param];
                 c= ';';
             }
         }
         request.open("GET", this.site + "/Greetings/goodbye" + params);
         request.setRequestHeader('Content-Type', "text/html");
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
};
