import asyncio
from asyncio import CancelledError
from contextlib import suppress
from pathlib import Path
import sys
if True:
    sys.path.insert(0, str(Path(__file__).parent / 'example'))
from pathlib import Path

import pytest
from bantam.http import WebApplication
from class_rest_get import RestAPIExampleAsyncInterface


@pytest.mark.asyncio
async def test_client_class_method(tmpdir):
    PORT = 8237
    app = WebApplication(static_path=Path(tmpdir), js_bundle_name='generated', using_async=False)
    task = asyncio.create_task(app.start(host='localhost', port=PORT, modules=['class_rest_get']))
    try:
        await asyncio.sleep(1)
        client: RestAPIExampleAsyncInterface = RestAPIExampleAsyncInterface.Client(end_point=f'http://localhost:{PORT}/')
        response = await client.api_get_basic(42, True, 992.123)
        assert response == f"Response to test_api_basic 1.0 2"
    finally:
        task.cancel()
        with suppress(CancelledError):
            await task


@pytest.mark.asyncio
async def test_client_constructor(tmpdir):
    PORT = 8237
    app = WebApplication(static_path=Path(tmpdir), js_bundle_name='generated', using_async=False)
    task = asyncio.create_task(app.start(host='localhost', port=PORT, modules=['class_rest_get']))
    try:
        await asyncio.sleep(1)
        client: RestAPIExampleAsyncInterface = RestAPIExampleAsyncInterface.Client(end_point=f'http://localhost:{PORT}/')
        response = await client.explicit_constructor(42)
        assert response.self_id is not None
    finally:
        task.cancel()
        with suppress(CancelledError):
            await task


@pytest.mark.asyncio
async def test_client_instance_method(tmpdir):
    PORT = 8237
    app = WebApplication(static_path=Path(tmpdir), js_bundle_name='generated', using_async=False)
    task = asyncio.create_task(app.start(host='localhost', port=PORT, modules=['class_rest_get']))
    try:
        await asyncio.sleep(1)
        Client = RestAPIExampleAsyncInterface.Client(end_point=f'http://localhost:{PORT}/')
        instance = await Client.explicit_constructor(4242)
        response = await instance.my_value()
        assert response == 4242
    finally:
        task.cancel()
        with suppress(CancelledError):
            await task


@pytest.mark.asyncio
async def test_client_class_method_streamed(tmpdir):
    PORT = 8237
    app = WebApplication(static_path=Path(tmpdir), js_bundle_name='generated', using_async=False)
    task = asyncio.create_task(app.start(host='localhost', port=PORT, modules=['class_rest_get']))
    try:
        await asyncio.sleep(1)
        client = RestAPIExampleAsyncInterface.Client(end_point=f'http://localhost:{PORT}/')
        count = 0
        async for item in client.api_get_stream(42, True, 992.123, "They're here..."):
            assert item == count
            count += 1
        assert count == 10
    finally:
        task.cancel()
        with suppress(CancelledError):
            await task


@pytest.mark.asyncio
async def test_client_instance_method_streamed(tmpdir):
    PORT = 8237
    app = WebApplication(static_path=Path(tmpdir), js_bundle_name='generated', using_async=False)
    task = asyncio.create_task(app.start(host='localhost', port=PORT, modules=['class_rest_get']))
    try:
        await asyncio.sleep(1)
        Client = RestAPIExampleAsyncInterface.Client(end_point=f'http://localhost:{PORT}/')
        instance = await Client.explicit_constructor(29)
        count = 0
        async for item in instance.my_value_repeated(200):
            assert item == 29
            count += 1
        assert count == 200
    finally:
        task.cancel()
        with suppress(CancelledError):
            await task

@pytest.mark.asyncio
async def test_client_instance_method_streamed_str(tmpdir):
    PORT = 8237
    app = WebApplication(static_path=Path(tmpdir), js_bundle_name='generated', using_async=False)
    task = asyncio.create_task(app.start(host='localhost', port=PORT, modules=['class_rest_get']))
    try:
        await asyncio.sleep(1)
        Client = RestAPIExampleAsyncInterface.Client(end_point=f'http://localhost:{PORT}/')
        instance = await Client.explicit_constructor(29)
        count = 0
        async for item in instance.my_value_repeated_string(200):
            assert item == str(29)
            count += 1
        assert count == 200
    finally:
        task.cancel()
        with suppress(CancelledError):
            await task
