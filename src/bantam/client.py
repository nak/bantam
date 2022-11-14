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
package.

"""
import json
import inspect
from abc import ABC
from typing import TypeVar, Type, Optional, Any

import aiohttp

from bantam import conversions
from bantam.api import RestMethod, API


T = TypeVar('T', bound="WebClient")


class WebInterface(ABC):

    # noinspection PyPep8Naming
    @classmethod
    def Client(cls: Type[T], impl_name: Optional[str] = None):

        # noinspection PyProtectedMember
        class ClientFactory:
            _cache = {}

            def __getitem__(self: T, end_point: str) -> Any:
                if end_point in ClientFactory._cache:
                    return ClientFactory._cache[end_point]
                while end_point.endswith('/'):
                    end_point = end_point[:-1]

                # noinspection PyProtectedMember
                class ClientImpl(cls):

                    end_point = None
                    _clazz = cls
                    if not impl_name and not cls.__name__.endswith('Interface'):
                        raise SyntaxError("You must either supply an explicit name in Client for implementing class, "
                                          "or name the class <implement-class-name>Interface (aka wit a suffix of "
                                          "'Interface'")
                    else:
                        _impl_name = impl_name or cls.__name__[:-9]

                    def __init__(self, self_id: str):
                        self._self_id = self_id

                    @classmethod
                    def add_instance_method(cls, name_: str, method_):
                        # instance method
                        if name_ in ('Client', '_construct'):
                            return
                        if not hasattr(method_, '_bantam_web_api'):
                            raise SyntaxError(f"All methods of class WebClient most be decorated with '@web_api'")
                        # noinspection PyProtectedMember
                        if method_._bantam_web_api.has_streamed_request:
                            raise SyntaxError(f"Streamed request for WebClient's are not supported at this time")
                        # noinspection PyProtectedMember
                        api: API = method_._bantam_web_api

                        async def instance_method(this, *args, **kwargs_):
                            nonlocal api
                            arg_spec = inspect.getfullargspec(api._func)
                            kwargs_.update({
                                arg_spec.args[n+1]: arg for n, arg in enumerate(args)
                            })
                            rest_method = api.method
                            while cls.end_point.endswith('/'):
                                cls.end_point = cls.end_point[:-1]
                            if rest_method.value == RestMethod.GET.value:
                                url_args = cls._generate_url_args(self_id=this._self_id, kwargs=kwargs_)
                                url = f"{cls.end_point}/{cls._impl_name}/{api.name}{url_args}"
                                async with aiohttp.ClientSession(timeout=api.timeout) as session:
                                    async with session.get(url) as resp:
                                        data = (await resp.content.read()).decode('utf-8')
                                        return conversions.from_str(data, api.return_type)
                            else:
                                url = f"{cls.end_point}/{cls._impl_name}/{api.name}?self={this._self_id}"
                                payload = json.dumps({k: conversions.to_str(v) for k, v in kwargs_.items()})
                                async with aiohttp.ClientSession(timeout=api.timeout) as session:
                                    async with session.post(url, data=payload) as resp:
                                        data = (await resp.content.read()).decode('utf-8')
                                        return conversions.from_str(data, api.return_type)

                        async def instance_method_streamed(this, *args, **kwargs_):
                            nonlocal api
                            arg_spec = inspect.getfullargspec(api._func)
                            kwargs_.update({
                                arg_spec.args[n+1]: arg for n, arg in enumerate(args)
                            })
                            method_api = api.method
                            rest_method = method_api._bantam_web_api.method
                            while cls.end_point.endswith('/'):
                                cls.end_point = cls.end_point[:-1]
                            if rest_method == RestMethod.GET:
                                url_args = cls._generate_url_args(self_id=this._self_id, kwargs=kwargs_)
                                url = f"{cls.end_point}/{cls._impl_name}/{api.name}{url_args}"
                                async with aiohttp.ClientSession(timeout=api.timeout) as session:
                                    async with session.get(url) as resp:
                                        resp.raise_for_status()
                                        async for data, _ in resp.content.iter_chunks():
                                            if data:
                                                data = data.decode('utf-8')
                                                yield conversions.from_str(data, api.return_type)
                            else:
                                url = f"{cls.end_point}/{cls._impl_name}/{api.name}?self={this._self_id}"
                                payload = json.dumps({k: conversions.to_str(v) for k, v in kwargs_.items()})
                                async with aiohttp.ClientSession(timeout=api.timeout) as session:
                                    async with session.post(url, data=payload) as resp:
                                        resp.raise_for_status()
                                        async for data, _ in resp.content.iter_chunks():
                                            if data:
                                                data = data.decode('utf-8')
                                                yield conversions.from_str(data, api.return_type)

                        if api.has_streamed_response:
                            setattr(cls, name_, instance_method_streamed)
                        else:
                            setattr(cls, name_, instance_method)

                    @classmethod
                    def _generate_url_args(cls, kwargs, self_id: Optional[str] = None):
                        if self_id is None and not kwargs:
                            return ''
                        return (f'?self={self_id}&' if self_id is not None else '?') + \
                            '&'.join([f"{k}={conversions.to_str(v)}" for k, v in kwargs.items() if v is not None])

                    @classmethod
                    def add_static_method(cls, name_: str, method_):
                        # class/static methods

                        if not hasattr(method_, '_bantam_web_api'):
                            raise SyntaxError(f"All methods of class WebClient most be decorated with '@web_api'")
                        # noinspection PyProtectedMember
                        if method_._bantam_web_api.has_streamed_request:
                            raise SyntaxError(f"Streamed request for WebClient's are not supported at this time")
                        # noinspection PyProtectedMember
                        api: API = method_._bantam_web_api
                        base_url = f"{cls.end_point}/{cls._impl_name}/{name_}"

                        # noinspection PyDecorator
                        @staticmethod
                        async def static_method(*args, **kwargs_):
                            nonlocal api
                            arg_spec = inspect.getfullargspec(api._func)
                            kwargs_.update({
                                arg_spec.args[n]: arg for n, arg in enumerate(args)
                            })
                            rest_method = api._func._bantam_web_api.method
                            while cls.end_point.endswith('/'):
                                cls.end_point = cls.end_point[:-1]
                            if rest_method.value == RestMethod.GET.value:
                                url_args = cls._generate_url_args(kwargs=kwargs_)
                                url = f"{base_url}{url_args}"
                                async with aiohttp.ClientSession(timeout=api.timeout) as session:
                                    async with session.get(url) as resp:
                                        resp.raise_for_status()
                                        data = (await resp.content.read()).decode('utf-8')
                                        if api.is_constructor:
                                            if hasattr(cls, 'jsonrepr'):
                                                repr_ = cls.jsonrepr(data)
                                                self_id = repr_[api.uuid_param or 'self_id']
                                            else:
                                                self_id = kwargs_[api.uuid_param or 'self_id']
                                            return cls(self_id)
                                        return conversions.from_str(data, api.return_type)
                            else:
                                payload = json.dumps({conversions.to_str(k): conversions.normalize_to_json_compat(v)
                                                      for k, v in kwargs_.items()})
                                async with aiohttp.ClientSession(timeout=api.timeout) as session:
                                    async with session.post(base_url, data=payload) as resp:
                                        resp.raise_for_status()
                                        data = (await resp.content.read()).decode('utf-8')
                                        if api.is_constructor:
                                            self_id = json.loads(data)['self_id']
                                            return cls(self_id)
                                        return conversions.from_str(data, api.return_type)

                        # noinspection PyDecorator
                        @staticmethod
                        async def static_method_streamed(*args, **kwargs_):
                            nonlocal api
                            arg_spec = inspect.getfullargspec(api._func)
                            kwargs_.update({
                                arg_spec.args[n]: arg for n, arg in enumerate(args)
                            })
                            rest_method = api._func._bantam_web_api.method
                            while cls.end_point.endswith('/'):
                                cls.end_point = cls.end_point[:-1]
                            if rest_method.value == RestMethod.GET.value:
                                url_args = cls._generate_url_args(kwargs=kwargs_)
                                url = f"{base_url}{url_args}"
                                async with aiohttp.ClientSession(timeout=api.timeout) as session:
                                    async with session.get(url) as resp:
                                        resp.raise_for_status()
                                        async for data, _ in resp.content.iter_chunks():
                                            if data:
                                                data = data.decode('utf-8')
                                                yield conversions.from_str(data, api.return_type)
                            else:
                                payload = json.dumps({conversions.to_str(k): conversions.normalize_to_json_compat(v)
                                                      for k, v in kwargs_.items()})
                                async with aiohttp.ClientSession(timeout=api.timeout) as session:
                                    async with session.post(base_url, data=payload) as resp:
                                        resp.raise_for_status()
                                        async for data, _ in resp.content.iter_chunks():
                                            if data:
                                                data = data.decode('utf-8')
                                                yield conversions.from_str(data, api.return_type)

                        if api.has_streamed_response:
                            setattr(ClientImpl, api.name, static_method_streamed)
                        else:
                            setattr(ClientImpl, api.name, static_method)

                    @classmethod
                    def add_class_method(cls, name_: str, method_):
                        # class/static methods

                        if not hasattr(method_, '_bantam_web_api'):
                            raise SyntaxError(f"All methods of class WebClient most be decorated with '@web_api'")
                        # noinspection PyProtectedMember
                        if method_._bantam_web_api.has_streamed_request:
                            raise SyntaxError(f"Streamed request for WebClient's are not supported at this time")
                        # noinspection PyProtectedMember
                        api: API = method_._bantam_web_api
                        base_url = f"{cls.end_point}/{cls._impl_name}/{name_}"

                        # noinspection PyDecorator,PyShadowingNames
                        @classmethod
                        async def class_method(cls, *args, **kwargs_):
                            nonlocal api
                            try:
                                arg_spec = inspect.getfullargspec(api._func)
                            except Exception:
                                arg_spec = inspect.getfullargspec(api._func.__func__)
                            kwargs_.update({
                                arg_spec.args[n+1]: arg for n, arg in enumerate(args)
                            })
                            # noinspection PyBroadException
                            rest_method = api._func._bantam_web_api.method
                            while cls.end_point.endswith('/'):
                                cls.end_point = cls.end_point[:-1]
                            if rest_method.value == RestMethod.GET.value:
                                url_args = cls._generate_url_args(kwargs=kwargs_)
                                url = f"{base_url}{url_args}"
                                async with aiohttp.ClientSession(timeout=api.timeout) as session:
                                    async with session.get(url) as resp:
                                        resp.raise_for_status()
                                        data = (await resp.content.read()).decode('utf-8')
                                        if api.is_constructor:
                                            if hasattr(cls, 'jsonrepr'):
                                                repr_ = cls.jsonrepr(data)
                                                self_id = repr_[api.uuid_param or 'self_id']
                                            else:
                                                self_id = kwargs_[api.uuid_param or 'self_id']
                                            return cls(self_id)
                                        return conversions.from_str(data, api.return_type)
                            else:
                                payload = json.dumps({conversions.to_str(k): conversions.normalize_to_json_compat(v)
                                                      for k, v in kwargs_.items()})
                                async with aiohttp.ClientSession(timeout=api.timeout) as session:
                                    async with session.post(base_url, data=payload) as resp:
                                        resp.raise_for_status()
                                        data = (await resp.content.read()).decode('utf-8')
                                        if api.is_constructor:
                                            self_id = json.loads(data)['self_id']
                                            return cls(self_id)
                                        return conversions.from_str(data, api.return_type)

                        # noinspection PyDecorator
                        @classmethod
                        async def class_method_streamed(cld, *args, **kwargs_):
                            nonlocal api
                            try:
                                arg_spec = inspect.getfullargspec(api._func)
                            except Exception:
                                arg_spec = inspect.getfullargspec(api._func.__func__)
                            kwargs_.update({
                                arg_spec.args[n+1]: arg for n, arg in enumerate(args)
                            })
                            rest_method = api._func._bantam_web_api.method
                            while cls.end_point.endswith('/'):
                                cls.end_point = cls.end_point[:-1]
                            if rest_method.value == RestMethod.GET.value:
                                url_args = cls._generate_url_args(kwargs=kwargs_)
                                url = f"{base_url}{url_args}"
                                async with aiohttp.ClientSession(timeout=api.timeout) as session:
                                    async with session.get(url) as resp:
                                        resp.raise_for_status()
                                        async for data, _ in resp.content.iter_chunks():
                                            if data:
                                                data = data.decode('utf-8')
                                                yield conversions.from_str(data, api.return_type)
                            else:
                                payload = json.dumps({conversions.to_str(k): conversions.normalize_to_json_compat(v)
                                                      for k, v in kwargs_.items()})
                                async with aiohttp.ClientSession(timeout=api.timeout) as session:
                                    async with session.post(base_url, data=payload) as resp:
                                        async for data, _ in resp.content.iter_chunks():
                                            resp.raise_for_status()
                                            if data:
                                                data = data.decode('utf-8')
                                                yield conversions.from_str(data, api.return_type)

                        if api.has_streamed_response:
                            setattr(ClientImpl, api.name, class_method_streamed)
                        else:
                            setattr(ClientImpl, api.name, class_method)

                    @classmethod
                    def _construct(cls):
                        for name, method in inspect.getmembers(
                                cls._clazz,
                                predicate=lambda x: inspect.ismethod(x) or inspect.isfunction(x)):
                            if name in ('__init__', '_construct', 'Client', 'jsonrepr'):
                                continue
                            if not hasattr(method, '_bantam_web_api'):
                                raise SyntaxError(f"classes inheriting from WebInterface should only implement "
                                                  "method decorated with @web_api")
                            if method._bantam_web_api.is_static:
                                cls.add_static_method(name, method)
                            elif method._bantam_web_api.is_class_method:
                                cls.add_class_method(name, method)
                            else:
                                cls.add_instance_method(name, method)

                ClientImpl.end_point = end_point

                # abstractmethod implementations added dynamcially in ClientImple._cosntruct
                # cannot be added before processed by interpreter, so have to create one more level
                class ClientImplSane(ClientImpl):
                    ClientImpl._construct()
                ClientFactory._cache[end_point] = ClientImplSane
                return ClientImplSane

        return ClientFactory()
