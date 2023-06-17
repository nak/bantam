"""
Bantam provides the ability to auto-generate client-side javascript code to abstract the details of makting
HTTP requests to the server.  This abstraction implies that the developer never need to know about routes,
formulating URLs, how to make a POST request, how to stream data over HTTP, etc!

To generate client side code, create a Python source file -- let's name it generator.py --
and import all of the classes containing @web_api's
to be generated. Then add the main entry poitn to generate the javascript code, like so:

>>> from bantam.js import JavascriptGenerator
... from salutations import Greetings
...
... if __name__ == '__main__':
...     with open('salutations.js', 'bw') as output:
...        JavascriptGenerator.generate(out=output, skip_html=True)

Run the script as so:

.. code-block:: bash

    % python generate.py

With the above Greetings example, the generated javasctipt code will mimic the Python:

.. code-block:: javascript
    :caption: javascript code auto-generated from Python server's web API

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
             ...
          }

           /*
           Tell someone goodbye by telling them to have a day (of the given type)
           The response will be provided as the (first) parameter passed into onsuccess

           @param {function(string) => null} onsuccess callback inoked, passing in response from server on success
           @param {function(int, str) => null}  onerror  callback upon error, passing in response code and status text
           @param {{string}} type_of_day adjective describing type of day to have
           */
          goodbye(onsuccess, onerror, type_of_day) {
            ...
          }
    };

The code maintains the same hierarchy in namespaces as modules in Python, albeit under a global *bantam* namespace.
This prevents potential namespace collisions.  The signatures of the API mimic those defined in the Pyhon codebase,
with the noted exception of the *onsuccess* and *onerror* callbacks as the first two parameters.
This is typical of how plain javascript handles asynchronous transactions:  rather than returning a value or raising an
exception, these callbacks are invoked instead, upon response from the server.


"""
import inspect
import re
from aiohttp.web_response import Response, StreamResponse
from typing import Callable, Awaitable, Union
from typing import Dict, Tuple, List, IO, Type
from urllib.request import Request

from bantam.api import API, RestMethod

AsyncApi = Callable[[Request], Awaitable[Union[Response, StreamResponse]]]


class JavascriptGenerator:
    """
    Class for generating equivalent javascript API from Python web_api routes
    """

    ENCODING = 'utf-8'

    class Namespace:

        def __init__(self):
            self._namespaces: Dict[str, JavascriptGenerator.Namespace] = {}
            self._classes: Dict[str, List[Tuple[RestMethod, str, API]]] = {}

        def add_module(self, module: str) -> 'JavascriptGenerator.Namespace':
            if '.' in module:
                my_name, child = module.split('.', maxsplit=1)
                m = self._namespaces.setdefault(my_name, JavascriptGenerator.Namespace())
                m = m.add_module(child)
            else:
                my_name = module
                m = self._namespaces.setdefault(my_name, JavascriptGenerator.Namespace())
            return m

        def add_class_and_route_get(self, class_name, route, api):
            m = self.add_module(api.module)
            m._classes.setdefault(class_name, []).append((RestMethod.GET, route, api))

        def add_class_and_route_post(self, class_name, route, api):
            m = self.add_module(api.module)
            m._classes.setdefault(class_name, []).append((RestMethod.POST, route, api))

        @property
        def child_namespaces(self):
            return self._namespaces

        @property
        def classes(self):
            return self._classes

    # noinspection PyUnresolvedReferences
    @classmethod
    def generate(cls, out: IO, skip_html: bool = True) -> None:
        """
        Generate javascript code from registered routes

        :param out: stream to write to
        :param skip_html: whether to skip entries of content type 'text/html' as these are generally not used in direct
           javascript calls
        """
        from bantam.http import WebApplication
        namespaces = cls.Namespace()
        for route, api in WebApplication.callables_get.items():
            if not skip_html or (api.content_type.lower() != 'text/html'):
                classname = route[1:].split('/')[0]
                namespaces.add_class_and_route_get(classname, route, api)
        for route, api in WebApplication.callables_post.items():
            if not skip_html or (api.content_type.lower() != 'text/html'):
                classname = route[1:].split('/')[0]
                namespaces.add_class_and_route_post(classname, route, api)
        tab = ""

        def process_namespace(ns: cls.Namespace, parent_name: str):
            nonlocal tab
            for name_, child_ns in ns.child_namespaces.items():
                out.write(f"{parent_name}.{name_} = class {{}}\n".encode(cls.ENCODING))
                process_namespace(child_ns, parent_name + '.' + name_)
            for class_name, routes in ns.classes.items():
                clazz_map = {c.__name__: c for c in WebApplication._class_instance_methods
                             if WebApplication._class_instance_methods[c]}
                out.write(f"\n{parent_name}.{class_name} = class {{\n".encode(cls.ENCODING))
                tab += "   "

                if class_name in clazz_map:
                    clazz = clazz_map[class_name]
                    if inspect.isabstract(clazz):
                        continue
                    cls._generate_request(out, route=f"/{class_name}/_create",
                                          api=API(clazz, clazz._create, method=RestMethod.GET,
                                                  content_type="test/plain", is_class_method=True,
                                                  is_instance_method=False, is_constructor=True, expire_on_exit=False),
                                          tab=tab)
                    cls._generate_request(out, route=f"/{class_name}/expire",
                                          api=API(clazz, clazz._expire, method=RestMethod.GET,
                                                  content_type="text/plain",
                                                  is_class_method=True,
                                                  is_instance_method=True, is_constructor=False, expire_on_exit=False),
                                          tab=tab)
                for method, route_, api in routes:
                    cls._generate_request(out, route_, api, tab)
                tab = tab[:-3]
                out.write("};\n".encode(cls.ENCODING))  # for class end

        out.write("\nclass bantam {};\n".encode(cls.ENCODING))
        for name, namespace in namespaces.child_namespaces.items():
            if name.startswith('bantam'):
                continue
            name = "bantam." + name
            out.write(f"{name} = class {{}};\n".encode(cls.ENCODING))
            tab += "   "
            process_namespace(namespace, name)

    @classmethod
    def _generate_docs(cls, out: IO, api: API, tab, callback: str = 'onsuccess') -> None:
        def prefix(text: str, tab: str):
            new_text = ""
            for line_ in text.splitlines():
                new_text += tab + line_.strip() + '\n'
            return new_text
        basic_doc_parts = prefix(api.doc or "<<No API documentation provided>>", tab).split(':param', maxsplit=1)
        if len(basic_doc_parts) == 1:
            basic_doc = basic_doc_parts[0]
            params_doc = ""
        else:
            basic_doc, params_doc = basic_doc_parts
            params_doc = ':param ' + params_doc

        name_map = {'str': 'string', 'bool': 'boolean', 'int': 'number [int]', 'float': 'number [float]'}
        response_type_name = "<<unspecified>>"
        return_cb_type_name = None
        type_name = None
        none_type = type(None)
        for name, typ in api.arg_annotations.items():
            try:
                if hasattr(typ, '_name') and typ._name in ['AsyncGenerator', 'AsyncIterator']:
                    var_type_name = typ.__args__[1].__name__
                    if name != 'return':
                        type_name = None
                    else:
                        return_cb_type_name = var_type_name
                elif str(typ).startswith('typing.Union') and typ.__args__[1] == none_type:
                    type_name = name_map.get(typ.__args__[0].__name__, type_name)
                    type_name = f"{{{type_name} [optional]}}"
                else:
                    type_name = typ.__name__
            except Exception:
                type_name = "<<unrecognized>>"
            if type_name:
                type_name = name_map.get(type_name, type_name)
                if name == 'return':
                    response_type_name = type_name
                else:
                    params_doc = re.sub(f":param *{name} *:", f"@param {{{{{type_name}}}}} {name}", params_doc)
            else:
                params_doc = re.sub(f":param *{name}.*", "@REMOVE@", params_doc)
        lines = params_doc.splitlines()
        params_doc = ""
        remove_line = False
        # remove parameter that has been moved as a return callback function and documented as such:
        for line in lines:
            if '@REMOVE@' in line:
                remove_line = True
            elif not remove_line:
                params_doc += f"{line}\n"
            elif '@param' in line:
                remove_line = False
                params_doc += f"{line}\n"
        if return_cb_type_name:
            params_doc += \
                f"{tab}@return {{{{function({return_cb_type_name}) => null}}}} " \
                "callback to send streamed chunks to server"
        if callback == 'onreceive':
            cb_docs = f"""
{tab}@param {{function({response_type_name}, bool) => null}} {callback} callback invoked on each chunk
{tab}     received from server
{tab}@param {{function(int, str) => null}}  onerror  callback upon error, passing in response code and status text
"""
        else:
            cb_docs = f"""
{tab}@param {{function({response_type_name}) => null}} {callback} callback inoked,
{tab}     passing response from server on success
{tab}@param {{function(int, str) => null}}  onerror  callback upon error, passing in response code and status text
"""
        docs = f"""\n{tab}/*
{tab}{basic_doc.strip()}
{tab}A call will be made to The server and the response will be provided as the (first) parameter passed into {callback}
{tab}
{tab}{cb_docs.strip()}
{tab}{params_doc.strip()}
{tab}*/
"""
        lines = [line for line in docs.splitlines() if not line.strip().startswith(':return')]
        docs = '\n'.join(lines) + '\n'
        out.write(docs.encode(cls.ENCODING))

    @classmethod
    def _generate_request(cls, out: IO, route: str, api: API, tab: str):
        func = api._func
        sig = inspect.signature(func)
        arg_count = len(sig.parameters)
        if 'self' in sig.parameters or 'cls' in sig.parameters or 'this' in sig.parameters:
            arg_count -= 1
        if not api.name.startswith('_') and arg_count != len(api.arg_annotations):
            raise Exception(f"Not all arguments of '{api.qualname}' have type hints.  This is required for web_api")
        if api.has_streamed_response is True:
            callback = 'onreceive'
            state = 3
            api._content_type = 'text/streamed; charset=x-user-defined'
        else:
            callback = 'onsuccess'
            state = 'XMLHttpRequest.DONE'
        cls._generate_docs(out, api, tab, callback=callback)
        argnames = [param for param in api.arg_annotations.keys()]
        if func.__name__ == '_create':
            out.write(
                f"{tab}constructor({', '.join(argnames)}) {{\n".encode(
                    cls.ENCODING))
        else:
            name = func.__name__ if not api.name.startswith('_') else api.name[1:]
            static_text = "" if api.is_instance_method else "static "
            out.write(f"{tab}{static_text}{name}({callback}, onerror, {', '.join(argnames)}) {{\n".encode(cls.ENCODING))
        if api.method == RestMethod.GET:
            cls._generate_get_request(out=out, route=route, tab=tab,
                                      api=api,
                                      response_type=api.return_type,
                                      state=state,
                                      callback=callback)
        else:
            cls._generate_post_request(out=out, api=api, route=route, tab=tab,
                                       response_type=api.return_type,
                                       state=state,
                                       callback=callback)

    @classmethod
    def _generate_post_request(cls, out: IO,
                               api: API,
                               route: str,
                               tab: str,
                               response_type: Type,
                               state: str,
                               callback: str):
        argnames = [param for param in api.arg_annotations.keys()]
        tab += "   "
        return_codeblock = ""
        if api.has_streamed_request:
            return_codeblock = f"""
{tab}var onchunkready = function(chunk){{
{tab}    request.send(chunk);
{tab}}}
{tab}return onchunkready;
"""
            self_id_text, c = ("{\"self\": this.self_id}", '&') if api.is_instance_method else ("\"\"", '?')
            param_code = f"""
{tab}let params = {self_id_text};
{tab}let c = '{c}';
{tab}let map = {{{','.join(['"' + arg + '": ' + arg for arg in argnames])}}};
{tab}for (var param of [{", ".join(['"' + a + '"' for a in argnames])}]){{
{tab}    if (typeof map[param] !== 'undefined'){{
{tab}        let value = JSON.stringify(map[param])
{tab}        if (value[0] === '"'){{
{tab}            value = value.slice(1, -1)
{tab}        }}
{tab}        params += c + param + '=' + value;
{tab}        c= '&';
{tab}    }}
{tab}}}"""
            query = 'params'
            body = ''
        else:
            param_code = f"   {tab}\"self\": this.self_id,\n" if api.is_instance_method else ""
            param_code += ',\n'.join([f"{tab}   \"{argname}\": {argname}" for argname in argnames])
            param_code = f"""
{tab}let params = {{
{param_code}
{tab}}};"""
            query = '""'
            body = 'JSON.stringify(params)'
        convert_codeblock = cls._generate_streamed_response(response_type, api.has_streamed_response,
                                                            callback=callback, tab=tab)
        out.write(f"""
{tab}{param_code}
{tab}let request = new XMLHttpRequest();
{tab}request.seenBytes = 0;
{tab}request.open("POST", "{route}" + {query});
{tab}request.setRequestHeader('Content-Type', "{api.content_type}");
{tab}let buffered = null;
{tab}request.onreadystatechange = function() {{
{tab}   if (request.readyState == XMLHttpRequest.DONE && (request.status > 299 || request.status < 200)) {{
{tab}       onerror(request.status, request.statusText + ': ' + request.responseText);
{tab}   }} else if(request.readyState >= {state}) {{
{tab}      {convert_codeblock}
{tab}   }}
{tab}}}
{tab}request.send({body});
{tab}{return_codeblock}
""".encode(cls.ENCODING))
        tab = tab[:-3]
        out.write(f"{tab}}}\n".encode(cls.ENCODING))

    @classmethod
    def _generate_get_request(cls, out: IO,
                              api: API,
                              route: str,
                              tab: str,
                              response_type: Type,
                              state: str,
                              callback: str,):
        argnames = list(api.arg_annotations.keys())
        tab += "   "
        convert_codeblock = cls._generate_streamed_response(response_type, api.has_streamed_response,
                                                            callback=callback, tab=tab)
        if api.name == '_create':
            out.write(f"""
{tab}let request = new XMLHttpRequest();
{tab}let params = "";
{tab}let c = '?';
{tab}let map = {{{','.join(['"' + arg + '": ' + arg for arg in argnames])}}};
{tab}for (var param of [{", ".join(['"' + a + '"' for a in argnames])}]){{
{tab}    if (typeof map[param] !== 'undefined'){{
{tab}        let value = JSON.stringify(map[param])
{tab}        if (value[0] === '"'){{
{tab}            value = value.slice(1, -1)
{tab}        }}
{tab}        params += c + param + '=' + value;
{tab}        c= '&';
{tab}    }}
{tab}}}
{tab}request.open("GET", "{route}" + params, false);
{tab}request.setRequestHeader('Content-Type', "{api.content_type}");
{tab}request.send(null);
{tab}if (request.status === 200){{
{tab}       this.self_id = request.responseText;
{tab}}} else {{
{tab}      throw request.stats;
{tab}}}
""".encode(cls.ENCODING))
        else:
            self_id_text, c = ("{\"self\": this.self_id}", '&') if api.is_instance_method else ("\"\"", '?')
            out.write(f"""
{tab}let request = new XMLHttpRequest();
{tab}let params = {self_id_text};
{tab}let c = '{c}';
{tab}let map = {{{','.join(['"' + arg + '": ' + arg for arg in argnames])}}};
{tab}for (var param of [{", ".join(['"' + a + '"' for a in argnames])}]){{
{tab}    if (typeof map[param] !== 'undefined'){{
{tab}        let value = JSON.stringify(map[param])
{tab}        if (value[0] === '"'){{
{tab}            value = value.slice(1, -1)
{tab}        }}
{tab}        params += c + param + '=' + value;
{tab}        c= '&';
{tab}    }}
{tab}}}
{tab}request.open("GET", "{route}" + params);
{tab}request.setRequestHeader('Content-Type', "{api.content_type}");
{tab}let buffered = null;
{tab}request.onreadystatechange = function() {{
{tab}   if(request.readyState == XMLHttpRequest.DONE && (request.status < 200 || request.status > 299)){{
{tab}       onerror(request.status, request.statusText + ": " + request.responseText);
{tab}   }} else if (request.readyState >= {state}) {{
{tab}       {convert_codeblock}
{tab}   }}
{tab}}}
{tab}request.send();
""".encode(cls.ENCODING))
        tab = tab[:-3]
        out.write(f"{tab}}}\n".encode(cls.ENCODING))

    @classmethod
    def _generate_streamed_response(cls, response_type: Type, streamed_response: bool, callback: str, tab: str) -> str:
        if hasattr(response_type, '__dataclass_fields__'):
            convert = "JSON.parse(val)"
        elif str(response_type).startswith('typing.Dict') or str(response_type).startswith('typing.List'):
            convert = "JSON.parse(val)",
        else:
            convert = {str: "",
                       int: "parseInt(val)",
                       float: "parseFloat(val)",
                       bool: "'true'== val",
                       dict: "JSON.parse(val)",
                       list: "JSON.parse(val)",
                       None: "null"}.get(response_type) or 'request.response.substr(request.seenBytes)'
        if streamed_response and response_type not in [bytes, str, None]:
            convert_codeblock = f"""
{tab}    // TODO: Can we clean this up a little?
{tab}    let vals = request.response.substr(request.seenBytes).trim().split('\\0');
{tab}    for (var i = 0; i < vals.length; ++i) {{
{tab}       let val = vals[i];
{tab}       let done = (i == vals.length -1) && (request.readyState == XMLHttpRequest.DONE);
{tab}       if (val !== ''){{
{tab}          if (buffered != null){{{callback}(buffered, false); buffered = null;}}
{tab}          buffered = {convert};
{tab}          if (typeof buffered === 'numbered' && isNaN(buffered)){{
{tab}             buffered = null;
{tab}             onerror(-1, "Unable to convert server response '" + val + "' to expected type");
{tab}             break;
{tab}          }}
{tab}       }}
{tab}    }}
{tab}    if (buffered !== null && request.readyState == XMLHttpRequest.DONE){{{callback}(buffered, true);}}
{tab}    request.seenBytes = request.response.length;"""
        elif streamed_response and response_type == str:
            convert_codeblock = f"""
{tab}    // TODO: Can we clean this up a little?
{tab}    let chunk = request.response.substr(request.seenBytes).trim();
{tab}    let vals = chunk.length == 0?[]:chunk.split('\\0');
{tab}    if (buffered !== null){{{callback}(buffered, request.readyState == XMLHttpRequest.DONE); buffered = null; }}
{tab}    for (var i = 0; i < vals.length-1 ; ++i) {{
{tab}       let val = vals[i];
{tab}       {callback}(val, false);
{tab}    }}
{tab}    if (vals.length > 0){{buffered = vals[vals.length-1];}}
{tab}    if (buffered !== null && request.readyState == XMLHttpRequest.DONE){{{callback}(buffered, true);}}
{tab}    request.seenBytes = request.response.length;"""
        else:
            convert_codeblock = f"""
{tab}       var val = request.response.substr(request.seenBytes);
{tab}       var converted = {convert};
{tab}       if ((typeof converted == 'number') && isNaN(converted)){{
{tab}          onerror(-1, "Unable to convert '" + val + "' to expected type");
{tab}       }}
{tab}       {callback}(converted, request.readyState == XMLHttpRequest.DONE);
{tab}       request.seenBytes = request.response.length;"""
        return convert_codeblock
