import json
from abc import ABC
import inspect
from typing import TypeVar, Type

import aiohttp

from src.bantam import conversions
from src.bantam.api import RestMethod, API


T = TypeVar('T', bound="WebClient")


class WebClient(ABC):

    @classmethod
    def Client(cls: Type[T]):

        class ClientFactory:

            def __getitem__(self: T, end_point: str) -> Type["ClientImpl"]:
                while end_point.endswith('/'):
                    end_point = end_point[:-1]
                ClientImpl.end_point = end_point
                ClientImpl._construct()
                return ClientImpl

        class ClientImpl(cls):

            end_point = None
            _clazz = cls

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

                    async def instance_method(self, *args, **kwargs):
                        nonlocal api
                        method = api.method
                        rest_method = method._bantam_web_method
                        kwargs = locals().copy()
                        del kwargs['cls']

                        while cls.end_point.endswith('/'):
                            cls.end_point = cls.end_point[:-1]
                        if rest_method == RestMethod.GET:
                            url_args = f'?self={self._self_id}&' +\
                                '&'.join([f"{k}={conversions.to_str(v)}" for k, v in kwargs])
                            url = f"{cls.end_point}/{cls.__name__}/{name}{url_args}"
                            async with aiohttp.ClientSession() as session:
                                async with session.get(url) as resp:
                                    data = (await resp.content.read()).decode('utf-8')
                                    return conversions.from_str(data, api.return_type)
                        else:
                            url = f"{cls.end_point}/{api.clazz.__name__}/{method.__func__.__name__}?self={self._self_id}"
                            payload = json.dumps({k: conversions.to_str(v) for k, v in kwargs})
                            async with aiohttp.ClientSession() as session:
                                async with session.post(url, data=payload) as resp:
                                    data = (await resp.content.read()).decode('utf-8')
                                    return conversions.from_str(data, api.return_type)

                    async def instance_method_streamed(self, *args, **kwargs):
                        nonlocal api
                        method = api.method
                        rest_method = method._bantam_web_method
                        kwargs = locals().copy()
                        del kwargs['cls']

                        while cls.end_point.endswith('/'):
                            cls.end_point = cls.end_point[:-1]
                        if rest_method == RestMethod.GET:
                            url_args = f'?self={self._self_id}&' +\
                                '&'.join([f"{k}={conversions.to_str(v)}" for k, v in kwargs])
                            url = f"{cls.end_point}/{cls.__name__}/{name}{url_args}"
                            async with aiohttp.ClientSession() as session:
                                async with session.get(url) as resp:
                                    async for data, _ in resp.content.iter_chunks():
                                        if data:
                                            data = data.decode('utf-8')
                                            yield conversions.from_str(data, api.return_type)
                        else:
                            url = f"{cls.end_point}/{api.clazz.__name__}/{method.__func__.__name__}?self={self._self_id}"
                            payload = json.dumps({k: conversions.to_str(v) for k, v in kwargs})
                            async with aiohttp.ClientSession() as session:
                                async with session.post(url, data=payload) as resp:
                                    async for data, _ in resp.content.iter_chunks():
                                        if data:
                                            data = data.decode('utf-8')
                                            yield conversions.from_str(data, api.return_type)

                    if api.has_streamed_response:
                        setattr(cls, api._func.name, instance_method_streamed)
                    else:
                        setattr(cls, api._func.name, instance_method)

                def add_static_method(name: str, method):
                    # class/static methods

                    if not hasattr(method, '_bantam_web_method'):
                        raise SyntaxError(f"All methods of class WebClient most be decorated with '@web_api'")
                    # noinspection PyProtectedMember
                    if method._bantam_web_api.has_streamed_request:
                        raise SyntaxError(f"Streamed request for WebClient's are not supported at this time")
                    # noinspection PyProtectedMember
                    api: API = method._bantam_web_api

                    @staticmethod
                    async def static_method(*args, **kwargs):
                        nonlocal api
                        method = api.method
                        rest_method = api._func._bantam_web_method
                        kwargs = locals().copy()
                        del kwargs['cls']
                        while cls.end_point.endswith('/'):
                            cls.end_point = cls.end_point[:-1]
                        if rest_method == RestMethod.GET:
                            url_args = '?' + '&'.join([f"{k}={conversions.to_str(v)}" for k, v in kwargs])
                            url = f"{cls.end_point}/{api.clazz.__name__}/{method.__func__.__name__}{url_args}"
                            async with aiohttp.ClientSession() as session:
                                async with session.get(url) as resp:
                                    data = (await resp.content.read()).decode('utf-8')
                                    if api.is_constructor:
                                        self_id = json.loads(data)['self_id']
                                        return cls(self_id)
                                    return conversions.from_str(data, api.return_type)
                        else:
                            url = f"{cls.end_point}/{api.clazz.__name__}/{method.__func__.__name__}"
                            payload = json.dumps({k: conversions.to_str(v) for k, v in kwargs})
                            async with aiohttp.ClientSession() as session:
                                async with session.post(url, data=payload) as resp:
                                    data = (await resp.content.read()).decode('utf-8')
                                    if api.is_constructor:
                                        self_id = json.loads(data)['self_id']
                                        return cls(self_id)
                                    return conversions.from_str(data, api.return_type)


                    @staticmethod
                    async def static_method_streamed(*args, **kwargs):
                        nonlocal api
                        method = api.method
                        rest_method = api._func._bantam_web_method
                        kwargs = locals().copy()
                        del kwargs['cls']
                        while cls.end_point.endswith('/'):
                            cls.end_point = cls.end_point[:-1]
                        if rest_method == RestMethod.GET:
                            url_args = '?' + '&'.join([f"{k}={conversions.to_str(v)}" for k, v in kwargs])
                            url = f"{cls.end_point}/{api.clazz.__name__}/{method.__func__.__name__}{url_args}"
                            async with aiohttp.ClientSession() as session:
                                async with session.get(url) as resp:
                                    async for data, _ in resp.content.iter_chunks():
                                        if data:
                                            data = data.decode('utf-8')
                                            yield conversions.from_str(data, api.return_type)
                        else:
                            url = f"{cls.end_point}/{api.clazz.__name__}/{method.__func__.__name__}"
                            payload = json.dumps({k: conversions.to_str(v) for k, v in kwargs})
                            async with aiohttp.ClientSession() as session:
                                async with session.post(url, data=payload) as resp:
                                    async for data, _ in resp.content.iter_chunks():
                                        if data:
                                            data = data.decode('utf-8')
                                            yield conversions.from_str(data, api.return_type)

                    if api.has_streamed_response:
                        setattr(cls, api.name, static_method_streamed)
                    else:
                        setattr(cls, api.name, static_method)

                for name, method in inspect.getmembers(cls, predicate=inspect.isfunction):
                    if name in ('__init__', '_construct', 'Client', 'jsonrepr'):
                        continue
                    if not hasattr(method, '__self__'):
                        add_static_method(name, method)
                    else:
                        add_instance_method(name, method)

        return ClientFactory()
