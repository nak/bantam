"""
Bantam provides the ability to auto-generate client-side Python code to abstract the details of makting
HTTP requests to the server.  This abstraction implies that the developer never need to know about routes,
formulating URLs, how to make a POST request, how to stream data over HTTP, etc!

To generate client side code, create a Python source file -- let's name it generator.py --
and import all of the classes containing @web_api's
to be generated. Then add the main entry poitn to generate the javascript code, like so:

>>> from bantam.pythonclient import PythonClientGenerator
... from pathlib import Path
...
... if __name__ == '__main__':
...     output_path = Path(client)
...     PythonClientGenerator.generate(output_path=output_path)

Run the script as so:

.. code-block:: bash

    % python generate.py

With the above Greetings example, the generated Pyahon has the same code structure as the core library, except that
only the @web_api declared class metthods are present, and the implementation is a Rest-based calling implementation
to a remote server.
"""
raise NotImplemented("This package is under construction and should not be used at this time")

import os
import re
from pathlib import Path

from aiohttp.web_response import Response, StreamResponse
from typing import Coroutine, Callable, Awaitable, Union
from typing import Dict, Tuple, List, IO, Type
from urllib.request import Request

from bantam.decorators import WebApi
from bantam.api import AsyncChunkIterator, AsyncLineIterator, RestMethod

AsyncApi = Callable[[Request], Awaitable[Union[Response, StreamResponse]]]


def type_name(typ):
    if typ not in (bytes, str, int, float, bool, None):
        if str(typ).startswith('typing.'):
            return str(typ).replace('NoneType', 'None')
        else:
            return "Any"
    return typ.__name__ if typ is not None else None


class PythonClientGenerator:
    """
    Class for generating a web-api-only based Python client for accessing the library from a remote client
    """

    ENCODING = 'utf-8'
    
    @classmethod
    def generate(cls, output_path: Path) -> None:
        """
        Generate Python Rest-ful web-api code from registered routes

        :param output_path: path to generate Python client-side code base
        """
        from bantam.web import WebApplication
        classes: Dict[Path, Dict[str, Dict[RestMethod, List[WebApi]]]] = {}
        content_types: Dict[WebApi, str] = {}
        routes: Dict[WebApi, str] = {}
        top_dir = None
        common_mod = None

        for method, callables in {RestMethod.GET: WebApplication.callables_get,
                          RestMethod.POST: WebApplication.callables_post}.items():
            for route, api in list(callables.items()):
                content_types[api] = WebApplication.content_type[route]
                routes[api] = route
                module: str = api.__module__
                top_dir = output_path.joinpath(Path(module.split('.', maxsplit=1)[0]))
                if not top_dir.exists():
                    top_dir.mkdir(parents=True)
                top_mod = top_dir.joinpath('__init__.py')
                if not common_mod:
                    common_mod = module.split('.', maxsplit=1)[0]
                    with open(top_mod, 'wb') as out:
                        out.write(f"""
from typing import Any, Dict, Optional, Type
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Config:
    \"\"\"
    class to hold common client configuration information
    \"\"\"
    # base url of server
    base_url: str
    # common headers to be sent on every request
    common_headers: Dict[str, str] = field(default_factory=dict)


_config: Optional[Config] = None


def setup_client(config):
    \"\"\"
    Setup client configuration.  This must be called once before any calls to server are made

    :param config:  The `Config` object used to specify server interaction details
    \"\"\"
    global _config
    if _config is not None:
        raise Exception("Cannot override existing config")
    _config = config


def get_config():
    \"\"\"
    :return: The server interaction configuration information
    \"\"\"
    if _config is None:
        raise Exception("No configuration provided for bantam Python web client")
    return _config


def _serialize(value: Any, typ: Type) -> bytes:
    \"\"\"
    Serialize given value of given type to a string for use in Rest communications
    \"\"\"
    val = {{int: str(value),
           float: str(value),
           bool: str(value).lower(),
           str: value}}.get(typ).encode('utf-8')
    if val is None:
        if not hasattr(typ, 'serialize'):
            raise ValueError(f"Cannot serialize type {{typ}}, not a basic type an no 'serialize' method found")
        val = value.serialize()
        if isinstance(val, str):
            val = val.encode('utf-8')
        elif not isinstance(val, bytes):
            raise ValueError("Result of serialize method call on {{typ}} is not bytes but {{type(val)}}")
    return val


def _deserialize(text: bytes, typ: Type):
    \"\"\"
    Deserialize the given bytes (from a Rest response) into the given type
    \"\"\"
    if typ is None:
        return
    val = {{int: int(text),
           float: float(text),
           bool: True if (text.lower()=='true') else False,
           str: text}}.get(typ)
    if val is None:
        if not hasattr(typ, 'deserialize'):
            raise ValueError("Unable to deserialize return string: {{typ}} is not a basic type and has no method 'deserialize'")
        else:
            val = typ.deserialize(text)
            if not isinstance(val, typ):
                raise ValueError("Result of {{typ}}.deserialize() was not of type {{typ}} as expected")
    return val
    
""".encode('utf-8'))
                    top_mod_generated = True
                if '.' in module:  # top level mod
                    mod_path = output_path.joinpath(module.replace('.', os.path.sep) + ".py")
                    os.makedirs(os.path.dirname(mod_path), exist_ok=True)
                    with open(mod_path, 'wb') as out:
                        out.write(f"""
from {common_mod} import get_config, _deserialize, _serialize
import aiohttp
import typing
from typing import Optional, AsyncGenerator, Callable, Awaitable

""".encode('utf-8'))

                if not mod_path.parent.exists():
                    mod_path.parent.mkdir(parents=True)
                class_name, class_method = api.__qualname__.split('.')
                classes.setdefault(mod_path, {}).setdefault(class_name, {}).setdefault(method, [])
                classes[mod_path][class_name][method].append(api)
        if top_dir is None:
            raise TypeError("No web abi definitions found to be generated")
        for output_path, class_dict in classes.items():
            with open(output_path, 'ba') as out:
                out.write(f"""

AsyncChunkIterator = Callable[[int], Awaitable[AsyncGenerator[None, bytes]]]
AsyncLineIterator = AsyncGenerator[None, str]


""".encode('utf-8'))
                for class_name, api_dict in class_dict.items():
                    for rest_method, api_list in api_dict.items():
                        cls.generate_class(out, rest_method, class_name, api_list, content_types, routes)

    @classmethod
    def generate_class(cls, out: IO, method: RestMethod, class_name: str, api_list: List[WebApi], content_type: Dict[WebApi, str],
                       routes: Dict[WebApi, str]):
        if not api_list:
            return
        out.write(f"\nclass {class_name}:\n".encode('utf-8'))

        for api in api_list:
            if method == RestMethod.GET:
                cls.generate_get_method(out, api, content_type[api], routes[api])
            else:
                cls.generate_post_method(out, api, content_type[api], routes[api])

    @classmethod
    def generate_get_method(cls, out: IO, api: WebApi, content_type: str, route: str) -> None:
        method_name = api.__qualname__.split('.')[-1]
        return_type = api.__annotations__.get('return')
        return_async_iter = str(return_type).startswith('typing.AsyncGenerator')
        arg_annotations = dict(api.__annotations__)
        if 'return' in arg_annotations:
            del arg_annotations['return']
        method_args = ", ".join([f"{name}: {type_name(typ)}" for name, typ in arg_annotations.items()])
        out.write(b"    @staticmethod\n")
        out.write(f"    def {method_name}({method_args}) -> {type_name(return_type)}:\n".encode('utf-8'))
        out.write(b"        param_values = locals()\n")
        out.write(f"""
        param_types = { {name: typ.__name__  if hasattr(typ, "__name__") else str(typ) for name, typ in 
                         arg_annotations.items() if 'typing.Async' not in str(typ)} }
        query = ";".join([f"{{name}}={{_serialize(value, param_types[name])}}" for name, value in param_values.items()])
        headers = get_config().common_headers.update({{'content_type': "{content_type}"}})
        route = "{route}"
        async with aiohttp.ClientSession(headers=get_config().common_headers) as session:
            async with session.get(f"{{get_config().base_url}}{{route}}?{{query}}", headers=headers) as resp:""".encode('utf-8'))
        if not return_async_iter:
            out.write(f"""
                return _deserialize(await resp.text(), {type_name(return_type)})

""".encode('utf-8'))
        else:
            return_type = return_type.__args__[1]
            if return_type != bytes:
                out.write(f"""
                async for line in resp.content:
                    if not line:
                        continue
                    for item in line.split(b'\\n'):
                        yield _deserialize(item, {type_name(return_type)})
                        
""".encode('utf-8'))
            else:
                out.write(b"""
                async for line in resp.content:
                    if line:
                        yield line
                        
""")

    @classmethod
    def generate_post_method(cls, out: IO, api: WebApi, content_type: str, route: str) -> None:
        method_name = api.__qualname__.split('.')[-1]
        annotations = api.__annotations__
        arg_annotations = dict(api.__annotations__)
        if 'return' in arg_annotations:
            del arg_annotations['return']
        return_type = annotations.get('return').replace('NoneType', 'None')
        return_async_iter = str(return_type).startswith('typying.AsyncIterator')

        method_args = ", ".join([f"{name}:{type_name(typ)}" for name, typ in api.__annotations__.items()])
        out.write(b"    @staticmethod\n")
        out.write(f"        def {method_name}({method_args}):".encode('utf-8'))
        out.write(b"            param_values = locals()")
        async_annotations = [a for a in annotations.items() if a[1] in (bytes, AsyncChunkIterator, AsyncLineIterator)]
        if len(async_annotations) > 1:
            raise TypeError("Only one parameter in a web api can by an async iterator")
        if async_annotations:
            out.write(f"""
            annotations = { {name: typ.__name__  if hasattr(typ, "__name__") else str(typ) for name, typ in 
                             arg_annotations.items() if name not in async_annotations} }
            async_param = {async_annotations[0] if async_annotations else "None"}
            del param_values["{async_annotations[0][0]}"]
            query = ";".join([f"{{name}}={{_serialize(value, annotations[name])}}" for name, value in param_values.items()])
            headers = get_config().common_headers.update({{'content_type': "{content_type}"}})
            route = "{route}"
            payload = {{"{async_annotations[0][0]}": "{async_annotations[0][1]}"}}
            async def sender():
                for chunk in {async_annotations[0][0]}:
                    yield chunk
            resp = await session.post(f"{{get_config().base_url}}{{route}}?{{query}}, headers=headers, data=sender())
""".encode('utf-8'))
        else:
            out.write(b"""
            query = ""
            payload = param_values
""")
            out.write(b"""
            resp = await session.post({{get_config().base_url}}{{route}}?{{query}}, headers=headers, data=json.dumps(payload).encode('utf-8'))
""")
        if not return_async_iter:
            out.write(f"""
            return _deserialize(await resp.text(), {type_name(return_type)})
""".encode('utf-8'))
        else:
            return_type = return_type.__args__[1]
            if return_type != bytes:
                out.write(f"""
            async for line in resp.content:
                if not line:
                    continue
                for item in line.split(b'\\n'):
                    if item:
                        yield _deserialize(item, {type_name(return_type)})
""".encode('utf-8'))
            else:
                out.write(b"""
            async for line in resp.content:
                if line:
                    yield line
""")
