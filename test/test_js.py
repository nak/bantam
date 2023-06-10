import asyncio
import json
import os
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



class TestJavascriptGenerator:

    @pytest.mark.asyncio
    async def test_generate_basic(self):
        def assert_preprocessor(request: Request) -> Dict[str, Any]:
            assert isinstance(request, Request), "Failed to get valid response on pre-processing"
            return {}

        def assert_postprocessor(response: Response) -> None:
            assert isinstance(response, Response), "Failed to get valid response for post-processing"

        from class_js_test import RestAPIExample
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
            if result != 'PASSED':
                await asyncio.sleep(2.0)
            await app.shutdown()
            return result

        try:
            completed, _ = await asyncio.wait([app.start(modules=['class_js_test']), launch_browser()],
                                              timeout=100, return_when=asyncio.FIRST_COMPLETED)
            results = [c.result() for c in completed if c is not None]
        except Exception as e:
            assert False, f"Exception processing javascript results: {e}"

        if any([isinstance(r, Exception) for r in results]):
            assert False, "At least one javascript test failed. See browser window for details"
        assert results[0] == "PASSED", \
            "FAILED JAVASCRIPT TESTS FOUND: \n" + \
            "\n".join([f"{test}: {msg}" for test, msg in json.loads(results[0]).items()])
