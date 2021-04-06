import inspect
from typing import Any, Callable, Awaitable, Union, Optional, Dict

from aiohttp.web import Request, Response
from aiohttp.web_response import StreamResponse

from bantam.api import RestMethod

WebApi = Callable[..., Awaitable[Any]]

_bantam_web_apis = {}


PreProcessor = Callable[[Request], Union[None, Dict[str, Any]]]
PostProcessor = Callable[[Union[Response, StreamResponse]], Union[Response, StreamResponse]]


def web_api(content_type: str, method: RestMethod = RestMethod.GET,
            preprocess: Optional[PreProcessor] = None,
            postprocess: Optional[PostProcessor] = None) -> Callable[[WebApi], WebApi]:
    """
    Decorator for class async method to register it as an API with the `WebApplication` class
    Decorated functions should be static class methods with parameters that are convertible from a string
    (things like float, int, str, bool).  Type hints must be provided and will be used to dynamically convert
    query parameeter strings to the right type.

    >>> class MyResource:
    ...
    ...   @web_api(content_type="text/html")
    ...   @staticmethod
    ...   def say_hello(name: str):
    ...      return f"Hi there, {name}!"

    Only GET calls with explicit parameters in the URL are support for now.  The above registers a route
    of the form:

    http://<host>:port>/MyRestAPI?name=Jill


    :param content_type: content type to disply (e.g., "text/html")
    :param method: one of MethodEnum rest api methods (GET or POST)
    :return: callable decorator
    """
    from .http import WebApplication
    if not isinstance(content_type, str):
        raise Exception("@web_api must be provided one str argument which is the content type")

    def wrapper(obj: Union[WebApi, staticmethod]):
        is_static = isinstance(obj, staticmethod)
        if is_static:
            obj = obj.__func__
        if not inspect.ismethod(obj) and not inspect.isfunction(obj):
            raise TypeError("@web_api should only be applied to class methods")
        if obj.__name__.startswith('_'):
            raise TypeError("names of web_api methods must not start with underscore")
        # noinspection PyProtectedMember
        # clazz = WebApplication._instance_methods_class_map[obj] if not isinstance(obj, staticmethod) else None

        return WebApplication._func_wrapper(obj, not is_static,
                                            method=method,
                                            content_type=content_type,
                                            preprocess=preprocess,
                                            postprocess=postprocess)

    return wrapper
