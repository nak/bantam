import inspect
from collections import Coroutine
from typing import Dict, Tuple, List, IO

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
                    if inspect.isasyncgenfunction(api):
                        if method == RestMethod.GET:
                            cls._generate_get_request(out, route_, api, tab, content_type, streamed_resp=True)
                        else:
                            cls._generate_post_request(out, route_, api, tab, content_type, streamed_resp=True)
                    else:
                        if method == RestMethod.GET:
                            cls._generate_get_request(out, route_, api, tab, content_type, streamed_resp=False)
                        else:
                            cls._generate_post_request(out, route_, api, tab, content_type, streamed_resp=False)
                tab = tab[:-3]
                out.write(f"}};\n".encode(cls.ENCODING))  # for class end

        for name, namespace in namespaces.child_namespaces.items():
            name = "bantam." + name
            out.write("\nclass bantam {};\n".encode(cls.ENCODING))
            out.write(f"{name} = class {{}};\n".encode(cls.ENCODING))
            tab += "   "
            process_namespace(namespace, name)

    @classmethod
    def _generate_docs(cls, out: IO, api, return_type, tab, callback: str = 'onsuccess') -> None:
        def prefix(text: str, tab: str):
            new_text = ""
            for line in text.splitlines():
                new_text += tab + line.strip() + '\n'
            return new_text
        return_type_name = 'bytes' if (return_type == bytes or
                                       getattr(return_type, '_name', None) == 'AsyncGenerator') \
            else return_type.__name__
        out.write(f"""\n{tab}/*
{tab}{(prefix(api.__doc__, tab) or "<<No API documentation provided>>").replace(':returns:', 'response:').replace(':return:', '@response:')}
{tab}@param {{({return_type_name}, bool) => Any}} {callback} callback invoked on successful response, 
{tab}    with the first parambeing the response from the server (typed according to underlying Python API),
{tab}    and the second indicating  whether  the response is completed (for streamed responses)
{tab}@param {{(int, str) => null}}  onerror  callback upon error, passing in response code and status text
{tab}*/
""".replace(':param ', '@param ').encode(cls.ENCODING))

    @classmethod
    def _generate_post_request(cls, out: IO, route: str, api: Coroutine, tab: str, content_type: str, streamed_resp: bool):
        annotations = dict(api.__annotations__)
        return_type = annotations.get('return')
        if return_type is None:
            return_type = str
        else:
            return_type = return_type.__args__[1]
        if 'return' in annotations:
            del annotations['return']
        if streamed_resp:
            callback = 'onreceive'
            condition2 = 3
        else:
            callback = 'onsuccess'
            condition2 = 'XMLHttpRequest.DONE'

        argnames = [param for param in annotations.keys()]
        cls._generate_docs(out, api, return_type, tab, callback=callback)
        out.write(f"{tab}{api.__name__}({', '.join(argnames)}, onreceive, onerror) {{\n".encode(cls.ENCODING))
        tab += "   "
        convert = {str: '(',
                   int: 'parseInt(',
                   float: 'parseFloat(',
                   bool: "('true'==",
                   None: "(null"}.get(return_type) or '('
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
{tab}request.seenBytes = 0;
{tab}request.open("POST", this.site + "{route}");
{tab}request.setRequestHeader('Content-Type', "{content_type}");
{tab}request.onreadystatechange = function() {{
{tab}   if (request.readyState == XMLHttpRequest.DONE && (request.status > 299 || request.status < 200)) {{
{tab}       onerror(request.status, request.statusText);
{tab}   }} else if(request.readyState >= {condition2}) {{
{tab}       var newData = request.responseText.substr(xhr.seenBytes);
{tab}       {callback}({convert}newData), request.readyState == XMLHttpResponse.DONE);
{tab}   }}
{tab}}}
{tab}request.send(JSON.stringify(params));
""".encode(cls.ENCODING))
        tab = tab[:-3]
        out.write(f"{tab}}}\n".encode(cls.ENCODING))

    @classmethod
    def _generate_get_request(cls, out: IO, route: str, api: Coroutine, tab: str, content_type: str,
                              streamed_resp: bool):
        annotations = dict(api.__annotations__)
        return_type = annotations.get('return')
        if 'return' in annotations:
            del annotations['return']
        argnames = [param for param in annotations.keys()]
        if streamed_resp:
            callback = 'onreceive'
            condition2 = 3
        else:
            callback = 'onsuccess'
            condition2 = 'XMLHttpRequest.DONE'
        cls._generate_docs(out, api, return_type, tab, callback=callback)
        out.write(f"{tab}{api.__name__}( onsuccess, onerror, {', '.join(argnames)}) {{\n".encode(cls.ENCODING))
        tab += "   "
        convert = {str: '(',
                   int: 'parseInt(',
                   float: 'parseFloat(',
                   bool: "('true'==",
                   None: "(null"}.get(return_type) or '('
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
{tab}request.onreadystatechange = function() {{
{tab}   if(request.readyState == XMLHttpRequest.DONE && (request.status < 200 || request.status > 299)){{
{tab}       onerror(request.status, request.statusText + ": " + request.responseText);
{tab}   }} else if (request.readyState >= {condition2}) {{
{tab}       {callback}({convert}request.response), request.readyState == XMLHttpRequest.DONE);
{tab}   }}
{tab}}}
{tab}request.send();
""".encode(cls.ENCODING))
        tab = tab[:-3]
        out.write(f"{tab}}}\n".encode(cls.ENCODING))
