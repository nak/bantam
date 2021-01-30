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
... from bantam.web import web_api, RestMethod, WebApplication
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
import sys
from pathlib import Path
from ssl import SSLContext
from typing import Optional, Union, Dict, Callable, Iterable, Mapping, Any, Awaitable

from aiohttp import web
from aiohttp.abc import Request, StreamResponse
from aiohttp.web import Application, HostSequence
from aiohttp.web_routedef import UrlDispatcher
from aiohttp.web_app import _Middleware

from .decorators import (
    AsyncChunkIterator,
    AsyncLineIterator,
    PreProcessor,
    PostProcessor,
    RestMethod,
    web_api,
    WebApi,
)
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


class WebApplication:
    """
    Main class for running a WebApplication server. See the docs for *aiohttp* for information on the various
    parameters.  Additional parameters are:

    :@param static_path: root path to where static files will be kept, mapped to a route "/static", if provided
    :@param js_bundle_name: the name of the javascript file, **without** exetnesion, where the client-side API
       will be generated, if provided
    """
    _context: Dict[Awaitable, Request] = {}

    class DuplicateRoute(Exception):
        """
        Raised if an attempt is made to register a web_api function under an existing route
        """
        pass

    routes_get: Dict[str, AsyncApi] = {}
    routes_post: Dict[str, AsyncApi] = {}
    callables_get: Dict[str, WebApi] = {}
    callables_post: Dict[str, WebApi] = {}
    content_type: Dict[str, str] = {}

    def __init__(self,
                 *,
                 static_path: Optional[PathLike] = None,
                 js_bundle_name: Optional[str] = None,
                 router: Optional[UrlDispatcher] = None,
                 middlewares: Iterable[_Middleware] = (),
                 handler_args: Optional[Mapping[str, Any]] = None,
                 client_max_size: int = MAX_CLIENTS,
                 using_async: bool = True,
                 debug: Any = ..., ) -> None:  # mypy doesn't support ellipsis
        if static_path is not None and not Path(static_path).exists():
            raise ValueError(f"Provided static path, {static_path} does not exist")
        if js_bundle_name:
            if static_path is None:
                raise ValueError("If 'js_bundle_name' is specified, 'static_path' cannot be None")
            static_path = Path(static_path)
            js_path = static_path.joinpath('js')
            if not js_path.exists():
                js_path.mkdir(parents=True)
            with open(js_path.joinpath(js_bundle_name + ".js"), 'bw') as out:
                if using_async:
                    JavascriptGeneratorAsync.generate(out=out, skip_html=False)
                else:
                    JavascriptGenerator.generate(out=out, skip_html=False)
        self._web_app = Application(router=router, middlewares=middlewares, handler_args=handler_args,
                                    client_max_size=client_max_size, debug=debug)
        for route, api_get in self.routes_get.items():
            self._web_app.router.add_get(route, wrap(self, api_get))
        for route, api_post in self.routes_post.items():
            self._web_app.router.add_post(route, wrap(self, api_post))
        if static_path:
            self._web_app.add_routes([web.static('/static', str(static_path))])
        self._started = False
        self._preprocessor: Optional[PreProcessor] = None
        self._postprocessor: Optional[PostProcessor] = None

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

    @staticmethod
    def register_route_get(route: str, async_handler: AsyncApi, async_web_api: WebApi, content_type: str) -> None:
        """
        Register the given handler as a GET call. This should be called from the @web_api decorator, and
        rarely if ever called directly

        :param route: route to register under
        :param async_handler: the raw handler for handling an incoming Request and returning a Response
        :param async_web_api: the high-level deocrated web_api that will be invoked by the handler
        :param content_type: http content-type header value
        """
        if route in WebApplication.routes_get or route in WebApplication.routes_post:
            existing = WebApplication.callables_get.get(route) or WebApplication.callables_post.get(route)
            raise WebApplication.DuplicateRoute(f"Route '{route}' associated with {async_web_api.__module__}.{async_web_api.__name__}"
                                                f" already exists here: {existing.__module__}.{existing.__name__} ")
        WebApplication.routes_get[route] = async_handler
        WebApplication.callables_get[route] = async_web_api
        WebApplication.content_type[route] = content_type

    @staticmethod
    def register_route_post(route: str, async_method: AsyncApi, func: WebApi, content_type: str) -> None:
        """
        Register the given handler as a POST call.  This should be called from the @web_api decorator, and
        rarely if ever called directly

        :param route: route to register under
        :param async_handler: the raw handler for handling an incoming Request and returning a Response
        :param async_web_api: the high-level deocrated web_api that will be invoked by the handler
        :param content_type: http content-type header value
        """
        if route in WebApplication.routes_post or route in WebApplication.routes_get:
            existing = WebApplication.callables_get.get(route) or WebApplication.callables_post.get(route)
            raise WebApplication.DuplicateRoute(f"Route '{route}' associated with {func.__module__}.{func.__name__}"
                                                f" already exists here {existing.__module__}.{existing.__name__} ")
        WebApplication.routes_post[route] = async_method
        WebApplication.callables_post[route] = func
        WebApplication.content_type[route] = content_type

    async def start(self,
                    host: Optional[Union[str, HostSequence]] = None,
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
        self._started = True
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
