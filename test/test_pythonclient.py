import asyncio
from pathlib import Path
from typing import Optional, AsyncGenerator

from bantam.decorators import web_api, RestMethod, AsyncLineIterator
from bantam.pythonclient import PythonClientGenerator


class RestAPIExample:

    result_queue : Optional[asyncio.Queue] = None

    @web_api(content_type='text/plain', method=RestMethod.GET)
    @staticmethod
    async def api_get_basic(param1: int, param2: bool, param3: float, param4: str = "text") -> str:
        """
        Some sort of doc
        :param param1:
        :param param2:
        :param param3:
        :param param4:
        :return: String for test_api_basic
        """
        return "Response to test_api_basic"

    @web_api(content_type='text/json', method=RestMethod.GET)
    @staticmethod
    async def api_get_stream(param1: int, param2: bool, param3: float, param4: Optional[str] = None) -> AsyncGenerator[None, int]:
        """
        Some sort of doc
        :param param1:
        :param param2:
        :param param3:
        :param param4:
        :return: stream of int
        """
        for index in range(10):
            yield index
            await asyncio.sleep(0.02)

    @web_api(content_type='text/json', method=RestMethod.GET)
    @staticmethod
    async def api_get_stream_text(param1: int, param2: bool, param3: float, param4: Optional[str] = None) -> AsyncGenerator[None, bytes]:
        """
        Some sort of doc
        :param param1:
        :param param2:
        :param param3:
        :param param4:
        :return: stream of int
        """
        for index in range(10):
            yield f"GET COUNT: {index}"
            await asyncio.sleep(0.02)
        yield "DONE"

    @web_api(content_type='text/json', method=RestMethod.POST)
    @staticmethod
    async def api_post_basic(param1: int, param2: bool, param3: float, param4: Optional[str] = "text") -> str:
        """
        Some sort of doc
        :param param1:
        :param param2:
        :param param3:
        :param param4:
        :return: stream of int
        """
        return "called basic post operation"

    @web_api(content_type='text/json', method=RestMethod.POST)
    @staticmethod
    async def api_post_stream(param1: int, param2: bool, param3: float, param4: str) -> AsyncGenerator[None, int]:
        """
        Some sort of doc
        :param param1:
        :param param2:
        :param param3:
        :param param4:
        :return: stream of int
        """
        for index in range(10):
            yield index
            await asyncio.sleep(0.02)

    @web_api(content_type='text/plain', method=RestMethod.POST)
    @staticmethod
    async def api_post_streamed_req_and_resp(param1: int, param2: bool, param3: float, param4: AsyncLineIterator)\
            -> AsyncGenerator[None, str]:
        """
        Some sort of doc
        :param param1:
        :param param2:
        :param param3:
        :param param4:
        :return: stream of int
        """
        async for line in param4:
            yield f"ECHO: {line}"
            await asyncio.sleep(0.02)

    @web_api(content_type='text/json', method=RestMethod.POST)
    @staticmethod
    async def api_post_stream_text(param1: int, param2: bool, param3: float, param4: Optional[str] = None) -> AsyncGenerator[None, str]:
        """
        Some sort of doc
        :param param1:
        :param param2:
        :param param3:
        :param param4:
        :return: stream of int
        """
        for index in range(10):
            yield f"COUNT: {index}"
            await asyncio.sleep(0.02)
        yield "DONE"


class TestPythonClientGenerator:

    def test_generate(self):
        PythonClientGenerator.generate(Path("client"))

