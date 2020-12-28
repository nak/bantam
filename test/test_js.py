import asyncio
from pathlib import Path
from typing import AsyncGenerator

from aiohttp import web

from bantam.decorators import web_api, RestMethod, AsyncLineGenerator
from bantam.js import JavascriptGenerator
from bantam.web import WebApplication


class RestAPIExample:

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
    async def api_get_stream(param1: int, param2: bool, param3: float, param4: str) -> AsyncGenerator[None, int]:
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

    @web_api(content_type='text/json', method=RestMethod.POST)
    @staticmethod
    async def api_post_stream(param1: int, param2: bool, param3: float, param4: str) -> AsyncGenerator[None, str]:
        """
        Some sort of doc
        :param param1:
        :param param2:
        :param param3:
        :param param4:
        :return: stream of int
        """
        for index in range(10):
            yield str(index)

    @web_api(content_type='text/plain', method=RestMethod.POST)
    @staticmethod
    async def api_post_streamed_req_and_resp(param1: int, param2: bool, param3: float, param4: AsyncLineGenerator)\
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


class TestJavascriptGenerator:

    def test_generate_basic(self):
        root = Path(__file__).parent
        static_path = root.joinpath('js')
        output_path = static_path.joinpath('generated.js')
        with open(output_path, 'bw') as f:
            JavascriptGenerator.generate(f)
        with open(output_path, 'r') as f:
            print(f.read())
        app = WebApplication(static_path='js')
        asyncio.get_event_loop().run_until_complete(web.run_app(app))
