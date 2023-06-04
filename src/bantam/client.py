"""
Bantam provides and abstraction to easily declare Python clients to interact with a Bantam web application.
Bantam even provide a means of auto-generating the code for clients.

To auto-generate client code, an application *bantam_generate* is provided:

.. code-block:: bash

   bantam_generate <module-name> [<suffix>]

This will generate code to stdout for client classes that match the @web_api's defined in the provided module.  Each
client class is named the same as the class it is derived from, unless the optional second argument is provided. If
provided the class name will be appended with this suffix.

You can also generate this code manually if desired, of course, following the pattern from auto-generation of code.
This code provides an abstraction to the @web_api interface implementation, stand-alone from the implementation code
if desired. (e.g. providing a stand-alone client package for install separate from the implementation server-side
package.)

"""
import inspect
import json
from abc import ABC
from functools import wraps
from typing import Any, Dict, TypeVar, Optional, Type

import aiohttp

from bantam import conversions
from bantam.api import API, RestMethod

C = TypeVar('C', bound="WebInterface")


# noinspection PyProtectedMember
class WebInterface(ABC):

    _clients: Dict[str, Any] = {}

    @classmethod
    def _generate_url_args(cls, kwargs, self_id: Optional[str] = None):
        if self_id is None and not kwargs:
            return ''
        return (f'?self={self_id}&' if self_id is not None else '?') + \
            '&'.join([f"{k}={conversions.to_str(v)}" for k, v in kwargs.items() if v is not None])

    @classmethod
    def _add_class_method(cls, clazz: Type, impl_name: str, end_point: str, method,
                          common_headers: dict):
        # class/static methods
        # noinspection PyProtectedMember
        # noinspection PyProtectedMember
        name = method.__name__
        api: API = method._bantam_web_api
        base_url = f"{end_point}/{impl_name}/{name}"

        # noinspection PyDecorator,PyShadowingNames
        @classmethod
        @wraps(method)
        async def class_method(cls_, *args, **kwargs_):
            nonlocal api, end_point
            # noinspection PyBroadException
            try:
                arg_spec = inspect.getfullargspec(api._func)
            except Exception:
                arg_spec = inspect.getfullargspec(api._func.__func__)
            kwargs_.update({
                arg_spec.args[n + 1]: arg for n, arg in enumerate(args)
            })
            # noinspection PyBroadException
            rest_method = api._func._bantam_web_api.method
            if rest_method.value == RestMethod.GET.value:
                url_args = cls._generate_url_args(kwargs=kwargs_)
                url = f"{base_url}{url_args}"
                async with aiohttp.ClientSession(timeout=api.timeout, headers=common_headers) as session:
                    async with session.get(url) as resp:
                        resp.raise_for_status()
                        data = (await resp.content.read()).decode('utf-8')
                        if api.is_constructor:
                            if hasattr(clazz, 'jsonrepr'):
                                repr_ = clazz.jsonrepr(data)
                                self_id = repr_[api.uuid_param or 'uuid']
                            else:
                                repr_ = json.loads(data)
                                self_id = repr_[api.uuid_param or 'uuid']
                            return cls_(self_id)
                        return conversions.from_str(data, api.return_type)
            else:
                payload = json.dumps({conversions.to_str(k): conversions.normalize_to_json_compat(v)
                                      for k, v in kwargs_.items()})
                async with aiohttp.ClientSession(timeout=api.timeout, headers=common_headers) as session:
                    async with session.post(base_url, data=payload) as resp:
                        resp.raise_for_status()
                        data = (await resp.content.read()).decode('utf-8')
                        if api.is_constructor:
                            self_id = json.loads(data)[api.uuid_param or 'uuid']
                            return cls_(self_id)
                        return conversions.from_str(data, api.return_type)

        setattr(clazz, name, class_method)

    @classmethod
    def _add_class_method_streamed(cls, clazz: Type, impl_name: str, end_point: str, method,
                                   common_headers: dict):
        if not hasattr(method, '_bantam_web_api'):
            raise SyntaxError(f"All methods of class WebClient most be decorated with '@web_api'")
        # noinspection PyProtectedMember
        if method._bantam_web_api.has_streamed_request:
            raise SyntaxError(f"Streamed request for WebClient's are not supported at this time")
        # noinspection PyProtectedMember

        name = method.__name__
        api: API = method._bantam_web_api
        base_url = f"{end_point}/{impl_name}/{name}"

        # noinspection PyDecorator,PyUnusedLocal
        @classmethod
        async def class_method_streamed(cls_, *args, **kwargs):
            nonlocal api, end_point
            # noinspection PyBroadException
            try:
                arg_spec = inspect.getfullargspec(api._func)
            except Exception:
                arg_spec = inspect.getfullargspec(api._func.__func__)
            kwargs.update({
                arg_spec.args[n + 1]: arg for n, arg in enumerate(args)
            })
            rest_method = api._func._bantam_web_api.method
            if rest_method.value == RestMethod.GET.value:
                url_args = cls._generate_url_args(kwargs=kwargs)
                url = f"{base_url}{url_args}"
                async with aiohttp.ClientSession(timeout=api.timeout, headers=common_headers) as session:
                    async with session.get(url) as resp:
                        resp.raise_for_status()
                        async for data, _ in resp.content.iter_chunks():
                            if data:
                                if api.return_type == str and data[-1] == 0:
                                    data = data[:-1]
                                data = data.decode('utf-8')
                                yield conversions.from_str(data, api.return_type)
            else:
                payload = json.dumps({conversions.to_str(k): conversions.normalize_to_json_compat(v)
                                      for k, v in kwargs.items()})
                async with aiohttp.ClientSession(timeout=api.timeout, headers=common_headers) as session:
                    async with session.post(base_url, data=payload) as resp:
                        async for data, _ in resp.content.iter_chunks():
                            resp.raise_for_status()
                            if data:
                                data = data.decode('utf-8')
                                yield conversions.from_str(data, api.return_type)

        setattr(clazz, name, class_method_streamed)

    @classmethod
    def _add_instance_method(cls, clazz: Type, impl_name: str, end_point: str, method,
                             common_headers: dict):
        # class/static methods
        # noinspection PyProtectedMember
        # noinspection PyProtectedMember
        name = method.__name__
        api: API = method._bantam_web_api
        base_url = f"{end_point}/{impl_name}/{name}"

        # noinspection PyDecorator,PyShadowingNames
        @wraps(method)
        async def instance_method(self, *args, **kwargs_):
            nonlocal api, end_point
            # noinspection PyBroadException
            try:
                arg_spec = inspect.getfullargspec(api._func)
            except Exception:
                arg_spec = inspect.getfullargspec(api._func.__func__)
            kwargs_.update({
                arg_spec.args[n]: arg for n, arg in enumerate(args)
            })
            # noinspection PyBroadException
            rest_method = api._func._bantam_web_api.method
            if rest_method.value == RestMethod.GET.value:
                url_args = cls._generate_url_args(self_id=self.self_id, kwargs=kwargs_)
                url = f"{base_url}{url_args}"
                async with aiohttp.ClientSession(timeout=api.timeout, headers=common_headers) as session:
                    async with session.get(url) as resp:
                        resp.raise_for_status()
                        data = (await resp.content.read()).decode('utf-8')
                        return conversions.from_str(data, api.return_type)
            else:
                kwargs_['self'] = self.self_id
                payload = json.dumps({conversions.to_str(k): conversions.normalize_to_json_compat(v)
                                      for k, v in kwargs_.items()})
                async with aiohttp.ClientSession(timeout=api.timeout, headers=common_headers) as session:
                    async with session.post(base_url, data=payload) as resp:
                        resp.raise_for_status()
                        data = (await resp.content.read()).decode('utf-8')
                        if api.is_constructor:
                            self_id = json.loads(data)['self_id']
                            return clazz(self_id)
                        return conversions.from_str(data, api.return_type)

        setattr(clazz, name, instance_method)

    @classmethod
    def _add_instance_method_streamed(cls, clazz: Type, impl_name: str, end_point: str, method,
                                      common_headers: dict):
        # class/static methods
        # noinspection PyProtectedMember
        # noinspection PyProtectedMember
        name = method.__name__
        api: API = method._bantam_web_api
        base_url = f"{end_point}/{impl_name}/{name}"

        async def instance_method_streamed(self, *args, **kwargs_):
            nonlocal api, end_point, base_url
            arg_spec = inspect.getfullargspec(api._func)
            kwargs_.update({
                arg_spec.args[n + 1]: arg for n, arg in enumerate(args)
            })
            rest_method = api.method
            if rest_method == RestMethod.GET:
                url_args = cls._generate_url_args(self_id=self.self_id, kwargs=kwargs_)
                url = f"{base_url}{url_args}"
                async with aiohttp.ClientSession(timeout=api.timeout, headers=common_headers) as session:
                    async with session.get(url) as resp:
                        resp.raise_for_status()
                        async for data, _ in resp.content.iter_chunks():
                            if data:
                                if api.return_type == str and data[-1] == 0:
                                    data = data[:-1]
                                data = data.decode('utf-8')
                                yield conversions.from_str(data, api.return_type)
            else:
                url = f"{base_url}?self={self.self_id}"
                kwargs_['self'] = self.self_id
                payload = json.dumps({k: conversions.to_str(v) for k, v in kwargs_.items()})
                async with aiohttp.ClientSession(timeout=api.timeout, headers=common_headers) as session:
                    async with session.post(url, data=payload) as resp:
                        resp.raise_for_status()
                        async for data, _ in resp.content.iter_chunks():
                            if data:
                                if api.return_type == str and data[-1] == 0:
                                    data = data[:-1]
                                data = data.decode('utf-8')
                                yield conversions.from_str(data, api.return_type)
        setattr(clazz, name, instance_method_streamed)

    # noinspection PyPep8Naming
    @classmethod
    def Client(cls: C, end_point: str, impl_name: Optional[str] = None,
               common_headers: Optional[dict] = None) -> C:
        if cls == WebInterface:
            raise Exception("Must call Client with concrete class of WebInterface, not WebInterface itself")
        if impl_name is None:
            if not cls.__name__.endswith('Interface'):
                raise Exception("Call to Client must specify impl_name explicitly since class name does not end in "
                                "'Interface'")
            impl_name = cls.__name__[:-len('Interface')]
        while end_point.endswith('/'):
            end_point = end_point[:-1]
        key = f"{cls.__name__}.{end_point}"
        if key in WebInterface._clients:
            return WebInterface._clients[key]

        class Impl:

            def __init__(self, self_id: str):
                super().__init__()
                self._id = self_id

            @property
            def self_id(self):
                return self._id

        non_class_methods = inspect.getmembers(cls, predicate=inspect.isfunction)
        for name, method in non_class_methods:
            if isinstance(inspect.getattr_static(cls, name), staticmethod):
                if hasattr(method, '_bantam_web_api'):
                    raise Exception(f"Static method {name} of {cls.__name__} cannot have @web_api decorator. "
                                    "WebInterface's can only have instance and class methods that are @web_api's")
                continue
            if not inspect.iscoroutinefunction(method) and not inspect.isasyncgenfunction(method):
                raise Exception(f"Function {name} of {cls.__name__} is not async as expected.")
            if isinstance(inspect.getattr_static(cls, name), staticmethod):
                raise Exception(f"Method {name} of {cls.__name__}")
            else:
                if inspect.isasyncgenfunction(method):
                    cls._add_instance_method_streamed(Impl, impl_name, end_point, method, common_headers)
                else:
                    cls._add_instance_method(Impl, impl_name, end_point, method, common_headers)

        class_methods = inspect.getmembers(cls, predicate=inspect.ismethod)
        for name, method in class_methods:
            if name == 'Client' or name.startswith('_'):
                continue
            if not inspect.iscoroutinefunction(method) and not inspect.isasyncgenfunction(method):
                raise Exception(f"Function {name} of {cls.__name__} is not async as expected.")
            if inspect.isasyncgenfunction(method):
                cls._add_class_method_streamed(Impl, impl_name, end_point, method, common_headers)
            else:
                cls._add_class_method(Impl, impl_name, end_point, method, common_headers)

        WebInterface._clients[key] = Impl
        return Impl
