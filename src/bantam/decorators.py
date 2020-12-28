import asyncio
import inspect
import json
from enum import Enum
from typing import Type, Any, AsyncGenerator, Callable

from aiohttp.web import Request, Response
from aiohttp.web_response import StreamResponse


class RestMethod(Enum):
    GET = 'GET'
    POST = 'POST'


AsyncChunkGenerator = Callable[[int], AsyncGenerator[None, bytes]]
AsyncLineGenerator = AsyncGenerator[None, bytes]


def _convert_request_param(value: str, typ: Type) -> Any:
    """
    Convert rest request string value for parameter to given Python type, returning an instance of that type

    :param value: value to convert
    :param typ: Python Type to convert to
    :return: converted instance, of the given type
    :raises: TypeError if value can not be converted/deserialized
    """
    if hasattr(typ, '_name') and str(typ).startswith('typing.Union'):
        typ = typ.__args__[0]
        return _convert_request_param(value, typ)
    if hasattr(typ, 'deserialize'):
        return typ.deserialize(value)
    elif typ == bool:
        if value.lower() == 'true':
            return True
        elif value.lower() == 'false':
            return False
        raise ValueError(f"Expected one of 'true' or 'false' but found {value}")
    try:
        return typ(value)
    except Exception as e:
        raise TypeError(f"Converting web request string to Python type {typ}: {e}")


def _serialize_return_value(value: Any, encoding: str) -> bytes:
    """
    Serialize a Python value into bytes to return through a Rest API.  If a basic type such as str, int or float, a
    simple str conversion is done, then converted to bytes.  If more complex, the conversion will invoke the
    'serialize' method of the value, raising TypeError if such a method does not exist or does not have a bare
    (no-parameter) signature.

    :param value: value to convert
    :return: bytes serialized from value
    """
    if isinstance(value, (str, bool, int, float)):
        return str(value).encode(encoding)
    elif hasattr(value, 'serialize'):
        try:
            image = value.serialize()
        except Exception as e:
            raise TypeError(f"Unable to serialize Python response to string-seralized web response: {e}")
        if not isinstance(image, (str, bytes)):
            raise TypeError(f"Call to serialize {value} of type {type(value)} did not return 'str' as expected")
        if isinstance(image, str):
            return image.encode(encoding)
        return image


async def _invoke_get_api_wrapper(func, content_type: str, request: Request):
    try:
        encoding = 'utf-8'
        items = content_type.split(';')
        for item in items:
            item = item.lower()
            if item.startswith('charset='):
                encoding = item.replace('charset=', '')
        annotations = dict(func.__annotations__)
        if 'return' in annotations:
            del annotations['return']
        # report first param that doesn't match the Python signature:
        for k in [p for p in request.query if p not in annotations]:
            return Response(status=400,
                reason=f"No such parameter or missing type hint for param {k} in method {func.__qualname__}")

        # convert incoming str values to proper type:
        kwargs = {k: _convert_request_param(v, annotations[k]) for k, v in request.query.items()}
        # call the underlying function:
        result = func(**kwargs)
        if inspect.isasyncgen(result):
            #################
            #  streamed response through async generator:
            #################
            # underlying function has yielded a result rather than turning
            # process the yielded value and allow execution to resume from yielding task
            async_q = asyncio.Queue()
            response = StreamResponse(status=200, reason='OK', headers={'Content-Type': content_type})
            await response.prepare(request)
            try:
                # iterate to get the one (and hopefully only) yielded element:
                async for res in result:
                    serialized = _serialize_return_value(res, encoding)
                    if not isinstance(res, str):
                        serialized += b'\n'
                    await response.write(serialized)
            except Exception as e:
                print(str(e))
                await async_q.put(None)
            await response.write_eof()
            return response
        else:
            #################
            #  regular response
            #################
            result = _serialize_return_value(await result, encoding)
            return Response(status=200, body=result if result is not None else b"Success",
                            content_type=content_type)

    except TypeError as e:
        return Response(status=400, text=f"Improperly formatted query: {str(e)}")
    except Exception as e:
        return Response(status=500, text=str(e))


async def _invoke_post_api_wrapper(func, content_type: str, request: Request):
    encoding = 'utf-8'
    items = content_type.split(';')
    for item in items:
        if item.startswith('charset='):
            encoding = item.replace('charset=', '')
    if not request.can_read_body:
        raise TypeError("Cannot read body for request in POST operation")

    annotations = dict(func.__annotations__)
    if 'return' in annotations:
        del annotations['return']
    try:
        kwargs = None
        async_annotations = [a for a in annotations.items() if a[1] in (bytes, AsyncChunkGenerator, AsyncLineGenerator)]
        if async_annotations:
            if not len(async_annotations) == 1:
                raise ValueError("At most one parameter of holding onf of the types: bytes, AsyncChunkGenerator or AsynLineGenerator is allowed")
            key, typ = async_annotations[0]
            if typ == bytes:
                kwargs = {key: await request.read()}
            elif typ == AsyncLineGenerator:
                async def iterator():
                    reader = request.content
                    while not reader.is_eof:
                        yield await reader.readline()
                kwargs = {key: iterator()}
            elif typ == AsyncChunkGenerator:
                async def iterator(packet_size: int):
                    reader = request.content
                    while not reader.is_eof:
                        yield await reader.read(packet_size)
                kwargs = {key: iterator}
            kwargs.update({k: _convert_request_param(v, annotations[k]) for k, v in request.query.items()})
        else:
            # treat payload as json string:
            bytes_response = await request.read()
            json_dict = json.loads(bytes_response.decode('utf-8'))
            for k in [p for p in json_dict if p not in annotations]:
                return Response(status=400,
                    text=f"No such parameter or missing type hint for param {k} in method {func.__qualname__}")

            # convert incoming str values to proper type:
            kwargs = dict(json_dict)
            # kwargs = {k: _convert_request_param(v, annotations[k]) for k, v in json_dict.items()}
        # call the underlying function:
        result = func(**kwargs)
        if inspect.isasyncgen(result):
            #################
            #  streamed response through async generator:
            #################
            # underlying function has yielded a result rather than turning
            # process the yielded value and allow execution to resume from yielding task
            async_q = asyncio.Queue()
            response = StreamResponse(status=200, reason='OK', headers={'Content-Type': content_type})
            await response.prepare(request)
            try:
                # iterate to get the one (and hopefully only) yielded element:
                async for res in result:
                    serialized = _serialize_return_value(res, encoding)
                    if not isinstance(res, str):
                        serialized += b'\n'
                    await response.write(serialized)
            except Exception as e:
                print(str(e))
                await async_q.put(None)
            await response.write_eof()
        else:
            #################
            #  regular response
            #################
            result = _serialize_return_value(await result, encoding)
            return Response(status=200, body=result if result is not None else b"Success",
                            content_type=content_type)

    except TypeError as e:
        return Response(status=400, text=f"Improperly formatted query: {str(e)}")
    except Exception as e:
        return Response(status=500, text=str(e))


def web_api(content_type: str, method: RestMethod = RestMethod.GET):
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
    from .web import WebApplication

    if not isinstance(content_type, str):
        raise Exception("@web_api must be provided one str argument which is the content type")

    def wrapper(func):
        if not isinstance(func, staticmethod):
            raise ValueError("the @web_api decorator can only be used on static class methods")
        elif not inspect.iscoroutinefunction(func.__func__) and not inspect.isasyncgenfunction(func.__func__):
            raise ValueError("the @web_api decorator can only be applied to methods that are coroutines (async)")
        func = func.__func__
        name = func.__qualname__
        name_parts = name.split('.')[-2:]
        route = '/' + '/'.join(name_parts)

        async def invoke_get(request: Request):
            return await _invoke_get_api_wrapper(func, content_type=content_type, request=request)

        async def invoke_post(request: Request):
            return await _invoke_post_api_wrapper(func, content_type=content_type, request=request)

        if method == RestMethod.GET:
            WebApplication.register_route_get(route, invoke_get, func, content_type)
        elif method == RestMethod.POST:
            WebApplication.register_route_post(route, invoke_post, func, content_type)
        else:
            raise ValueError(f"Method provide was not an instance of MethodEnum")
        return func
    return wrapper
