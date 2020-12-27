from pathlib import Path
from typing import Type, Optional, Union, Coroutine, Dict, Callable

from aiohttp import web
from aiohttp.web import Application
from .decorators import web_api, RestMethod as MEnum, AsyncChunkGenerator, AsyncLineGenerator


_all__ = ['WebApplicaction', web_api, AsyncChunkGenerator, AsyncLineGenerator]


class WebApplication(Application):

    MethodEnum = MEnum

    class DuplicateRoute(Exception):
        pass

    routes_get: Dict[str, Coroutine] = {}
    routes_post: Dict[str, Coroutine] = {}
    callables_get: Dict[str, Callable] = {}
    callables_post: Dict[str, Callable] = {}
    content_type: Dict[str, str] = {}

    @staticmethod
    def register_route_get(route: str, async_method, func: Callable, content_type: str) -> None:
        if route in WebApplication.routes_get or route in WebApplication.routes_post:
            raise WebApplication.DuplicateRoute(f"Route '{route}' already exists")
        WebApplication.routes_get[route] = async_method
        WebApplication.callables_get[route] = func
        WebApplication.content_type[route] = content_type

    @staticmethod
    def register_route_post(route: str, async_method, func: Callable, content_type: str) -> None:
        if route in WebApplication.routes_post or route in WebApplication.routes_get:
            raise WebApplication.DuplicateRoute("Route '{route}' already exists")
        WebApplication.routes_post[route] = async_method
        WebApplication.callables_post[route] = func
        WebApplication.content_type[route] = content_type

    def __init__(self, static_path: Optional[Union[Path, str]] = None):
        super().__init__()
        for route, api_get in self.routes_get.items():
            self.router.add_get(route, api_get)
        for route, api_post in self.routes_post.items():
            self.router.add_get(route, api_post)
        if static_path:
            self.add_routes([web.static('/static', str(static_path))])
