import asyncio
import webbrowser
from pathlib import Path
from typing import AsyncGenerator, Optional

import pytest
from aiohttp import web

from bantam.decorators import web_api, RestMethod, AsyncLineIterator
from bantam.js import JavascriptGenerator
from bantam.web import WebApplication


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
            yield f"COUNT: {index}\n"
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
            yield f"COUNT: {index}\n"
            await asyncio.sleep(0.02)
        yield "DONE"

    @web_api(content_type='text/plain', method=RestMethod.GET)
    @staticmethod
    async def publish_result(result: str) -> None:
        await RestAPIExample.result_queue.put(result)


class TestJavascriptGenerator:

    @pytest.mark.asyncio
    async def test_generate_basic(self):
        RestAPIExample.result_queue = asyncio.Queue()
        root = Path(__file__).parent
        static_path = root.joinpath('static')
        # output_path = static_path.joinpath('generated.js')
        # with open(output_path, 'bw') as f:
        #    JavascriptGenerator.generate(f)
        app = WebApplication(static_path=static_path, js_bundle_name='generated')

        async def launch_browser():
            await asyncio.sleep(2.0)
            webbrowser.get().open("http://localhost:8080/static/index.html")
            result = await RestAPIExample.result_queue.get()
            await asyncio.sleep(2.0)
            await app.shutdown()
            return result

        try:
            completed, _ = await asyncio.wait([app.start(), launch_browser()], timeout=100, return_when=asyncio.FIRST_COMPLETED)
            results = [c.result() for c in completed if c is not None]
        except Exception as e:
            assert False, f"Exception processing javascript results: {e}"

        if any([isinstance(r, Exception) for r in results]):
            assert False, "At least one javascript test failed. See browser window for details"

        if results[0] != "PASSED":
            raise Exception(results[0])