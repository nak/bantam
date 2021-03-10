import asyncio
from typing import AsyncGenerator

import os

from bantam.api import RestMethod
from bantam.web import WebApplication, web_api

class PoetryReader:
    POEM = """
    Mary had a little lamb...
    Its fleece was white as snow...
    Everywhere that Mary went...
    Her lamb was sure to go...
    """

    @web_api(content_type='text/streamed', method=RestMethod.POST)
    @staticmethod
    async def read_poem() -> AsyncGenerator[None, str]:
        for line in PoetryReader.POEM.strip().splitlines():
            yield line
            await asyncio.sleep(2)  # for dramatic effect
        yield "THE END"
        await asyncio.sleep(2)


if __name__ == '__main__':
    app = WebApplication(static_path=os.path.dirname(__file__), js_bundle_name='poetry_reader')
    asyncio.get_event_loop().run_until_complete(app.start())  # default to localhost HTTP on port 8080
