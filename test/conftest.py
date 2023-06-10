import sys
import pytest

from pathlib import Path

if True:
    sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from bantam.http import WebApplication



@pytest.fixture()
def clear_web_app():
    WebApplication._context= {}
    WebApplication._class_instance_methods = {}
    WebApplication._instance_methods_class_map= {}
    WebApplication._instance_methods = []
    WebApplication._all_methods = []
    WebApplication.routes_get = {}
    WebApplication.routes_post = {}
    WebApplication.callables_get = {}
    WebApplication.callables_post = {}
    WebApplication.module_mapping_get = {}
    WebApplication.module_mapping_post = {}
    yield
