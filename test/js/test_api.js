//var imported = document.createElement('script')
//imported.src = 'generated.js'
//document.head.appendChild(imported)

class TestRunner{

    constructor(){
        this.passed = {}
        this.failed = {}
    }

    onerror(test, code, reason) {
        var elem = document.createElement('p');
        document.body.insertBefore(elem, document.getElementById('div1'));
        elem.innerHTML = test + ": FAILED[" + code + "] " + reason;
        elem.setAttribute('style', 'color:red');
    }

    onsuccess(test, text, expected) {
        var elem = document.createElement('p');
        document.body.insertBefore(elem, document.getElementById('div1'));
        if (text == expected || typeof expected == 'undefined'){
            elem.innerHTML = test + ": PASSED";
            elem.setAttribute('style', 'color:darkgreen');
        }  else {
            elem.innerHTML = test + ": FAILED  response not as expected '" + text + "' != " + expected;
            elem.setAttribute('style', 'color:red');
        }
    }

    run(){
        //this will run test in parallel, as the onerror/onsuccess callbacks are invoked asynchrounously
        for (var test of [this.test_api_basic, this.test_api_basic_optional_param_value]) {
            this.current_test = test;
            this.current_test(test.name);
        }
    }

    test_api_basic(testname) {
        let self = this;
        let api = new bantam.test.test_js.RestAPIExample('http://localhost:8080');
        api.api_get_basic(function(text){self.onsuccess(testname, text, "Response to test_api_basic")},
            function(code, reason){self.onerror(code, reason)},
            1234, true, 9.8765, "text");
    }

    test_api_basic_optional_param_value(testname) {
        let self = this;
        let api = new bantam.test.test_js.RestAPIExample('http://localhost:8080');
        api.api_get_basic(function(text){self.onsuccess(testname, text, "Response to test_api_basic")},
            function(testname, code, reason){self.onerror(code, reason)},
            1234, true, 9.8765);//, "text");
    }

}