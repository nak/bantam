import asyncio
import json
import os
import subprocess
import sys
import webbrowser
from contextlib import suppress
from pathlib import Path
from typing import AsyncGenerator, Optional, Dict, Any

import pytest
from aiohttp.web_request import Request
from aiohttp.web_response import Response

from bantam.decorators import web_api
from bantam.api import AsyncLineIterator, RestMethod
from bantam.http import WebApplication


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

    @web_api(content_type='text/plain', method=RestMethod.GET)
    @staticmethod
    async def publish_result(result: str) -> None:
        await RestAPIExample.result_queue.put(result)


class TestJavascriptGenerator:

    @pytest.mark.asyncio
    async def test_generate_basic(self):
        def assert_preprocessor(request: Request) -> Dict[str, Any]:
            assert isinstance(request, Request), "Failed to get valid response on pre-processing"
            return {}

        def assert_postprocessor(response: Response) -> None:
            assert isinstance(response, Response), "Failed to get valid response for post-processing"

        RestAPIExample.result_queue = asyncio.Queue()
        root = Path(__file__).parent
        static_path = root.joinpath('static')
        app = WebApplication(static_path=static_path, js_bundle_name='generated', using_async=False)
        app.set_preprocessor(assert_preprocessor)
        app.set_postprocessor(assert_postprocessor)

        async def launch_browser():
            await asyncio.sleep(2.0)
            browser = None
            default = False
            try:
                browser = webbrowser.get("chrome")
            except:
                with suppress(Exception):
                    browser = webbrowser.get("google-chrome")
                if not browser:
                    browser = webbrowser.get()
                    default = True
            flags = ["--new-window"] if browser and not default else []
            if not browser:
                with suppress(Exception):
                    browser = webbrowser.get("firefox")
                    flags = ["-new-instance"]
            if not browser:
                os.write(sys.stderr.fileno(),
                         b"UNABLE TO GET BROWSER SUPPORT HEADLESS CONFIGURATION. DEFAULTING TO NON_HEADLESSS")
                browser = webbrowser.get()
            # cmdline = [browser.name] + flags + \
            browser.open("http://localhost:8080/static/index.html")
            # process = subprocess.Popen(cmdline)
            result = await RestAPIExample.result_queue.get()
            await asyncio.sleep(2.0)
            await app.shutdown()
            # if process.returncode != None:
            #    raise Exception("Browser died!")
            # process.kill()
            return result

        try:
            completed, _ = await asyncio.wait([app.start(), launch_browser()], timeout=100, return_when=asyncio.FIRST_COMPLETED)
            results = [c.result() for c in completed if c is not None]
        except Exception as e:
            assert False, f"Exception processing javascript results: {e}"

        if any([isinstance(r, Exception) for r in results]):
            assert False, "At least one javascript test failed. See browser window for details"
        assert results[0] == "PASSED", \
            "FAILED JAVSSCRIPT TESTS FOUND: \n" + \
            "\n".join([f"{test}: {msg}" for test, msg in json.loads(results[0]).items()])
