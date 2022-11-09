import json
from typing import AsyncIterator, Dict
from unittest.mock import patch

import pytest
from abc import abstractmethod

from bantam.api import RestMethod
from bantam.client import WebInterface
from bantam.decorators import web_api


class MockWebClientInterface(WebInterface):

    def jsonrepr(self):
        return {'self_id': id(self)}

    @web_api(method=RestMethod.GET, is_constructor=True, content_type='application/json')
    @staticmethod
    async def constructor(data: str) -> "MockWebClientInterface":
        """
        constructor mock
        :param data:
        :return:
        """
        raise NotImplementedError()


    @web_api(method=RestMethod.GET, content_type='application/json')
    @staticmethod
    @abstractmethod
    async def static_method() -> Dict[str, str]:
        raise NotImplementedError()

    @web_api(method=RestMethod.GET, is_constructor=True, content_type='json')
    @staticmethod
    @abstractmethod
    async def static_method_streamed(val1: int, val2: float) -> AsyncIterator[str]:
        raise NotImplementedError()

    @web_api(method=RestMethod.GET, content_type='application/json')
    @abstractmethod
    async def instance_method(self, val: str) -> str:
        raise NotImplementedError()


class TestWebClient:

    class MockContent:

        @property
        def content(self):
            return self

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

        async def iter_chunks(self):
            for text in ['I', "am", 'the', 'very', 'model']:
                yield text.encode('utf-8'), text == 'model'

        async def read(self, *args, **kwargs):
            class MockWebClient(MockWebClientInterface):

                async def constructor(data: str) -> "MockWebClient":
                    return MockWebClient()

            if TestWebClient._get_count == 1:
                return json.dumps(MockWebClientInterface.jsonrepr(MockWebClient())).encode('utf-8')
            elif TestWebClient._get_count == 2:
                return json.dumps({'a': "1"}).encode('utf-8')
            elif TestWebClient._get_count == 4:
                return b'PONG'

    _get_count = 0

    @staticmethod
    def mock_get(url: str, **kwargs):
        urls = [
            "http://someendpoint/MockWebClient/constructor?data=data",
            "http://someendpoint/MockWebClient/static_method",
            "http://someendpoint/MockWebClient/static_method_streamed?val1=1&val2=2.34",
            ("http://someendpoint/MockWebClient/instance_method?self","val=PING"),
        ]
        if TestWebClient._get_count < 3:
            assert url == urls[TestWebClient._get_count]
        else:
            assert url.startswith(urls[TestWebClient._get_count][0])
            assert url.endswith(urls[TestWebClient._get_count][1])
        TestWebClient._get_count += 1
        return TestWebClient.MockContent()


    @pytest.mark.asyncio
    @patch(target='aiohttp.ClientSession.get', new=mock_get)
    async def test_client(self):
        Client = MockWebClientInterface.Client()
        MyClient: MockWebClientInterface = Client['http://someendpoint/']
        MyClient2: MockWebClientInterface = Client['http://someendpoint2/']
        assert MyClient2 != MyClient
        instance = await MyClient.constructor('data')
        assert await MyClient.static_method() == {'a': "1"}
        data_values = []
        async for data in MyClient.static_method_streamed(val1=1, val2=2.34):
            data_values.append(data)
        assert data_values == ['I', 'am', 'the', 'very', 'model']
        assert await instance.instance_method("PING") == 'PONG'
