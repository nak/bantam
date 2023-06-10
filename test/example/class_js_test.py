import asyncio
from typing import Optional, AsyncGenerator

from bantam.api import RestMethod, AsyncLineIterator
from bantam.decorators import web_api


class ClassRestExample:
    """
    HTTP resource for testing class with instance methods
    """

    def __init__(self, val: int):
        """
        Create a session-level object

        :param val: some dummy value
        """
        self._value = val

    @web_api(content_type='text/plain', method=RestMethod.POST)
    async def echo(self, param1: int, param2: bool, param3: float, param4: Optional[str] = "text") -> str:
        """
        Some sort of doc
        :param param1:
        :param param2:
        :param param3:
        :param param4:
        :return: sting based on state and params
        """
        return f"called basic post operation on instance {self._value}: {param1} {param2} {param3} {param4}"


class RestAPIExample:

    result_queue: Optional[asyncio.Queue] = None

    @classmethod
    @web_api(content_type='text/plain', method=RestMethod.GET)
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

    @classmethod
    @web_api(content_type='text/json', method=RestMethod.GET)
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

    @classmethod
    @web_api(content_type='text/json', method=RestMethod.GET)
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

    @classmethod
    @web_api(content_type='text/json', method=RestMethod.POST)
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

    @classmethod
    @web_api(content_type='text/json', method=RestMethod.POST)
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

    @classmethod
    @web_api(content_type='text/plain', method=RestMethod.POST)
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

    @classmethod
    @web_api(content_type='text/json', method=RestMethod.POST)
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

    @classmethod
    @web_api(content_type='text/plain', method=RestMethod.GET)
    async def publish_result(result: str) -> None:
        await RestAPIExample.result_queue.put(result)
