import asyncio
import os
import sys
from pathlib import Path
from bantam.http import WebApplication

sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.join(os.getcwd(), ".."))
sys.path.insert(0, os.path.join(os.getcwd(), "..", "src"))

import test.test_js_async

if __name__ == '__main__':
    root = Path(__file__).parent
    static_path = root.joinpath('static')
    app = WebApplication(static_path=static_path, js_bundle_name='generated')
    asyncio.get_event_loop().run_until_complete(app.start())