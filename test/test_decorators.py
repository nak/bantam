from typing import Any, Type, Dict

import pytest
from bantam.http import _convert_request_param, WebApplication
from bantam.api import AsyncChunkIterator, AsyncLineIterator


class Deserialiazlbe:

    def __init__(self, val: int):
        self._val = val

    @classmethod
    def deserialize(cls, text: str):
        return Deserialiazlbe(int(text))

    def __eq__(self, other):
        return other._val == self._val


class MockStreamResponse:

    def __init__(self, status: int, reason: str, headers: Dict[str, str]):
        self.body = b''
        assert status == 200
        assert reason == "OK"
        assert headers.get('Content-Type') in ['text/plain', 'text-streamed; charset=x-user-defined']
        self._status = status

    async def prepare(self, request):
        pass

    async def write(self, content: bytes):
        self.body += b' ' + content.replace('\n', '')

    async def write_eof(self, *args, **kargs):
        self.body += b'\n'



class MockRequestGet:

    def __init__(self, **kwargs):
        self.query = kwargs

    async def prepare(self, request):
        pass


class MockRequestPost:

    def __init__(self, **kwargs):
        self.can_read_body = True
        self.text_content = str(kwargs).replace("'", '"').encode('utf-8')

    async def read(self):
        return self.text_content


class MockRequestPostRaw:

    def __init__(self, param1: bytes, **kwargs):
        self.can_read_body = True
        self.byte_content = param1
        self.query = kwargs

    async def read(self):
        return self.byte_content


class MockRequestPostStream:

    class StreamReader:

        def __init__(self, content: bytes):
            self._content = content
            self._content_lines = content.splitlines()
            self.is_eof = False

        async def read(self, size: int):
            line = self._content[:size]
            self._content = self._content[size:]
            self.is_eof = len(self._content) == 0
            return line

        async def readline(self):
            line = self._content_lines[0]
            self._content_lines = self._content_lines[1:]
            self.is_eof = len(self._content_lines) == 0
            return line

    def __init__(self, param1: bytes, **kwargs):
        self.can_read_body = True
        self.content = self.StreamReader(param1)
        self.query = kwargs

    async def read(self):
        return str(self.query).encode('utf-8').replace(b'\'', b'"')


class TestDecoratorUtils:

    @pytest.mark.parametrize("text,typ,value", [("True", bool, True), ("false", bool, False), ("18938", int, 18938),
                                                ("1.2345", float, 1.2345), ("This is text", str, "This is text"),
                                                ])
    def test_convert_request_param(self, text: str, typ: Type, value: Any):
        assert _convert_request_param(text, typ) == value

    @pytest.mark.asyncio
    async def test__invoke_get_api_wrapper(self):
        async def func(param1: int, param2: str) -> str:
            assert param1 == 1
            assert param2 == 'text'
            return "RESULT"

        request = MockRequestGet(param1=1, param2='text')
        response = await WebApplication._invoke_get_api_wrapper(func=func, content_type='text/plain', request=request)
        assert response.status == 200
        assert response.body == b"RESULT"
        assert response.text == "RESULT"

    @pytest.mark.asyncio
    async def test__invoke_post_api_wrapper(self):
        async def func(param1: int, param2: str) -> str:
            assert param1 == 1
            assert param2 == 'text'
            return "RESULT"

        request = MockRequestPost(param1=1, param2='text')
        response = await WebApplication._invoke_post_api_wrapper(func=func, content_type='text/plain', request=request)
        assert response.status == 200
        assert response.body == b"RESULT"
        assert response.text == "RESULT"

    @pytest.mark.asyncio
    async def test__invoke_post_api_wrapper_raw_bytes(self):
        param_value = bytes([1, 22, 44, 3])

        async def func(param1: bytes) -> str:
            assert param1 == param_value
            return "RESULT"

        request = MockRequestPostRaw(param1=param_value)
        response = await WebApplication._invoke_post_api_wrapper(func=func, content_type='text/plain', request=request)
        assert response.status == 200
        assert response.body == b"RESULT"
        assert response.text == "RESULT"

    @pytest.mark.asyncio
    async def test__invoke_post_api_wrapper_stream(self):
        param_value = "I am the very\n model of a modern\n major general".encode('utf-8')

        async def func(param1: AsyncLineIterator) -> str:
            all = b""
            async for line in param1:
                all += line
            return all.decode('utf-8')

        request = MockRequestPostStream(param1=param_value)
        response = await WebApplication._invoke_post_api_wrapper(func=func, content_type='text/plain', request=request)
        assert response.status == 200
        assert response.body == param_value.replace(b'\n', b'')
        assert response.text == param_value.replace(b'\n', b'').decode('utf-8')

    @pytest.mark.asyncio
    async def test__invoke_post_api_wrapper_chunked(self):
        param_value = "I am the very\n model of a modern\n major general".encode('utf-8')

        async def func(param1: AsyncChunkIterator) -> str:
            all = b""
            async for line in param1(10):
                all += line
            return all.decode('utf-8').upper()

        request = MockRequestPostStream(param1=param_value)
        response = await WebApplication._invoke_post_api_wrapper(func=func, content_type='text/plain', request=request)
        assert response.status == 200
        assert response.body == param_value.upper()
        assert response.text == param_value.upper().decode('utf-8')
