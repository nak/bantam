import json
import inspect
from typing import TypeVar, Type, Optional

import aiohttp

from bantam import conversions
from bantam.api import RestMethod, API


T = TypeVar('T', bound="WebClient")


class WebInterface:

    # noinspection PyPep8Naming
    @classmethod
    def Client(cls: Type[T], impl_name: Optional[str] = None):

        # noinspection PyProtectedMember
        class ClientFactory:
            _cache = {}

            def __getitem__(self: T, end_point: str) -> Type["ClientImpl"]:
                if end_point in ClientFactory._cache:
                    return ClientFactory._cache[end_point]
                while end_point.endswith('/'):
                    end_point = end_point[:-1]
                ClientImpl.end_point = end_point
                ClientImpl._construct()
                ClientFactory._cache[end_point] = ClientImpl
                return ClientImpl

        # noinspection PyProtectedMember
        class ClientImpl(cls):

            end_point = None
            _clazz = cls
            if not impl_name and not cls.__name__.endswith('Interface'):
                raise SyntaxError("You must either supply an explicit name in Client for implementing class, "
                                  "or name the class <implement-class-name>Interface (aka wit a suffix of 'Interface'")
            else:
                _impl_name = impl_name or cls.__name__[:-9]

            def __init__(self, self_id: str):
                self._self_id = self_id

            @classmethod
            def _construct(cls):
                def add_instance_method(name: str, method):
                    # instance method
                    if name in ('Client', '_construct'):
                        return
                    if not hasattr(method, '_bantam_web_method'):
                        raise SyntaxError(f"All methods of class WebClient most be decorated with '@web_api'")
                    # noinspection PyProtectedMember
                    if method._bantam_web_api.has_streamed_request:
                        raise SyntaxError(f"Streamed request for WebClient's are not supported at this time")
                    # noinspection PyProtectedMember
                    api: API = method._bantam_web_api

                    async def instance_method(self, *args, **kwargs_):
                        nonlocal api
                        rest_method = api.method
                        arg_spec = inspect.getfullargspec(api._func)
                        kwargs = {arg_spec.args[n + 1]: args[n] for n in range(len(args))
                                  if args[n] is not None}  # skip self as first argspec
                        kwargs.update(kwargs_)

                        while cls.end_point.endswith('/'):
                            cls.end_point = cls.end_point[:-1]
                        if rest_method.value == RestMethod.GET.value:
                            url_args = f'?self={self._self_id}&' +\
                                '&'.join([f"{k}={conversions.to_str(v)}" for k, v in kwargs.items()])
                            url = f"{cls.end_point}/{cls._impl_name}/{api.name}{url_args}"
                            async with aiohttp.ClientSession() as session:
                                async with session.get(url) as resp:
                                    data = (await resp.content.read()).decode('utf-8')
                                    return conversions.from_str(data, api.return_type)
                        else:
                            url = f"{cls.end_point}/{cls._impl_name}/{api.name}?self={self._self_id}"
                            payload = json.dumps({k: conversions.to_str(v) for k, v in kwargs.items()})
                            async with aiohttp.ClientSession() as session:
                                async with session.post(url, data=payload) as resp:
                                    data = (await resp.content.read()).decode('utf-8')
                                    return conversions.from_str(data, api.return_type)

                    async def instance_method_streamed(self, *args, **kwargs_):
                        nonlocal api
                        method = api.method
                        rest_method = method._bantam_web_method
                        arg_spec = inspect.getfullargspec(api._func)
                        kwargs = {arg_spec.args[n]: args[n] for n in range(len(args))
                                  if args[n] is not None}
                        kwargs.update(kwargs_)

                        while cls.end_point.endswith('/'):
                            cls.end_point = cls.end_point[:-1]
                        if rest_method == RestMethod.GET:
                            url_args = f'?self={self._self_id}&' +\
                                '&'.join([f"{k}={conversions.to_str(v)}" for k, v in kwargs.items()])
                            url = f"{cls.end_point}/{cls._impl_name}/{api.name}{url_args}"
                            async with aiohttp.ClientSession() as session:
                                async with session.get(url) as resp:
                                    async for data, _ in resp.content.iter_chunks():
                                        if data:
                                            data = data.decode('utf-8')
                                            yield conversions.from_str(data, api.return_type)
                        else:
                            url = f"{cls.end_point}/{cls._impl_name}/{api.name}?self={self._self_id}"
                            payload = json.dumps({k: conversions.to_str(v) for k, v in kwargs.items()})
                            async with aiohttp.ClientSession() as session:
                                async with session.post(url, data=payload) as resp:
                                    async for data, _ in resp.content.iter_chunks():
                                        if data:
                                            data = data.decode('utf-8')
                                            yield conversions.from_str(data, api.return_type)

                    if api.has_streamed_response:
                        setattr(cls, name, instance_method_streamed)
                    else:
                        setattr(cls, name, instance_method)

                def add_static_method(name: str, method):
                    # class/static methods

                    if not hasattr(method, '_bantam_web_method'):
                        raise SyntaxError(f"All methods of class WebClient most be decorated with '@web_api'")
                    # noinspection PyProtectedMember
                    if method._bantam_web_api.has_streamed_request:
                        raise SyntaxError(f"Streamed request for WebClient's are not supported at this time")
                    # noinspection PyProtectedMember
                    api: API = method._bantam_web_api
                    base_url = f"{cls.end_point}/{cls._impl_name}/{name}"

                    # noinspection PyDecorator
                    @staticmethod
                    async def static_method(*args, **kwargs_):
                        nonlocal api
                        arg_spec = inspect.getfullargspec(api._func)
                        kwargs = {arg_spec.args[n]: args[n] for n in range(len(args))
                                  if args[n] is not None}
                        kwargs.update(kwargs_)
                        rest_method = api._func._bantam_web_method
                        while cls.end_point.endswith('/'):
                            cls.end_point = cls.end_point[:-1]
                        if rest_method.value == RestMethod.GET.value:
                            url_args = '?' + '&'.join([f"{k}={conversions.to_str(v)}" for k, v in kwargs.items()])\
                                if kwargs else ''
                            url = f"{base_url}{url_args}"
                            async with aiohttp.ClientSession() as session:
                                async with session.get(url) as resp:
                                    data = (await resp.content.read()).decode('utf-8')
                                    if api.is_constructor:
                                        if hasattr(cls, 'jsonrepr'):
                                            repr = cls.jsonrepr(data)
                                            self_id = repr[api.uuid_param or 'self_id']
                                        else:
                                            self_id = kwargs[api.uuid_param or 'self_id']
                                        return ClientImpl(self_id)
                                    return conversions.from_str(data, api.return_type)
                        else:
                            payload = json.dumps({k: conversions.to_str(v) for k, v in kwargs.items()})
                            async with aiohttp.ClientSession() as session:
                                async with session.post(base_url, data=payload) as resp:
                                    data = (await resp.content.read()).decode('utf-8')
                                    if api.is_constructor:
                                        self_id = json.loads(data)['self_id']
                                        return cls(self_id)
                                    return conversions.from_str(data, api.return_type)

                    # noinspection PyDecorator
                    @staticmethod
                    async def static_method_streamed(*args, **kwargs_):
                        nonlocal api
                        rest_method = api._func._bantam_web_method
                        arg_spec = inspect.getfullargspec(api._func)
                        kwargs = {arg_spec.args[n]: args[n] for n in range(len(args))
                                  if args[n] is not None}
                        kwargs.update(kwargs_)
                        while cls.end_point.endswith('/'):
                            cls.end_point = cls.end_point[:-1]
                        if rest_method.value == RestMethod.GET.value:
                            url_args = '?' + '&'.join([f"{k}={conversions.to_str(v)}" for k, v in kwargs.items()])
                            url = f"{base_url}{url_args}"
                            async with aiohttp.ClientSession() as session:
                                async with session.get(url) as resp:
                                    async for data, _ in resp.content.iter_chunks():
                                        if data:
                                            data = data.decode('utf-8')
                                            yield conversions.from_str(data, api.return_type)
                        else:
                            payload = json.dumps({k: conversions.to_str(v) for k, v in kwargs.items()})
                            async with aiohttp.ClientSession() as session:
                                async with session.post(base_url, data=payload) as resp:
                                    async for data, _ in resp.content.iter_chunks():
                                        if data:
                                            data = data.decode('utf-8')
                                            yield conversions.from_str(data, api.return_type)

                    if api.has_streamed_response:
                        setattr(ClientImpl, api.name, static_method_streamed)
                    else:
                        setattr(ClientImpl, api.name, static_method)

                for name, method in inspect.getmembers(cls._clazz, predicate=inspect.isfunction):
                    if name in ('__init__', '_construct', 'Client', 'jsonrepr'):
                        continue
                    if not method._bantam_web_api.is_instance_method:
                        delattr(cls._clazz, name)
                        add_static_method(name, method)
                    else:
                        add_instance_method(name, method)

        return ClientFactory()
