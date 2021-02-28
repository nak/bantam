"""
Bantam provides the ability to auto-generate client-side javascript code to abstract the details of makting
HTTP requests to the server.  This abstraction implies that the developer never need to know about routes,
formulating URLs, how to make a POST request, how to stream data over HTTP, etc!

To generate client side code, create a Python source file -- let's name it generator.py --
and import all of the classes containing @web_api's
to be generated. Then add the main entry poitn to generate the javascript code, like so:

>>> from bantam.js_async import JavascriptGeneratorAsync
... from salutations import Greetings
...
... if __name__ == '__main__':
...     with open('salutations.js', 'bw') as output:
...        JavascriptGeneratorAsync.generate(out=output, skip_html=True)

Run the script as so:

.. code-block:: bash

    % python generate.py

With the above Greetings example, the generated javasctipt code will mimic the Python:

.. code-block:: javascript
    :caption: javascript code auto-generated from Python server's web API

    class bantam {};
    bantam.salutations = class {};
    bantam.salutations.Greetings = class {

          /*
          Welcome someone
          The response will be provided as the (first) parameter passed into onsuccess

          @param {{string}} name name of person to greet
          */
          welcome(name) {
             ...
          }

           /*
           Tell someone goodbye by telling them to have a day (of the given type)
           The response will be provided as the (first) parameter passed into onsuccess

           @param {{string}} type_of_day adjective describing type of day to have
           */
          goodbye(type_of_day) {
            ...
          }
    };

The code maintains the same hierarchy in namespaces as modules in Python, albeit under a global *bantam* namespace.
This prevents potential namespace collisions.  The javascript API mimics the signature of the Python API, including
async generators/iterator usage.


"""
import re
from aiohttp.web_response import Response, StreamResponse
from typing import Coroutine, Callable, Awaitable, Union
from typing import Dict, Tuple, List, IO, Type
from urllib.request import Request

from bantam.decorators import RestMethod, AsyncChunkIterator, AsyncLineIterator

AsyncApi = Callable[[Request], Awaitable[Union[Response, StreamResponse]]]


class JavascriptGeneratorAsync:
    """
    Class for generating equivalent javascript API from Python web_api routes
    """

    ENCODING = 'utf-8'

    BANTAM_CORE = """
class bantam {
    
    static compute_query(param_map){
        let c = '?';
        let params = '';
        for (var param in param_map){
             if (typeof param_map[param] !== 'undefined'){
                 params += c + param + '=' + JSON.stringify(param_map[param]);
                 c= ';';
             }
        }
        return params;
    }
    
    static async fetch_GET(route, content_type, param_map, convert){
        let result = await fetch(route + bantam.compute_query(param_map), 
                    {method:'GET', headers: {'Content-Type': content_type}});
        if (result.status < 200 || result.status > 299){
            let statusBody = await result.body.getReader().read();
            statusBody = result.statusText + ": " + new TextDecoder().decode(statusBody.value);
            let stats = {status: result.status, statusText: statusBody};
            throw stats;
        }
        return convert(result.text());
    }
    
    static async *fetch_GET_streamed(route, content_type, param_map, convert, return_is_bytes){
        let result = await fetch(route + bantam.compute_query(param_map), {method:'GET', headers: {'Content-Type': content_type}});
        let reader = await result.body.getReader();
        while (true){
            if (result.status < 200 || result.status > 299){
                let statusBody = await result.body.getReader().read();
                statusBody = result.statusText + ": " + new TextDecoder().decode(statusBody.value);
                let stats = {status: result.status, statusText: statusBody};
                throw stats;
            }
            let resp = await reader.read();            
            if (resp.done){
                break;
            }
            if (return_is_bytes){
               yield resp.value;
            } else {
               let value = new TextDecoder().decode(resp.value);
               for (var val of value.split('\\n')){
                   if(val){
                      yield convert(val);
                   }
               }
           }
        }
    }

    static async fetch_POST(route, content_type, param_map, convert, streamed_param){
        let params;
        let requestBody;
        if (typeof streamed_param !== 'undefined'){
            params = bantam.compute_query(param_map);
            requestBody = new ReadableStream({
                async start(controller){
                    let encoder = new TextEncoder();
                    for await (var chunk of streamed_param){
                        controller.enqueue(encoder.encode(chunk));
                    }
                    controller.close();
                }
            });  
        } else {
            params = '';
            requestBody = JSON.stringify(param_map);
        }
        try{
            let result = await fetch(route + params, 
                               {method:'POST', headers: {'Content-Type': content_type},
                                body: requestBody});

            if (result.status < 200 || result.status > 299){
                let statusBody = await result.body.getReader().read();
                statusBody = result.statusText + ": " + new TextDecoder().decode(statusBody.value);
                let stats = {status: result.status, statusText: statusBody};
                throw stats;
            }
            return convert(result.text());
        } catch (error) {
            if (error.message === 'Failed to fetch'){
                throw new Error("Streamed requests not supported by this browser");
            }
            throw error;
        }
    }

    static async * fetch_POST_streamed(route, content_type, param_map, convert, return_is_bytes, streamed_param){
        let body;
        if (typeof streamed_param !== 'undefined'){
            let requestBody = new ReadableStream({
                async start(controller){
                    let encoder = new TextEncoder();
                    for await (var chunk of streamed_param){
                        controller.enqueue(encoder.encode(chunk));
                    }
                    controller.close();
                }
            });
            try{
                body = await fetch(route + bantam.compute_query(param_map), {method:'POST', headers: {'Content-Type': content_type},
                                           body: requestBody});
            } catch (error) {
                if (error.message === 'Failed to fetch'){
                    throw new Error("Streamed requests not supported by this browser");
                }
                throw error;
            }
        } else {
            body = await fetch(route, {method:'POST', headers: {'Content-Type': content_type},
                                       body: JSON.stringify(param_map)});
        }
        let reader = await body.body.getReader();
        while (true){
            if (body.status < 200 || body.status > 299){
                let statusBody = await result.body.getReader().read();
                statusBody = result.statusText + ": " + new TextDecoder().decode(statusBody.value);
                let stats = {status: result.status, statusText: statusBody};
                throw stats;
            }
            let resp = await reader.read();            
            if (resp.done){
                break;
            }
            if (return_is_bytes){
               yield resp.value;
            } else {
               let value = new TextDecoder().decode(resp.value);
               for (var val of value.split('\\n')){
                   if(val){
                      yield convert(val);
                   }
               }
           }
        }
    }
    
    static convert_int(text){
        let converted = parseInt(text);
        if (typeof converted === 'numbered' && isNaN(buffered)){
              let stats ={status:-1, statusText:"Unable to convert server response '" + val + "' to int"};
              throw stats;
         }
         return converted;
    }
    
    static convert_str(text){
        return text;
    }
    
    static convert_bytes(text){
        let encoder = new TextEncoder();
        return encoder.encode(text);
    }
    
    convert_float(text){
        let converted = parseFloat(text);
        if (typeof converted === 'numbered' && isNaN(buffered)){
             let stats = {status:-1, statusText:"Unable to convert server response '" + val + "' to float"};
             throw stats;
         }
         return converted;    
    }
    
    static convert_bool(text){
        return text === 'true';
    }
    
    static convert_None(text){
        return null;
    }
    
    static convert_complex(text){
        return JSON.parse(text);
    }
    
};
"""
    
    class Namespace:
        
        def __init__(self):
            self._namespaces: Dict[str, JavascriptGeneratorAsync.Namespace] = {}
            self._classes: Dict[str, List[Tuple[RestMethod, str, Coroutine]]] = {}
        
        def add_module(self, module: str) -> 'JavascriptGeneratorAsync.Namespace':
            if '.' in module:
                my_name, child = module.split('.', maxsplit=1)
                m = self._namespaces.setdefault(my_name, JavascriptGeneratorAsync.Namespace())
                m = m.add_module(child)
            else:
                my_name = module
                m = self._namespaces.setdefault(my_name, JavascriptGeneratorAsync.Namespace())
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
        from bantam.web import WebApplication
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
                for method, route_, api in routes:
                    content_type = WebApplication.content_type.get(route_) or 'text/plain'
                    cls._generate_request(out, route_, method, api, tab, content_type)
                tab = tab[:-3]
                out.write(f"}};\n".encode(cls.ENCODING))  # for class end

        for name, namespace in namespaces.child_namespaces.items():
            name = "bantam." + name
            ni = '\n'
            out.write(f"{ni}{cls.BANTAM_CORE};{ni}".encode(cls.ENCODING))
            out.write(f"{name} = class {{}};\n".encode(cls.ENCODING))
            tab += "   "
            process_namespace(namespace, name)

    @classmethod
    def _generate_docs(cls, out: IO, api: AsyncApi, tab) -> None:
        def prefix(text: str, tab: str):
            new_text = ""
            for line in text.splitlines():
                new_text += tab + line.strip() + '\n'
            return new_text
        basic_doc_parts = prefix(api.__doc__ or "<<No API documentation provided>>", tab).split(':param', maxsplit=1)
        if len(basic_doc_parts) == 1:
            basic_doc = basic_doc_parts[0]
            params_doc = ""
        else:
            basic_doc, params_doc = basic_doc_parts
            params_doc = ':param ' + params_doc

        annotations = dict(api.__annotations__)
        name_map = {'str': 'string', 'bool': 'boolean', 'int': 'number [int]', 'float': 'number [float]'}
        type_name = None
        for name, typ in annotations.items():
            try:
                if hasattr(typ, 'deserialize'):
                    type_name = f"str serialization of {name_map.get(type_name, type_name)}"
                elif hasattr(typ, '_name') and typ._name == 'AsyncGenerator':
                    if name != 'return':
                        type_name = 'async generator of byte data'
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
                    params_doc = re.sub(f":return*:", f"@return {{{{{type_name}}}}}", params_doc)
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
                remove_line = True  # start of removal until next @param line is reached
            elif not remove_line:
                params_doc += f"{line}\n"
            elif '@param' in line:
                remove_line = False
                params_doc += f"{line}\n"

        docs = f"""\n{tab}/*
{tab}{basic_doc.strip()}
{tab}{params_doc.strip()}
{tab}*/
"""
        lines = [line for line in docs.splitlines() if not line.strip().startswith(':return')]
        docs = '\n'.join(lines) + '\n'
        out.write(docs.encode(cls.ENCODING))

    @classmethod
    def _generate_request(cls, out: IO, route: str, method: RestMethod,
                          api: AsyncApi, tab: str, content_type: str):
        annotations = dict(api.__annotations__)
        response_type = annotations.get('return')
        streamed_resp = False
        if 'return' not in annotations:
            response_type = 'string'
        else:
            if hasattr(response_type, '_name') and response_type._name == "AsyncGenerator":
                response_type = response_type.__args__[1]
                streamed_resp = True
                content_type = 'text/streamed; charset=x-user-defined'
            del annotations['return']

        offset = 1 if 'self' in api.__code__.co_varnames else 0
        if api.__code__.co_argcount - offset != len(annotations):
            raise Exception(f"Not all arguments of '{api.__module__}.{api.__name__}' have type hints.  This is required for web_api")
        cls._generate_docs(out, api, tab)
        argnames = list(annotations.keys())
        out.write(f"{tab}static async{'*' if streamed_resp else ''} {api.__name__}({', '.join(argnames)}) {{\n".encode(cls.ENCODING))
        async_annotations = [a for a in annotations.items() if a[1] in (AsyncChunkIterator, AsyncLineIterator)]
        if async_annotations:
            if len(async_annotations) > 1:
                raise TypeError("Only one parameter may be streamed")
            streamed_param, _ = async_annotations[0]
            argnames.remove(streamed_param)
        else:
            streamed_param = None
        if hasattr(response_type, '__dataclass_fields__'):
            convert = "convert_complex"
        else:
            convert = {str: "convert_str",
                       int: "convert_int",
                       float: "convert_float",
                       bool: "convert_bool",
                       bytes: "convert_bytes",
                       dict: "convert_complex",
                       list: "convert_complex",
                       None: "convert_None"}[response_type]
        tab += "   "
        self_param_code = f"{tab}  \"self\": this.self_id{',' if argnames else ''}" + '\n' if offset == 1 else ""
        param_code = ',\n'.join([f"{tab}   \"{argname}\": {argname}" for argname in argnames])
        param_code = f"""
{tab}let params = {{
{self_param_code}{param_code}
{tab}}}"""
        out.write(param_code.encode('utf-8'))
        if streamed_resp:
            out.write(f"""
{tab}for await (var chunk of bantam.fetch_{method.value}_streamed("{route}",
{tab}                    "{content_type}", 
{tab}                    params, 
{tab}                    bantam.{convert},
{tab}                    {str(response_type == bytes).lower()}
{tab}                    {f", {streamed_param}" if streamed_param else ""})){{
{tab}   yield chunk;
{tab}}}
{tab[:-3]}}}
""".encode('utf-8'))
        else:
            out.write(f"""
{tab}return await bantam.fetch_{method.value}("{route}", "{content_type}", params,
{tab}           bantam.{convert}, {f", {streamed_param}" if streamed_param else ""});
{tab[:-3]}}}
""".encode('utf-8'))
