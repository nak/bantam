import pytest
from abc import abstractmethod

from bantam.api import RestMethod
from bantam.client import WebClient
from bantam.decorators import web_api


class MockWebClientIF(WebClient):

    def jsonrepr(self):
        return {'self_id': id(self)}

    @web_api(method=RestMethod.GET, is_constructor=True, content_type='json')
    @staticmethod
    @abstractmethod
    async def constructor(data: str) -> "MockWebClient":
        """
        constructor mock
        :param data:
        :return:
        """


class TestWebClient:

    @pytest.mark.asyncio
    async def test_client(self):
        MyClient: MockWebClientIF = MockWebClientIF.Client()['http:/someendpoint/']
        await MyClient.constructor('data')
