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
            is_constructor: bool = False,
            expire_obj: bool = False,
            uuid_param: Optional[str] = None,
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
    :param is_constructor: set to True if API is static method return a class instnace, False oherwise (default)
    :param expire_obj: for instance methods only, epxire the object upon successful completion of that call
    :return: callable decorator
    """
    from .http import WebApplication
    if not isinstance(content_type, str):
        raise Exception("@web_api must be provided one str argument which is the content type")

    def wrapper(obj: Union[WebApi, staticmethod]):
        is_static = isinstance(obj, staticmethod)
        if not is_static and is_constructor:
            raise TypeError("@web_api's that are declared constructors must be static methods")
        if is_static and expire_obj:
            raise TypeError("@web_api's expire_obj param can only be set True for instance methods")
        if is_static:
            obj = obj.__func__
        if not inspect.ismethod(obj) and not inspect.isfunction(obj):
            raise TypeError("@web_api should only be applied to class methods")
        if obj.__name__.startswith('_'):
            raise TypeError("names of web_api methods must not start with underscore")
        # noinspection PyProtectedMember
        # clazz = WebApplication._instance_methods_class_map[obj] if not isinstance(obj, staticmethod) else None

        return WebApplication._func_wrapper(None,
                                            obj,
                                            is_instance_method=not is_static,
                                            method=method,
                                            content_type=content_type,
                                            is_constructor=is_constructor,
                                            expire_on_exit=expire_obj,
                                            uuid_param=uuid_param,
                                            preprocess=preprocess,
                                            postprocess=postprocess)

    return wrapper
