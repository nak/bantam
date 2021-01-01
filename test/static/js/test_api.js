//var imported = document.createElement('script')
//imported.src = 'generated.js'
//document.head.appendChild(imported)

class TestRunner{

    constructor(){
        this.passed = {}
        this.failed = {}
    }

    publish_results(){
        let passed_count = Object.keys(this.passed).length;
        let failed_count = Object.keys(this.failed).length
        let self = this;
        function sleep(ms) {
          return new Promise(resolve => setTimeout(resolve, ms));
        }
        async function close(){
            let api = new bantam.test.test_js.RestAPIExample('http://localhost:8080');
            api.publish_result(function(a, b){}, function(a,b){},
                               failed_count==0?"PASSED":JSON.stringify(self.failed));
            await sleep(5000);
            window.close();
        }
        if (this.test_suite.length == passed_count + failed_count){
            var elem = document.createElement('p');
            document.body.insertBefore(elem, document.getElementById('div1'));
            elem.innerHTML = failed_count == 0?"ALL TESTS PASSED":"COMPLETE WITH AT LEAST ONE FAILURE"; // got expected error response
            elem.setAttribute('style', 'color:' + failed_count==0?'darkgreen':'red');
            close();
        }
    }

    onerror(test, code, reason, expected) {
        var elem = document.createElement('p');
        document.body.insertBefore(elem, document.getElementById('div1'));
        if (typeof expected == 'undefined'){
            elem.innerHTML = test + ": FAILED[" + code + "] " + reason;
            elem.setAttribute('style', 'color:red');
            this.failed[test] = reason;
        } else if (reason != expected) {
            elem.innerHTML = test + ": FAILED to receive expected error response: '" + reason + "' != '" + expected + ";";
            elem.setAttribute('style', 'color:red');
            this.failed[test] = reason;
        } else {
            elem.innerHTML = test + ": PASSED"; // got expected error response
            elem.setAttribute('style', 'color:darkgreen');
            this.passed[test] = "PASSED";
        }
        this.publish_results();
    }

    onsuccess(test, text, expected) {
        var elem = document.createElement('p');
        document.body.insertBefore(elem, document.getElementById('div1'));
        if (text == expected || typeof expected == 'undefined'){
            elem.innerHTML = test + ": PASSED";
            elem.setAttribute('style', 'color:darkgreen');
            this.passed[test] = "PASSED";
        }  else {
            elem.innerHTML = test + ": FAILED  response not as expected '" + text + "' != " + expected;
            elem.setAttribute('style', 'color:red');
            this.failed[test] = reason;
        }
        this.publish_results();
    }

    run(){
        this.test_suite = [this.test_api_basic, this.test_api_basic_optional_param_value,
            this.test_api_basic_error_not_all_required_params,
            this.test_api_get_streamed_response, 
            this.test_api_get_streamed_response_text,
            this.test_api_post_basic,
            this.test_api_post_basic_optional_param_value,
            this.test_api_post_streamed_response,
            this.test_api_post_streamed_response_text,
            this.test_api_post_basic_error_not_all_required_params];
        //this will run test in parallel, as the onerror/onsuccess callbacks are invoked asynchrounously
        for (var test of this.test_suite) {
            this.current_test = test;
            try{
                this.current_test(test.name);
            } catch (error){
                this.onerror(test.name,  -1, "Caught exception in test: " + error);
            }
        }
    }

    test_api_basic(testname) {
        let self = this;
        let api = new bantam.test.test_js.RestAPIExample('http://localhost:8080');
        api.api_get_basic(function(text){self.onsuccess(testname, text, "Response to test_api_basic")},
            function(code, reason){self.onerror(testname, code, reason)},
            1234, true, 9.8765, "text");
    }

    test_api_post_basic_optional_param_value(testname) {
        let self = this;
        let api = new bantam.test.test_js.RestAPIExample('http://localhost:8080');
        api.api_get_basic(function(text){self.onsuccess(testname, text, "Response to test_api_basic")},
            function(code, reason){self.onerror(testname, code, reason)},
            1234, true, 9.8765);// no text param provided, but server should then us default
    }

     test_api_basic_error_not_all_required_params(testname) {
        let self = this;
        let api = new bantam.test.test_js.RestAPIExample('http://localhost:8080');
        api.api_get_basic(function(text){self.onsuccess(testname, text, "Response to test_api_basic")},
            function(code, reason){self.onerror(testname, code, reason,
            "Bad Request: Improperly formatted query: api_get_basic() missing 1 required positional argument: 'param3'")},
            1234, true);
    }

    test_api_get_streamed_response(testname){
        let self = this;
        let api = new bantam.test.test_js.RestAPIExample('http://localhost:8080');
        let int_vals = [];
        let onreceive = function(int_val, is_done){
            int_vals.push(int_val);
            if (is_done){
                let is_valid = true;
                for (var i = 0; i < int_vals.length; ++i){
                    if (i != int_vals[i]){
                        is_valid = false;
                    }
                }
                if (!is_valid || int_vals.length != 10){
                    self.onerror(testname, -1, "Response not a stream of successive integers from 0 to 9 as expected: "
                     + JSON.stringify(int_vals));
                } else {
                    self.onsuccess(testname);
                }
            }
        }
        api.api_get_stream(onreceive, function(code, reason){self.onerror(testname, code, reason)},
             98, false, 1239929.04, "string value");
    }


    test_api_get_streamed_response_text(testname){
        let self = this;
        let api = new bantam.test.test_js.RestAPIExample('http://localhost:8080');
        let count = 0
        let error = false
        let onreceive = function(text, is_done){
            let split = text.trim().split('\n');
            for (var line of split){
                if (line === ''){
                    continue;
                }

                if (count == 10 && line != 'DONE'){
                     self.onerror(testname, -1, "Unexpected response: '" + line + "' != 'DONE'");
                     error = true;
                     break;
                }
                if(count < 10 && line !== 'GET COUNT: ' + count){
                    self.onerror(testname, -1, "Unexpected response: '" + line + "' != 'GET COUNT: " + count + "'");
                    error = true;
                    break;
                }
                ++count;
            }
            if(is_done && !error){
                self.onsuccess(testname);
            }
        }
        api.api_get_stream_text(onreceive, function(code, reason){self.onerror(testname, code, reason)},
             98, false, 1239929.04, "string value");
    }


    test_api_post_basic(testname) {
        let self = this;
        let api = new bantam.test.test_js.RestAPIExample('http://localhost:8080');
        api.api_post_basic(function(text){self.onsuccess(testname, text, "called basic post operation")},
            function(code, reason){self.onerror(testname, code, reason)},
            1234, true, 9.8765, "text");
    }


    test_api_basic_optional_param_value(testname) {
        let self = this;
        let api = new bantam.test.test_js.RestAPIExample('http://localhost:8080');
        api.api_post_basic(function(text){self.onsuccess(testname, text, "called basic post operation")},
            function(code, reason){self.onerror(testname, code, reason)},
            1234, true, 9.8765);// no text param provided, but server should then us default
    }



    test_api_post_streamed_response(testname){
        let self = this;
        let api = new bantam.test.test_js.RestAPIExample('http://localhost:8080');
        let int_vals = [];
        let onreceive = function(int_val, is_done){
            int_vals.push(int_val);
            if (is_done){
                let is_valid = true;
                for (var i = 0; i < int_vals.length; ++i){
                    if (i != int_vals[i]){
                        is_valid = false;
                    }
                }
                if (!is_valid || int_vals.length != 10){
                    self.onerror(testname, -1, "Response not a stream of successive integers from 0 to 9 as expected: "
                     + JSON.stringify(int_vals));
                } else {
                    self.onsuccess(testname);
                }
            }
        }
        api.api_post_stream(onreceive, function(code, reason){self.onerror(testname, code, reason)},
             98, false, 1239929.04, "string value");
    }

    test_api_post_streamed_response_text(testname){
        let self = this;
        let api = new bantam.test.test_js.RestAPIExample('http://localhost:8080');
        let count = 0;
        let error = false;
        let onreceive = function(text, is_done){
            let split = text.trim().split('\n');
            for (var line of split){
                if (line === ''){
                    continue;
                }
                if (count == 10 && line != 'DONE'){
                     self.onerror(testname, -1, "Unexpected response: '" + line + "' != 'DONE'");
                     error = true;
                     break;
                }
                if(count < 10 && line !== 'COUNT: ' + count){
                    self.onerror(testname, -1, "Unexpected response: '" + line + "' != 'COUNT: " + count + "'");
                    error = true;
                    break;
                }
                ++count;
            }
            if(is_done && !error){
                self.onsuccess(testname);
            }
        }
        api.api_post_stream_text(onreceive, function(code, reason){self.onerror(testname, code, reason)},
             98, false, 1239929.04, "string value");
    }


    test_api_post_basic_error_not_all_required_params(testname) {
        let self = this;
        let api = new bantam.test.test_js.RestAPIExample('http://localhost:8080');
        api.api_post_basic(function(text){self.onsuccess(testname, text, "Response to test_api_basic")},
            function(code, reason){self.onerror(testname, code, reason,
            "Bad Request: Improperly formatted query: api_post_basic() missing 1 required positional argument: 'param3'")},
            1234, true);
    }

}