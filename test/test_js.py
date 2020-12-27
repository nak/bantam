from typing import AsyncGenerator


from bantam.decorators import web_api, RestMethod, AsyncLineGenerator
from bantam.js import JavascriptGenerator


class RestAPIExample:

    @web_api(content_type='text/plain', method=RestMethod.GET)
    @staticmethod
    async def test_api_basic(param1: int, param2: bool, param3: float, param4: str) -> str:
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
    async def test_api_stream(param1: int, param2: bool, param3: float, param4: str) -> AsyncGenerator[None, int]:
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
    async def test_post_api_stream(param1: int, param2: bool, param3: float, param4: str) -> AsyncGenerator[None, str]:
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
    async def test_post_api_streamed_req_and_resp(param1: int, param2: bool, param3: float, param4: AsyncLineGenerator)\
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

    def test_generate_basic(self, tmp_path):
        with open(tmp_path / "temp.js", 'bw') as f:
            JavascriptGenerator.generate(f)
        with open(tmp_path / "temp.js", 'r') as f:
            print(f.read())
