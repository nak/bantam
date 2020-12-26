from pathlib import Path
from typing import Type, Optional, Union

from aiohttp import web
from aiohttp.web import Application
from .decorators import web_api, RestMethod as MEnum, AsyncChunkGenerator, AsyncLineGenerator


_all__ = ['WebApplicaction', web_api, AsyncChunkGenerator, AsyncLineGenerator]


class WebApplication(Application):

    MethodEnum = MEnum

    class DuplicateRoute(Exception):
        pass

    routes_get = {}
    routes_post = {}

    @staticmethod
    def register_route_get(route: str, async_method) -> None:
        if route in WebApplication.routes_get or route in WebApplication.routes_post:
            raise WebApplication.DuplicateRoute(f"Route '{route}' already exists")
        WebApplication.routes_get[route] = async_method

    @staticmethod
    def register_route_post(route: str, async_method) -> None:
        if route in WebApplication.routes_post or route in WebApplication.routes_get:
            raise WebApplication.DuplicateRoute("Route '{route}' already exists")
        WebApplication.routes_post[route] = async_method

    def __init__(self, static_path: Optional[Union[Path, str]] = None):
        super().__init__()
        for route, api_get in self.routes_get.items():
            self.router.add_get(route, api_get)
        for route, api_post in self.routes_post.items():
            self.router.add_get(route, api_post)
        if static_path:
            self.add_routes([web.static('/static', str(static_path))])
