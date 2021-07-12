"""
Welcome to Bantam, a framework for running a web server, built on top of *aiohttp*,
poviding a convience-layer of abstraction.
The framework allows users to define a Python web API through static methods of classes,
and allows auto-generation of corresponding javascript APIs to match.  The developer need not
be concerned about the details of how to map routes nor to understand the details of HTTP transactions.
Ths developer need only focus on development of a web API as a Python interface.

Getting Started
---------------

Let's look at setting up a simple WebApplication on your localhost:

>>> import asyncio
... from bantam.http import web_api, RestMethod, WebApplication
...
... class Greetings:
...
...     @web_api(content_type='text/html', method=RestMethod.GET)
...     @staticmethod
...     async def welcome(name: str) -> str:
...         \"\"\"
...         Welcome someone
...
...         :@param name: name of person to greet
...         :return: a salutation of welcome
...         \"\"\"
...         return f"<html><body><p>Welcome, {name}!</p></body></html>"
...
...     @web_api(content_type='text/html', method=RestMethod.GET)
...     @staticmethod
...     async def goodbye(type_of_day: str) -> str:
...         \"\"\"
...         Tell someone goodbye by telling them to have a day (of the given type)
...
...         :@param type_of_day:  an adjective describe what type of day to have
...         :return: a saltation of welcome
...         \"\"\"
...         return f"<html><body><p>Have a {type_of_day} day!</p></body></html>"
...
... if __name__ == '__main__':
...     app = WebApplication()
...     asyncio.get_event_loop().run_until_complete(app.start()) # default to localhost HTTP on port 8080

Saving this to a file, 'saultations.py', you can run this start your server:

.. code-block:: bash

    % python3 salutations.py

Then open a browser to the following URL's:

* http://localhost:8080/Greetings/welcome?name=Bob
* http://localhost:8080/Greetings/goodbye?type_of_day=wonderful

to display various salutiations.

To explain this code, the *@web_api* decorator declares a method that is mapped to a route. The route is determined
by the class name, in this case *Greetings*, and the method name. Thus, the "welcome" method above, as a member of
*Greetings* class, is mapped to the route '/Greetings/welcome".  There are some rules about methods declared as *@web_api*:

#. They must be @staticmethod's.
#. They must provide all type hints for parameters and return value,
#. They must have parameters and return values of basic types (str, float, int bool) or a @dataclass class

The query parameters provided in the full URL are mapped to the parameters in the Python method.  For example,
the query parameter name=Box in the first uRL above maps to the *name* parameter of the *Greetings.welcome* method,
with 'Bob' as the value.
The query parameters are translated to the value and type expected by the
Python API. If the value is not convertible to the proper type, an error code along with reason are returned.
There are a few other options for parameters and return type that will be  discussed later on streaming.

The methods can also be declared as POST operations.  In this case, parameter values would be sent as part of the
payload of the request (not query parameters) as a simple JSON dictionary.

.. caution::

    Although the code prevents name collisions, the underlying (automated) routes do not, and a route must be unique.
    Thus, each pair of class/method declared as a @web_api must be unique, including across differing modules.

"""
import asyncio
from asyncio import Task

import docutils.core
import importlib
import inspect
import json
import os
import sys
import traceback
import types

from aiohttp import web
from aiohttp.web import (
    Application,
    Request,
    Response,
    StreamResponse,
)
from contextlib import suppress
from pathlib import Path
from ssl import SSLContext
from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    List,
    Mapping,
    Optional,
    Union,
    Type,
)

from . import HTTPException
from .conversions import from_str, to_str
from .decorators import (
    PreProcessor,
    PostProcessor,
    web_api,
    WebApi,
)
from .api import AsyncChunkIterator, AsyncLineIterator, RestMethod, API, APIDoc
from .js_async import JavascriptGeneratorAsync
from .js import JavascriptGenerator

_all__ = ['WebApplication', web_api, AsyncChunkIterator, AsyncLineIterator, 'AsyncApi', RestMethod]

AsyncApi = Callable[['WebApplication', Request], Awaitable[StreamResponse]]
PathLike = Union[Path, str]
MAX_CLIENTS = 1024 ** 2


def wrap(app, op):
    async def wrapper(request):
        return await op(app, request)
    return wrapper


# noinspection PyUnresolvedReferences
class WebApplication:
    """
    Main class for running a WebApplication server. See the docs for *aiohttp* for information on the various
    parameters.  Additional parameters are:

    :@param static_path: root path to where static files will be kept, mapped to a route "/static", if provided
    :@param js_bundle_name: the name of the javascript file, **without** exetnesion, where the client-side API
       will be generated, if provided
    """
    _context: Dict[Awaitable, Request] = {}
    _class_instance_methods: Dict[Type, List[API]] = {}
    _instance_methods_class_map: Dict[API, Type] = {}
    _instance_methods: List[API] = []
    _all_methods: List[API] = []

    class ObjectRepo:
        DEFAULT_OBJECT_EXPIRATION: int = 60*60*2   # in seconds = 1 hour

        instances: Dict[str, Any] = {}
        by_instance: Dict[Any, str] = {}
        expiry: Dict[str, Task] = {}

        @classmethod
        async def expire_obj(cls, obj_id: str, new_lease_time: int):
            if new_lease_time > 0:
                await asyncio.sleep(new_lease_time)
            if hasattr(cls.instances[obj_id], '__aexit__'):
                with suppress(Exception):
                    await cls.instances[obj_id].__aexit__(None, None, None)
            del cls.instances[obj_id]
            del cls.expiry[obj_id]

    class DuplicateRoute(Exception):
        """
        Raised if an attempt is made to register a web_api function under an existing route
        """
        pass

    routes_get: Dict[str, AsyncApi] = {}
    routes_post: Dict[str, AsyncApi] = {}
    callables_get: Dict[str, API] = {}
    callables_post: Dict[str, API] = {}

    def __init__(self,
                 *,
                 static_path: Optional[PathLike] = None,
                 js_bundle_name: Optional[str] = None,
                 handler_args: Optional[Mapping[str, Any]] = None,
                 client_max_size: int = MAX_CLIENTS,
                 using_async: bool = True,
                 debug: Any = ..., ) -> None:  # mypy doesn't support ellipsis
        if static_path is not None and not Path(static_path).exists():
            raise ValueError(f"Provided static path, {static_path} does not exist")
        self._static_path = static_path
        self._js_bundle_name = js_bundle_name
        self._using_async = using_async
        self._web_app = Application(handler_args=handler_args,
                                    client_max_size=client_max_size, debug=debug)
        if static_path:
            self._web_app.add_routes([web.static('/static', str(static_path))])
        self._started = False
        self._preprocessor: Optional[PreProcessor] = None
        self._postprocessor: Optional[PostProcessor] = None

    def _generate_rest_docs(self):
        rst_out = self._static_path.joinpath('_developer_docs.rst')
        html_out = self._static_path.joinpath('_developer_docs.html')

        def document_class(clazz_, doc_out):
            docs = clazz_.__doc__ or """<<no documentation provided>>"""
            title = f"Resource: {clazz_.__name__}"
            doc_out.write(f"""
{title}
{'-'*len(title)}

{docs.strip()}
""")

        with open(rst_out, 'w') as out:
            out.write("REST API DOCUMENTATION\n")
            out.write("======================\n\n")

            out.write("\nReST Resources and Methods")
            out.write("\n==========================\n")
            resources_seen = set()
            for (route, api), method in sorted(
                    [(item, RestMethod.GET) for item in WebApplication.callables_get.items()] +
                    [(item, RestMethod.POST) for item in WebApplication.callables_post.items()]
            ):
                resource, _ = route[1:].split('/', maxsplit=1)
                if resource not in resources_seen:
                    resources_seen.add(resource)
                    for clazz in WebApplication._class_instance_methods:
                        if clazz.__name__ == resource:
                            document_class(clazz, out)
                out.write(APIDoc.generate(api=api, flavor=APIDoc.Flavor.REST))
                out.write("\n")
        if html_out.exists():
            os.remove(html_out)
        css = """
        
        h2{
            margin: 1em 0 .6em 0;
            font-weight: normal;
            color: black;
            font-family: 'Hammersmith One', sans-serif;
            text-shadow: 0 -3px 0 rgba(255,255,255,0.8);
            position: relative;
            font-size: 30px;
            line-height: 40px;
            background-color: lightgrey;
            font-size:150%
        }

        h3 {
            margin: 1em 0 0.5em 0;
            color: #343434;
            font-size: 22px;
            line-height: 40px;
            font-weight: normal;
            font-family: 'Orienta', sans-serif;
            letter-spacing: 1px;
            font-style: italic;font-size: 90%; background-color: #fed8b1;
        }
        
        """
        css_dir: Path = self._static_path.joinpath('css')
        if not css_dir.exists():
            css_dir.mkdir(parents=True)
        css_file = css_dir.joinpath('docs.css')
        with open(css_file, 'w') as css_out:
            css_out.write(css)
        docutils.core.publish_file(
            source_path=str(rst_out),
            destination_path=str(html_out),
            writer_name="html",
            settings_overrides={'stylesheet_path': ','.join(["html4css1.css", str(css_file)])}
        )

    def set_preprocessor(self, processor: PreProcessor):
        self._preprocessor = processor

    @property
    def preprocessor(self):
        return self._preprocessor

    def set_postprocessor(self, processor: PostProcessor):
        self._postprocessor = processor

    @property
    def postprocessor(self):
        return self._postprocessor

    @classmethod
    def register_route_get(cls, route: str, async_handler: AsyncApi, api: API) -> None:
        """
        Register the given handler as a GET call. This should be called from the @web_api decorator, and
        rarely if ever called directly

        :param route: route to register under
        :param async_handler: the raw handler for handling an incoming Request and returning a Response
        :param api: the high-level deocrated web_api that will be invoked by the handler
        """
        if route in WebApplication.routes_get or route in cls.routes_post:
            existing = WebApplication.callables_get.get(route) or WebApplication.callables_post.get(route)
            raise WebApplication.DuplicateRoute(
                f"Route '{route}' associated with {api.module}.{api.name}"
                f" already exists here: {existing.module}.{existing.name} "
            )
        cls.routes_get[route] = async_handler
        cls.callables_get[route] = api

    @staticmethod
    def register_route_post(route: str, async_method: AsyncApi, api: API) -> None:
        """
        Register the given handler as a POST call.  This should be called from the @web_api decorator, and
        rarely if ever called directly

        :param route: route to register under
        :param async_method: the raw handler for handling an incoming Request and returning a Response
        :param api: web api (decorated as @web_api) instance
        """
        if route in WebApplication.routes_post or route in WebApplication.routes_get:
            existing = WebApplication.callables_get.get(route) or WebApplication.callables_post.get(route)
            raise WebApplication.DuplicateRoute(f"Route '{route}' associated with {api.module}.{api._func.__name__}"
                                                f" already exists here {existing.module}.{existing.name} ")
        WebApplication.routes_post[route] = async_method
        WebApplication.callables_post[route] = api

    async def start(self,
                    host: Optional[str] = None,
                    port: Optional[int] = None,
                    path: Optional[str] = None,
                    shutdown_timeout: float = 60.0,
                    ssl_context: Optional[SSLContext] = None,
                    backlog: int = 128,
                    handle_signals: bool = True,
                    reuse_address: Optional[bool] = None,
                    reuse_port: Optional[bool] = None,) -> None:
        """
        start the app

        :param host: host of app, if TCP based
        :param port: port to handle requests on (to listen on) if TCP based
        :param path: path, if using UNIX domain sockets to listen on (cannot specify both TCP and domain parameters)
        :param shutdown_timeout: force shutdown if a shutdown call fails to take hold after this many seconds
        :param ssl_context: for HTTPS server; if not provided, will default to HTTP connection
        :param backlog: number of unaccepted connections before system will refuse new connections
        :param handle_signals: gracefully handle TERM signal or not
        :param reuse_address: tells the kernel to reuse a local socket in TIME_WAIT state, without waiting for its
           natural timeout to expire. If not specified will automatically be set to True on UNIX.
        :param reuse_port: tells the kernel to allow this endpoint to be bound to the same port as other existing
            endpoints are bound to, so long as they all set this flag when being created. This option is not supported
            on Windows.
        """
        from aiohttp.web import _run_app as web_run_app
        for api in self._all_methods:
            if api.name in ['_expire']:
                continue
            mod = importlib.import_module(api.module)
            self._process_module_classes(mod, api)

        for route, api_get in self.routes_get.items():
            import logging
            log = logging.getLogger("LOG")
            log.error(f">>>>>>>>>> ROUTE {route}")
            self._web_app.router.add_get(route, wrap(self, api_get))
        for route, api_post in self.routes_post.items():
            self._web_app.router.add_post(route, wrap(self, api_post))

        if self._js_bundle_name:
            if self._static_path is None:
                raise ValueError("If 'js_bundle_name' is specified, 'static_path' cannot be None")
            static_path = Path(self._static_path)
            js_path = static_path.joinpath('js')
            if not js_path.exists():
                js_path.mkdir(parents=True)
            with open(js_path.joinpath(self._js_bundle_name + ".js"), 'bw') as out:
                if self._using_async:
                    JavascriptGeneratorAsync.generate(out=out, skip_html=False)
                else:
                    JavascriptGenerator.generate(out=out, skip_html=False)
        self._started = True
        if self._static_path:
            with suppress(Exception):
                self._generate_rest_docs()
        await web_run_app(app=self._web_app, host=host, port=port, path=path, shutdown_timeout=shutdown_timeout,
                          ssl_context=ssl_context, backlog=backlog, handle_signals=handle_signals,
                          reuse_address=reuse_address, reuse_port=reuse_port)

    async def shutdown(self) -> None:
        """
        Shutdown this server
        """
        if self._started:
            await self._web_app.shutdown()
            self._started = False

    # noinspection PyProtectedMember
    @classmethod
    def get_context(cls):
        i = 1
        frame = sys._getframe(i)
        try:
            # with debuggers, stack is polluted, so....
            while frame not in WebApplication._context:
                i += 1
                frame = sys._getframe(i)
        except IndexError:
            return None
        return WebApplication._context[frame].headers

    @classmethod
    def _process_module_classes(cls, mod: types.ModuleType, api: API):
        def process_class(clazz_: Type):
            if hasattr(clazz_, '_expire') or hasattr(clazz_, '_create'):
                raise TypeError("Classes with @web_api applied cannot have methods named _expire nor _create")

            # noinspection PyDecorator
            @staticmethod
            async def _create(*args, **kargs) -> str:
                self_id = None
                if '__uuid' in kargs or (api.uuid_param is not None and api.uuid_param in kargs):
                    self_id = kargs[api.uuid_param] if api.uuuid_param is not None else kargs['__uuid']
                    del kargs['__uuid']
                    if self_id in cls.ObjectRepo.instances:
                        raise HTTPException(404, f"UUid {self_id} already in use. uuid's must be unique")
                instance = clazz_(*args, **kargs)
                if hasattr(clazz_, '__aenter__'):
                    await instance.__aenter__()
                return instance

            clazz_._create = _create
            if hasattr(clazz_, '__init__') and hasattr(clazz_.__init__, '__annotations__'):
                clazz_._create.__annotations__ = clazz_.__init__.__annotations__ if hasattr(clazz_, '__init__') else {}
            else:
                clazz._create.__annotations__ = {}
            clazz_._create.__annotations__['return'] = str

            clazz_._create.__doc__ = clazz_.__init__.__doc__ if hasattr(clazz_, '__init__') else f"""
                Create an instance of {clazz_.__name__} on server, returning a unique string id for the instnace.  
                The instance will remain active until /{clazz_.__name__}/expire is invoked.  The sting is used for 
                instance-based ReST methods to act on the created instance on the server.

                :return: unqiue string id of instance created
                """
            clazz_._create.__qualname__ = f"{clazz_.__name__}._create"
            # noinspection PyProtectedMember
            cls._func_wrapper(clazz, clazz_._create, is_instance_method=False, is_constructor=True, expire_on_exit=False,
                              method=RestMethod.GET, content_type="text/plain")

            async def _expire(self, new_lease_time: int = cls.ObjectRepo.DEFAULT_OBJECT_EXPIRATION,
                              _uuid: Optional[str] = None) -> None:
                """
                Release/close an instance on the server that was created through invocation of _create for the
                associated resource
                """
                self_id = cls.ObjectRepo.by_instance.get(self)
                if self_id not in cls.ObjectRepo.instances:
                    raise HTTPException(code=404, msg=f"No such object with id {self_id}")
                cls.ObjectRepo.expiry[self_id].cancel()
                if cls.ObjectRepo.instances and new_lease_time <= 0:
                    await cls.ObjectRepo.expire_obj(self_id, 0)
                else:
                    cls.ObjectRepo.expiry[self_id] = asyncio.create_task(
                        cls.ObjectRepo.expire_obj(self_id, new_lease_time))

            clazz_._expire = _expire
            clazz_._expire.__doc__ = _expire.__doc__
            clazz_._expire.__name__ = 'expire'
            clazz_._expire.__qualname__ = f"{clazz_.__name__}.expire"

            # noinspection PyProtectedMember
            cls._func_wrapper(clazz, clazz_._expire, is_instance_method=True, expire_on_exit=False,
                              is_constructor=False, method=RestMethod.GET, content_type="text/plain")

        for clazz in [cls for _, cls in inspect.getmembers(mod) if inspect.isclass(cls)]:
            # noinspection PyProtectedMember
            method_found = any([item for item in inspect.getmembers(clazz) if item[1] == api._func])
            if method_found:
                api._clazz = clazz
            if method_found and (api in cls._instance_methods or api.is_constructor):
                if clazz not in cls._class_instance_methods or not cls._class_instance_methods.get(clazz):
                    process_class(clazz)
                cls._class_instance_methods.setdefault(clazz, []).append(api)
                cls._instance_methods_class_map[api] = clazz
                if api.is_constructor:
                    if api._func.__annotations__.get('return') != clazz.__name__:
                        raise TypeError("@web_api's declared as constructors must return that class's type")

                if api.expire_object:
                    async def wrapped(self, *args, **kargs):
                        try:
                            return await api._func(self, *args, **kargs)
                        finally:
                            if self in cls.ObjectRepo.by_instance:
                                uuid = cls.ObjectRepo.by_instance[self]
                                del cls.ObjectRepo.by_instance[self]
                                del cls.ObjectRepo.instances[uuid]

                    setattr(clazz, api.name, wrapped)
            elif method_found and api in cls._all_methods:
                if api.is_constructor:
                    if api._func.__annotations__.get('return') != clazz.__name__:
                        raise TypeError("@web_api's declared as constructors must return that class's type")
                cls._class_instance_methods.setdefault(clazz, [])  # create an empty list of instance methods at least

    @classmethod
    def _func_wrapper(cls, clazz, func: WebApi, is_instance_method: bool,
                      is_constructor: bool,
                      expire_on_exit: bool,
                      method: RestMethod,
                      content_type: str,
                      uuid_param: Optional[str] = None,
                      preprocess: Optional[PreProcessor] = None,
                      postprocess: Optional[PostProcessor] = None) -> WebApi:
        """
        Wraps a function as called from decorators.web_api to set up logic to invoke get or post requests

        :param func: function to wrap
        :param clazz: if function is instance method, provide owning class, otherwise None
        :return: function back, having processed as a web api and registered the route
        """
        api = API(clazz, func, method=method, content_type=content_type, is_instance_method=is_instance_method,
                  is_constructor=is_constructor, expire_on_exit=expire_on_exit, uuid_param=uuid_param)
        if is_instance_method:
            if not inspect.iscoroutinefunction(func) and not inspect.isasyncgenfunction(func):
                raise ValueError("the @web_api decorator can only be applied to classes with public "
                                 f"methods that are coroutines (async); see {api.qualname}")
            cls._instance_methods.append(api)
        else:
            if not inspect.iscoroutinefunction(func) and not inspect.isasyncgenfunction(func):
                raise ValueError("the @web_api decorator can only be applied to methods that are coroutines (async)")
        cls._all_methods.append(api)
        name = api.qualname.replace('__init__', 'create').replace('._expire', '.expire')
        name_parts = name.split('.')[-2:]
        route = '/' + '/'.join(name_parts)

        async def invoke(app: WebApplication, request: Request):
            nonlocal preprocess, postprocess
            try:
                preprocess = preprocess or app.preprocessor
                try:
                    addl_args = (preprocess(request) or {}) if preprocess else {}
                except Exception as e:
                    return Response(status=400, text=f"Error in preprocessing request: {e}")
                if method == RestMethod.GET:
                    # noinspection PyProtectedMember
                    response = await cls._invoke_get_api_wrapper(
                        api, content_type=content_type, request=request, **addl_args
                    )
                elif method == RestMethod.POST:
                    # noinspection PyProtectedMember
                    response = await cls._invoke_post_api_wrapper(
                        api, content_type=content_type, request=request, **addl_args
                    )
                else:
                    raise ValueError(f"Unknown method {method} in @web-api")
                try:
                    postprocess = postprocess or app.postprocessor
                    postprocess(response) if postprocess else response
                except Exception as e:
                    return Response(status=400, text=f"Error in post-processing of response: {e}")
                return response
            except Exception as e:
                return Response(status=500, text=f"Server error: {e}")

        invoke.clazz = WebApplication._instance_methods_class_map.get(api) if is_instance_method else None
        if method == RestMethod.GET:
            WebApplication.register_route_get(route, invoke, api)
        elif method == RestMethod.POST:
            WebApplication.register_route_post(route, invoke, api)
        else:
            raise ValueError(f"Unknown method {method} in @web-api")
        return func

    @classmethod
    async def _invoke_get_api_wrapper(cls, api: API, content_type: str, request: Request,
                                      **addl_args: Any) -> Union[Response, StreamResponse]:
        """
        Invoke the underlying GET web API from given request.  Called as part of setup in cls._func_wrapper

        :param func:  async function to be called
        :param content_type: http header content-type
        :param request: request to be processed
        :return: http response object
        """
        # noinspection PyUnresolvedReferences,PyProtectedMember
        cls._context[sys._getframe(0)] = request
        if api.has_streamed_request:
            raise TypeError("GET web_api methods does not support streaming requests")
        try:
            encoding = 'utf-8'
            items = content_type.split(';')
            for item in items:
                item = item.lower()
                if item.startswith('charset='):
                    encoding = item.replace('charset=', '')
            # report first param that doesn't match the Python signature:
            for k in [p for p in request.query if p not in api.arg_annotations and p != 'self']:
                return Response(
                    status=400,
                    text=f"No such parameter or missing type hint for param {k} in method {api.qualname}"
                )

            # convert incoming str values to proper type:
            kwargs = {k: _convert_request_param(v, api.arg_annotations[k]) if k != 'self' else v
                      for k, v in request.query.items()}
            if addl_args:
                kwargs.update(addl_args)
            if api.is_instance_method:
                # we are invoking a class method, and need to lookup instance
                self_id = kwargs.get('self').replace('\\', '')
                if self_id is None:
                    raise ValueError(
                        "A self request parameter is needed. No instance provided for call to instance method")
                instance = cls.ObjectRepo.instances.get(self_id)
                if instance is None:
                    raise ValueError(f"No instance found for request with 'self' id of {self_id}")
                del kwargs['self']
                result = api(instance, **kwargs)
            else:
                # call the underlying function:
                result = api(**kwargs)
            if inspect.isasyncgen(result):
                #################
                #  streamed response through async generator:
                #################
                # underlying function has yielded a result rather than turning
                # process the yielded value and allow execution to resume from yielding task
                content_type = "text-streamed; charset=x-user-defined"
                response = StreamResponse(status=200, reason='OK', headers={'Content-Type': content_type})
                await response.prepare(request)
                try:
                    # iterate to get the one (and hopefully only) yielded element:
                    # noinspection PyTypeChecker
                    async for res in result:
                        serialized = _serialize_return_value(res, encoding)
                        if not isinstance(res, bytes):
                            serialized += b'\n'
                        await response.write(serialized)
                except Exception as e:
                    print(str(e))
                await response.write_eof()
                return response
            else:
                #################
                #  regular response
                #################
                result = await result
                instance = result
                if api.is_constructor:
                    if hasattr(api.clazz, 'jsonrepr'):
                        repr = api.clazz.jsonrepr(result)
                        uuid = repr.get(api.uuid_param)
                        content_type = 'application/json'
                        result = json.dumps(repr)
                    else:
                        uuid = kwargs.get(api.uuid_param) or hex(id(result))
                        result = uuid
                    cls.ObjectRepo.instances[uuid] = instance
                    cls.ObjectRepo.by_instance[instance] = uuid
                    cls.ObjectRepo.expiry[uuid] = asyncio.create_task(cls.ObjectRepo.expire_obj(
                    uuid, cls.ObjectRepo.DEFAULT_OBJECT_EXPIRATION))
                else:
                    result = _serialize_return_value(result, encoding)
                return Response(status=200, body=result if result is not None else b"Success",
                                content_type=content_type)
        except TypeError as e:
            return Response(status=400, text=f"Improperly formatted query: {str(e)}\n{traceback.format_exc()}")
        except HTTPException as e:
            return Response(status=e.status_code, text=f"{e}: \n{traceback.format_exc()}")
        except Exception as e:
            return Response(status=500, text=f"{e}: \n{traceback.format_exc()}")
        finally:
            # noinspection PyUnresolvedReferences,PyProtectedMember
            del cls._context[sys._getframe(0)]

    @classmethod
    async def _invoke_post_api_wrapper(cls, api: API, content_type: str, request: Request,
                                       **addl_args: Any) -> Union[Response, StreamResponse]:
        """
        Invoke the underlying POST web API from given request. Called as part of setup in cls._func_wrapper

        :param api:  API wrapping async function to be called
        :param content_type: http header content-type
        :param request: request to be processed
        :return: http response object
        """
        async def line_by_line_response(req: Request):
            reader = req.content
            chunk = True
            while not reader.is_eof() and chunk:
                chunk = await reader.readline()
                yield chunk
            last = await reader.readline()
            if last:
                yield last

        def streamed_bytes_arg_value(req: Request):
            async def iterator(packet_size: int):
                reader = req.content
                chunk = True
                while not reader.is_eof() and chunk:
                    chunk = await reader.read(packet_size)
                    yield chunk

            return iterator

        # noinspection PyUnresolvedReferences,PyProtectedMember
        cls._context[sys._getframe(0)] = request
        encoding = 'utf-8'
        items = content_type.split(';')
        for item in items:
            if item.startswith('charset='):
                encoding = item.replace('charset=', '')
        if not request.can_read_body:
            raise TypeError("Cannot read body for request in POST operation")
        try:
            kwargs: Dict[str, Any] = {}
            if api.has_streamed_request:
                key, typ = api.async_arg_annotations.items()[0]
                if typ == bytes:
                    kwargs = {key: await request.read()}
                elif typ == AsyncLineIterator:
                    kwargs = {key: line_by_line_response(request)}
                elif typ == AsyncChunkIterator:
                    kwargs = {key: streamed_bytes_arg_value(request)}
                kwargs.update({k: _convert_request_param(v, api.synchronous_arg_annotations[k]) if k != 'self' else v
                               for k, v in request.query.items() if k in api.synchronous_arg_annotations})
            else:
                # treat payload as json string:
                bytes_response = await request.read()
                json_dict = json.loads(bytes_response.decode('utf-8'))
                for k in [p for p in json_dict if p not in api.arg_annotations and p != 'self']:
                    return Response(
                        status=400,
                        text=f"No such parameter or missing type hint for param {k} in method {api.qualname}"
                    )

                # convert incoming str values to proper type:
                kwargs.update(dict(json_dict))
            # call the underlying function:
            if addl_args:
                kwargs.update(addl_args)
            if api.is_instance_method:
                self_id = kwargs.get('self')
                if self_id is None:
                    raise ValueError("No instance provided for call to instance method")
                instance = cls.ObjectRepo.instances.get(self_id)
                if instance is None:
                    raise ValueError(f"No instance id found for request {self_id}")
                del kwargs['self']
                awaitable = api(instance, **kwargs)
                if api.expire_object:
                    del cls.ObjectRepo.instances[self_id]
            else:
                awaitable = api(**kwargs)
            if inspect.isasyncgen(awaitable):
                #################
                #  streamed response through async generator:
                #################
                # underlying function has yielded a result rather than turning
                # process the yielded value and allow execution to resume from yielding task
                async_q = asyncio.Queue()
                content_type = "text/streamed; charset=x-user-defined"
                response = StreamResponse(status=200, reason='OK', headers={'Content-Type': content_type})
                await response.prepare(request)
                try:
                    # iterate to get the one (and hopefully only) yielded element:
                    # noinspection PyTypeChecker
                    async for res in awaitable:
                        serialized = _serialize_return_value(res, encoding)
                        if not isinstance(res, bytes):
                            serialized += b'\n'
                        await response.write(serialized)
                except Exception as e:
                    print(str(e))
                    await async_q.put(None)
                await response.write_eof()
            else:
                #################
                #  regular response
                #################
                result = _serialize_return_value(await awaitable, encoding)
                return Response(status=200, body=result if result is not None else b"Success",
                                content_type=content_type)

        except TypeError as e:
            return Response(status=400, text=f"Improperly formatted query: {str(e)}")
        except HTTPException as e:
            return Response(status=e.status_code, text=str(e))
        except Exception as e:
            return Response(status=500, text=str(e))
        finally:
            # noinspection PyUnresolvedReferences,PyProtectedMember
            del cls._context[sys._getframe(0)]


def _convert_request_param(value: str, typ: Type) -> Any:
    """
    Convert rest request string value for parameter to given Python type, returning an instance of that type

    :param value: value to convert
    :param typ: Python Type to convert to
    :return: converted instance, of the given type
    :raises: TypeError if value can not be converted/deserialized
    """
    try:
        return from_str(value, typ)
    except Exception as e:
        raise TypeError(f"Converting web request string to Python type {typ}: {e}")


def _serialize_return_value(value: Any, encoding: str) -> bytes:
    """
    Serialize a Python value into bytes to return through a Rest API.  If a basic type such as str, int or float, a
    simple str conversion is done, then converted to bytes.  If more complex, the conversion will invoke the
    'serialize' method of the value, raising TypeError if such a method does not exist or does not have a bare
    (no-parameter) signature.

    :param value: value to convert
    :return: bytes serialized from value
    """
    try:
        if value is None:
            return bytes()
        return to_str(value).encode(encoding)
    except Exception as e:
        raise TypeError(f"Converting response '{value}' from Python type '{type(value)}' to string: {e}")
