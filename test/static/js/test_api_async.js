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
            let api = bantam.class_rest_get.RestAPIExampleAsync;
            await sleep(5000);
            if (failed_count > 0){
               alert("There were failed tests");
            }
            api.publish_result(function(a, b){}, function(a,b){},
                               failed_count==0?"PASSED":JSON.stringify(self.failed));
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
        if (text === expected || typeof expected == 'undefined'){
            elem.innerHTML = test + ": PASSED";
            elem.setAttribute('style', 'color:darkgreen');
            this.passed[test] = "PASSED";
        }  else {
            elem.innerHTML = test + ": FAILED  response not as expected '" + text + "' != '" + expected + "'";
            elem.setAttribute('style', 'color:red');
            this.failed[test] = reason;
        }
        this.publish_results();
    }

    run(){
        this.test_suite = [
            this.test_api_basic,
            this.test_api_basic_optional_param_value,
            this.test_api_basic_error_not_all_required_params,
            this.test_api_post_basic,
            this.test_api_post_basic_optional_param_value,
            this.test_api_post_basic_error_not_all_required_params,
            this.test_api_post_streamed_response_text,
            this.test_api_post_streamed_req_resp,
            this.test_api_session_instance
            ];
        (async () => {
            //this will run test in parallel, as the onerror/onsuccess callbacks are invoked asynchrounously
            for (var test of this.test_suite) {
                this.current_test = test;
                try{
                    await this.current_test(test.name);
                } catch (error){
                    this.onerror(test.name,  -1, "Caught exception in test: " + JSON.stringify(error) + error);
                }
            }
        })();
    }

    async test_api_basic(testname) {
        let self = this;
        let api = bantam.class_rest_get.RestAPIExampleAsync;
        try{
            const text = await api.api_get_basic(1234, true, 9.8765, "text", {'f1': 0.1, 'f2': -345});
            self.onsuccess(testname, text, "Response to test_api_basic 0.1 -345")
        } catch (error){
            self.onerror(testname, error.status, JSON.stringify(error));
        }
    }

    async test_api_post_basic_optional_param_value(testname) {
        let self = this;
        let api = bantam.class_rest_get.RestAPIExampleAsync;
        try{
            const text = await api.api_post_basic(
                1234, true, 9.8765);// no text param provided, but server should then us default
            self.onsuccess(testname, text, "called basic post operation");
        } catch (error){
            self.onerror(testname, error.status, JSON.stringify(error));
        }
     }

     async test_api_basic_error_not_all_required_params(testname) {
        let self = this;
        let api = bantam.class_rest_get.RestAPIExampleAsync;
        try{
            const text = await api.api_get_basic(1234, true);
            self.onerror(testname,-1, "Call succeeded ");
        } catch (error){
            if (error.status == 400){
                self.onsuccess(testname);
            } else {
                self.onerror(testname, error.status, "Unexpected error code or exception: " + JSON.stringify(error));
            }
        }
    }

    async test_api_get_streamed_response(testname){
        let self = this;
        let api = bantam.class_rest_get.RestAPIExampleAsync;
        let int_vals = [];
        try{
            for await (const int_val of  api.api_get_stream(98, false, 1239929.04, "string value")){
                int_vals.push(int_val);
            }
        } catch (error){
            self.onerror(testname, error.status, JSON.stringify(error));
            return;
        }
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


    async test_api_get_streamed_response_text(testname){
        let self = this;
        let api = bantam.class_rest_get.RestAPIExampleAsync;
        let count = 0
        let error = false
        let remainder = ''
        for await (var line of api.api_get_stream_bytes(98, false, 1239929.04, "string value", [9, 8, 7, 6, 5])){
          let parts = new TextDecoder().decode(line)
          for (line of parts.split('\n')){
               if (line === ''){
                    continue;
                }
                if (count == 10 && line != 'DONE [9, 8, 7, 6, 5]'){
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
       }
    }


    async test_api_post_basic(testname) {
        let self = this;
        let api = bantam.class_rest_get.RestAPIExampleAsync;
        try{
            const text = await api.api_post_basic(1234, true, 9.8765, "text");
            self.onsuccess(testname, text, "called basic post operation");
        } catch (error){
            self.onerror(testname, error.status, JSON.stringify(error))
        }
    }


    async test_api_basic_optional_param_value(testname) {
        let self = this;
        let api = bantam.class_rest_get.RestAPIExampleAsync;
        try{
            const text = await api.api_get_basic(1234, true, 9.8765);// no text param provided, but server should then us default
            self.onsuccess(testname, text, "Response to test_api_basic 1.0 2");
        }  catch (error){
            self.onerror(testname, error.status, JSON.stringify(error));
        }
    }

    async test_api_post_streamed_response_text(testname){
        let self = this;
        let api = bantam.class_rest_get.RestAPIExampleAsync;
        let count = 0;
        let error = false;
        for await (const text of api.api_post_stream_text(98, false, 1239929.04, "string value")){
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
        }
        if (!error){
            self.onsuccess(testname);
        }
    }

   async *chunked_req(){
             for(let i = 0; i< 10; ++i){
                yield "int value " + i;
             }
   }

    async test_api_post_streamed_req_resp(testname){
        let self = this;
        let api = bantam.class_rest_get.RestAPIExampleAsync;
        let count = 0;
        let error = false;

         for await (const text of api.api_post_streamed_req_and_resp(98, false, 1239929.04, this.chunked_req)){
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
        }
        if (!error){
            self.onsuccess(testname);
        }
    }

    async test_api_post_basic_error_not_all_required_params(testname) {
        let self = this;
        let api = bantam.class_rest_get.RestAPIExampleAsync;
        try{
            const text =  await api.api_post_basic(1234, true);
            alert("HERE3" + testname)
            self.onerror(testname, -1, "Expected exception due to lack of parameters");
        } catch (error){
            self.onsuccess(testname);
        }
    }


   async test_api_session_instance(testname) {
        let self = this;
        let api = new bantam.class_rest_get.ClassRestExampleAsync(92);
        const text =  await api.echo(1234, true, -8721.345);
        if (text !== "called basic post operation on instance 92: 1234 True -8721.345 text") {
           self.onerror(testname, -1, "not a match:  '" + text + "' != 'called basic post operation on instance 92: 1234 True -8721.345 text'");
        } else {
            self.onsuccess(testname);
        }
        // await api.expire()
    }
}