import inspect
import re
from collections import Coroutine
from typing import Dict, Tuple, List, IO, Type

from bantam.decorators import RestMethod
from bantam.web import WebApplication


class JavascriptGenerator:
    """
    Class for generating equivalent javascript API from Python web_api routes
    """

    ENCODING = 'utf-8'
    
    class Namespace:
        
        def __init__(self):
            self._namespaces: Dict[str, JavascriptGenerator.Namespace] = {}
            self._classes: Dict[str, List[Tuple[RestMethod, str, Coroutine]]] = {}
        
        def add_module(self, module: str) -> 'JavascriptGenerator.Namespace':
            if '.' in module:
                my_name, child = module.split('.', maxsplit=1)
                m = self._namespaces.setdefault(my_name, JavascriptGenerator.Namespace())
                m = m.add_module(child)
            else:
                my_name = module
                m = self._namespaces.setdefault(my_name, JavascriptGenerator.Namespace())
            return m

        def add_class_and_route_get(self, module, class_name, route, api):
            m = self.add_module(module)
            m._classes.setdefault(class_name, []).append((RestMethod.GET, route, api))

        def add_class_and_route_post(self, module, class_name, route, api):
            m = self.add_module(module)
            m._classes.setdefault(class_name, []).append((RestMethod.POST, route, api))

        @property
        def child_namespaces(self):
            return self._namespaces
        
        @property
        def classes(self):
            return self._classes

    @classmethod
    def generate(cls, out: IO, skip_html: bool = True) -> None:
        """
        Generate javascript code from registered routes

        :param out: stream to write to
        :param skip_html: whether to skip entries of content type 'text/html' as these are generally not used in direct
           javascript calls
        """
        namespaces = cls.Namespace()
        for route, api in WebApplication.callables_get.items():
            content_type = WebApplication.content_type.get(route)
            if not skip_html or (content_type.lower() != 'text/html'):
                classname = route[1:].split('/')[0]
                namespaces.add_class_and_route_get(api.__module__, classname, route, api)
        for route, api in WebApplication.callables_post.items():
            content_type = WebApplication.content_type.get(route)
            if not skip_html or (content_type.lower() != 'text/html'):
                classname = route[1:].split('/')[0]
                namespaces.add_class_and_route_post(api.__module__, classname, route, api)
        tab = ""

        def process_namespace(ns: cls.Namespace, parent_name: str):
            nonlocal tab
            for name_, child_ns in ns.child_namespaces.items():
                out.write(f"{parent_name}.{name_} = class {{}}\n".encode(cls.ENCODING))
                process_namespace(child_ns, parent_name + '.' + name_)
            for class_name, routes in ns.classes.items():
                out.write(f"\n{parent_name}.{class_name} = class {{\n".encode(cls.ENCODING))
                tab += "   "
                out.write(f"{tab}constructor(site){{this.site = site;}}\n".encode(cls.ENCODING))
                for method, route_, api in routes:
                    content_type = WebApplication.content_type.get(route_) or 'text/plain'
                    is_streamed = inspect.isasyncgenfunction(api)
                    cls._generate_request(out, route_, method, api, tab, content_type, streamed_resp=is_streamed)
                tab = tab[:-3]
                out.write(f"}};\n".encode(cls.ENCODING))  # for class end

        for name, namespace in namespaces.child_namespaces.items():
            name = "bantam." + name
            out.write("\nclass bantam {};\n".encode(cls.ENCODING))
            out.write(f"{name} = class {{}};\n".encode(cls.ENCODING))
            tab += "   "
            process_namespace(namespace, name)

    @classmethod
    def _generate_docs(cls, out: IO, api, tab, callback: str = 'onsuccess') -> None:
        def prefix(text: str, tab: str):
            new_text = ""
            for line in text.splitlines():
                new_text += tab + line.strip() + '\n'
            return new_text
        basic_doc_parts = prefix(api.__doc__ or "<<No API documentation provided>>", tab).\
            replace(':return:', ':returns:').split(':param', maxsplit=1)
        if len(basic_doc_parts) == 1:
            basic_doc = basic_doc_parts[0]
            params_doc = ""
        else:
            basic_doc, params_doc = basic_doc_parts
            params_doc = ':param ' + params_doc

        annotations = dict(api.__annotations__)
        name_map = {'str': 'string', 'bool': 'boolean', 'int': 'number [int]', 'float': 'number [float]'}
        response_type_name = "<<unspecified>>"
        return_cb_type_name = None
        type_name = None
        for name, typ in annotations.items():
            try:
                if hasattr(typ, 'deserialize'):
                    type_name = f"str serialization of {name_map.get(type_name, type_name)}"
                elif hasattr(typ, '_name') and typ._name == 'AsyncGenerator':
                    var_type_name = typ.__args__[1].__name__
                    if name != 'return':
                        type_name = None
                    else:
                        return_cb_type_name = var_type_name
                elif str(typ).startswith('typing.Union') and typ.__args__[1] == type(None):
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
            params_doc += f"{tab}@return {{{{function({return_cb_type_name}) => null}}}} callback to send streamed chunks to server"
        if callback == 'onreceive':
            cb_docs = f"""
{tab}@param {{function({response_type_name}, bool) => null}} {callback} callback invoked on each chunk received from server 
{tab}@param {{function(int, str) => null}}  onerror  callback upon error, passing in response code and status text
"""
        else:
            cb_docs = f"""
{tab}@param {{function({response_type_name}) => null}} {callback} callback inoked, passing in response from server on success
{tab}@param {{function(int, str) => null}}  onerror  callback upon error, passing in response code and status text
"""
        docs = f"""\n{tab}/*
{tab}{basic_doc.strip()}
{tab}
{tab}{cb_docs.strip()}
{tab}{params_doc.strip()}
{tab}*/
"""
        lines = [line for line in docs.splitlines() if not line.strip().startswith(':return')]
        docs = '\n'.join(lines) + '\n'
        out.write(docs.encode(cls.ENCODING))

    @classmethod
    def _generate_request(cls, out: IO, route: str, method: RestMethod,
                          api: Coroutine, tab: str, content_type: str, streamed_resp: bool):
        annotations = dict(api.__annotations__)
        response_type = annotations.get('return')
        if 'return' not in annotations:
            response_type = 'string'
        else:
            if hasattr(response_type, '_name') and response_type._name == "AsyncGenerator":
                response_type = response_type.__args__[1]
            del annotations['return']
        if api.__code__.co_argcount != len(annotations):
            raise Exception(f"Not all arguments of '{api.__module__}.{api.__name__}' have type hints.  This is required for web_api")
        if streamed_resp is True:
            callback = 'onreceive'
            state = 3
        else:
            callback = 'onsuccess'
            state = 'XMLHttpRequest.DONE'
        cls._generate_docs(out, api, tab, callback=callback)
        argnames = [param for param in annotations.keys()]
        out.write(f"{tab}{api.__name__}({callback}, onerror, {', '.join(argnames)}) {{\n".encode(cls.ENCODING))
        if method == RestMethod.GET:
            cls._generate_get_request(out=out, route=route, api=api, tab=tab, content_type=content_type,
                                      annotations=annotations,
                                      response_type=response_type,
                                      state=state,
                                      callback=callback,
                                      streamed_response=streamed_resp)
        else:
            cls._generate_post_request(out=out, route=route, api=api, tab=tab, content_type=content_type,
                                       annotations=annotations,
                                       response_type=response_type,
                                       state=state,
                                       callback=callback,
                                       streamed_response=streamed_resp)

    @classmethod
    def _generate_post_request(cls, out: IO,
                               route: str,
                               api: Coroutine,
                               tab: str,
                               content_type: str,
                               annotations: Dict[str, Type],
                               response_type: str,
                               state: str,
                               callback: str,
                               streamed_response: bool):
        argnames = [param for param in annotations.keys()]
        tab += "   "
        return_codeblock = ""
        request_streamed = False
        for name, typ in dict(annotations).items():
            if hasattr(typ, '_name') and typ._name == 'AsyncGenerator':
                del annotations[name]
                request_streamed = True
                return_codeblock = f"""
{tab}var onchunkready = function(chunk){{
{tab}    request.send(chunk);
{tab}}}
{tab}return onchunkready;
"""
                break

        convert = {str: "",
                   int: f"parseInt(val)",
                   float: f"parseFloat(val)",
                   bool: f"'true'== val",
                   None: "null"}.get(response_type) or 'request.response.substr(request.seenBytes)'
        if request_streamed:
            param_code = f"""
{tab}let params = "";
{tab}let c = '?';
{tab}let map = {{{','.join(['"' + arg + '": ' + arg for arg in argnames])}}};
{tab}for (var param of [{", ".join(['"' + a + '"' for a in argnames])}]){{
{tab}    if (typeof map[param] !== 'undefined'){{
{tab}        params += c + param + '=' + map[param];
{tab}        c= ';';
{tab}    }}
{tab}}}"""
            query = 'params'
            body=''
        else:
            param_code = ',\n'.join([f"{tab}   \"{argname}\": {argname}" for argname in argnames])
            param_code = f"""
{tab}let params = {{
{param_code}
{tab}}};"""
            query = '""'
            body = 'JSON.stringify(params)'

        if streamed_response and response_type not in [str, None]:
                convert_codeblock = f"""
{tab}    // TODO: Can we clean this up a little? 
{tab}    let vals = request.response.substr(request.seenBytes).trim().split('\\n');
{tab}    request.seenBytes = 0; 
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
        else:
            convert_codeblock = f"""
{tab}       var val = request.response.substr(request.seenBytes);
{tab}       var converted = {convert};
{tab}       if ((typeof converted == 'number') && isNaN(converted)){{
{tab}          onerror(-1, "Unable to convert '" + val + "' to expected type");
{tab}       }}
{tab}       {callback}(converted, request.readyState == XMLHttpRequest.DONE);
{tab}      request.seenBytes = request.response.length;"""

        out.write(f"""
{tab}{param_code}
{tab}let request = new XMLHttpRequest();
{tab}request.seenBytes = 0;
{tab}request.open("POST", this.site + "{route}" + {query});
{tab}request.setRequestHeader('Content-Type', "{content_type}");
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
                               route: str,
                               api: Coroutine,
                               tab: str,
                               content_type: str,
                               annotations: Dict[str, Type],
                               response_type: str,
                               state: str,
                               callback: str,
                               streamed_response: bool):
        argnames = [param for param in annotations.keys()]
        tab += "   "
        convert = {str: "",
                   int: f"parseInt(val)",
                   float: f"parseFloat(val)",
                   bool: f"'true'== val",
                   None: "null"}.get(response_type) or 'request.response.substr(request.seenBytes)'

        if response_type in [str, None]:
            convert_codeblock = f"""
{tab}       var converted = {convert};
{tab}       if ((typeof converted == 'number') && isNaN(converted)){{
{tab}          onerror(-1, "Unable to convert '" + val + "' to expected type");
{tab}       }}
{tab}      {callback}(converted, request.readyState == XMLHttpRequest.DONE); 
{tab}      request.seenBytes = request.response.length;"""
        else:
            convert_codeblock = f"""
{tab}    let vals = request.response.substr(request.seenBytes).trim().split('\\n');
{tab}    request.seenBytes = 0; 
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

        out.write(f"""
{tab}let request = new XMLHttpRequest();
{tab}let params = "";
{tab}let c = '?';
{tab}let map = {{{','.join(['"'+ arg+ '": ' + arg for arg in argnames])}}};
{tab}for (var param of [{", ".join(['"' + a + '"' for a in argnames])}]){{
{tab}    if (typeof map[param] !== 'undefined'){{
{tab}        params += c + param + '=' + map[param];
{tab}        c= ';';
{tab}    }}
{tab}}}
{tab}request.open("GET", this.site + "{route}" + params);
{tab}request.setRequestHeader('Content-Type', "{content_type}");
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
