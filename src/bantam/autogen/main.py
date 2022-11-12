import importlib
import sys

from bantam.http import WebApplication


def _qual_name(typ):
    if hasattr(typ, '__qualname__'):
        return (typ.__module__ + '.' if typ.__module__ != 'builtins' else '') + typ.__qualname__
    return str(typ)


def main():
    if len(sys.argv) not in (2, 3):
        print(f"Usage: {sys.argv[0]} <module-name> [suffix-for-client-class]")
        sys.exit(1)
    module_name = sys.argv[1]
    class_suffix = sys.argv[2] if len(sys.argv) == 3 else ''
    # load the web_apis:
    importlib.import_module(module_name)
    apis = WebApplication.module_mapping_get.get(module_name, {})
    apis.update(
        WebApplication.module_mapping_post.get(module_name, {})
    )
    if not apis:
        print(f"No web_apis defined in {module_name}")
        sys.exit(2)
    by_class = {}
    for route, api in apis.items():
        class_name = route[1:].split('/')[0]
        assert class_name, f"Route has improper spec: '{route}'"
        by_class.setdefault(class_name, {})[route] = api

    for class_name, route_mapping in by_class.items():
        text = f"""
import typing
from bantam.client import WebInterface
from abc import abstractmethod
from bantam.http import web_api
from bantam.api import RestMethod

class {class_name}Interface(WebInterface):

    """
        method_text = ""
        imports = set()
        for route, api in route_mapping.items():
            target = route[1:].split('/', maxsplit=1)[1]
            args = api.arg_annotations
            arg_text = ', '.join(f"{arg_name}: {_qual_name(typ)}" for arg_name, typ in args.items())
            for typ in list(args.values()) + [api.return_type]:
                if typ.__module__ != 'builtins':
                    imports.add(f"import {typ.__module__}")
            web_api_args = \
                f"method={api.method}, content_type='{api.content_type}', is_constructor={api.is_constructor},"\
                f" uuid_param={api.uuid_param}"
            return_type = f"{_qual_name(api.return_type)}"
            if api.is_static:
                addl_decorator = "@staticmethod\n    "
            elif api.is_class_method:
                addl_decorator = "@classmethod\n    "
                arg_text = f"cls, {arg_text}"
            else:
                addl_decorator = ''
            if api.is_instance_method:
                arg_text = f"self, {arg_text}"
            method_text += f"""
    @web_api({web_api_args})
    {addl_decorator}@abstractmethod
    async def {target}({arg_text}) -> {return_type}:
        \"\"\"
        abstraction for {route} web-api route
        \"\"\"
"""
        sys.stdout.write('\n'.join(imports) + '\n')
        sys.stdout.write(text)
        sys.stdout.write(method_text)
        sys.stdout.write(f"""
        
{class_name}{class_suffix} = {class_name}Interface.Client
""")
        sys.stdout.write('\n')
    return 0


if __name__ == '__main__':
    main()
