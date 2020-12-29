"""
Welcome to Bantam, a framework for running a web server that abstracts away the need to worry about manual
registration of routes.  The framework allows users to declare static methods of classes as part of a Web API,
and allows auto-generation of corresponding javascript APIs to match.  In this way the developer need not
worry about the underlying mechanisms of sending or processing web requests!

"""
import logging
from pathlib import Path
from ssl import SSLContext
from typing import Optional, Union, Dict, Callable, Iterable, Mapping, Any, Awaitable

from aiohttp import web
from aiohttp.abc import Request, StreamResponse
from aiohttp.log import web_logger
from aiohttp.web import Application, HostSequence
from aiohttp.web_routedef import UrlDispatcher
from aiohttp.web_app import _Middleware

from .decorators import web_api, RestMethod, AsyncChunkGenerator, AsyncLineGenerator, WebApi


_all__ = ['WebApplication', web_api, AsyncChunkGenerator, AsyncLineGenerator, 'AsyncApi', RestMethod]

AsyncApi = Callable[[Request], Awaitable[StreamResponse]]


class WebApplication:
    """
    Let's look at setting up a simple WebApplication on your localhost:

    >>> import asyncio
    ... from bantam.web import web_api, RestMethod, WebApplication
    ...
    ... class Greetings:
    ...
    ...   @web_api(content_type='text/html', method=RestMethod.GET)
    ...   @staticmethod
    ...   async def welcome(self, name: str) -> str:
    ...      return f"<html><body><p>Welcome, {name}!</p></body></html>"
    ...
    ...   @web_api(content_type='text/html', method=RestMethod.GET)
    ...   @staticmethod
    ...   async def goodbye(self, type_of_day: str) -> str:
    ...      return f"<html><body><p>Have a {type_of_day} day!</p></body></html>"
    ...
    ... app = WebApplication()
    ... asyncio.get_event_loop().run_until_complete(app.start()) # default to localhost HTTP on port 8080

    Saving this to a file, 'saultations.py', you can run this as so to start a server:

    .. code-block:: bash
       % python3 salutations.py

    Then open a browser to the following URL's:

    * http://localhost:8080/Greetings/welcome?name=Bob
    * http://localhost:8080/Greetings/goodbye?type_of_day=wonderful

    to display various salutiations.

    To explain this code, the *@web_api* decorator declares methods that are to mapped to a route. The route is determined
    by the class name, in this case *Greetings* and the method name.  The methods:

    #. Must be @staticmethod's
    #. Must provide all type hints for parameters and return value
    #. Must have parameters and return values of basic types (str, float, int bool) or a class that has both q serialize/deserialize method to convert to/from bytes

    There are a few other options for parameters and return type that will be discussed later on streaming. The query
    parameters are translated to the value and type expected by the Python API.  If the value is not convertible to
    the proper type, an error code along with reason are returned.

    The methods can also be declared POST.  In this case, they would be sent as part of the payload of the request
    (not query parameters) in a simple JSON dicetionary.
    """
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

    def __init__(self, *,
                 static_path: Union[Path, str],
                 logger: logging.Logger = web_logger,
                 router: Optional[UrlDispatcher] = None,
                 middlewares: Iterable[_Middleware] = (),
                 handler_args: Optional[Mapping[str, Any]] = None,
                 client_max_size: int = 1024 ** 2,
                 debug: Any = ..., ) -> None:  # mypy doesn't support ellipsis
        self._web_app = Application(logger=logger, router=router, middlewares=middlewares, handler_args=handler_args,
                                    client_max_size=client_max_size, debug=debug)
        for route, api_get in self.routes_get.items():
            self._web_app.router.add_get(route, api_get)
        for route, api_post in self.routes_post.items():
            self._web_app.router.add_post(route, api_post)
        if static_path:
            self._web_app.add_routes([web.static('/static', str(static_path))])
        self._started = False

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
        :param shutdown_timeout: force shutdwon if a shutdown call fails to take hold after this many seconds
        :param ssl_context: for HTTPS server; if not provided, will default to HTTP connectoin
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
