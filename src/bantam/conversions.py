"""
package for conversions to/from text or json
"""
import dataclasses
import json
from typing import Type, Any


def to_str(val: Any) -> str:
    if hasattr(val, '__dataclass_fields__'):
        mapping = dataclasses.asdict(val)
        for key in mapping.keys():
            if hasattr(mapping[key], '__dataclass_fields__'):
                mapping[key] = to_str(mapping[key])
        return json.dumps(mapping)
    elif type(val) == str:
        return val
    elif type(val) in (int, float, bool):
        return str(val).lower()
    elif type(val) in [dict, list]or (getattr(type(val), '_name', None) in ('Dict', 'List', 'Mapping')):
        return json.dumps(val)
    raise TypeError(f"Type of value, '{type(val)}' is not supported in web api")


def from_str(image: str, typ: Type) -> Any:
    if hasattr(typ, '_name') and (str(typ).startswith('typing.Union') or str(typ).startswith('typing.Optional')):
        typ = typ.__args__[0]
    if typ == str:
        return image
    elif typ in (int, float):
        return typ(image)
    elif typ == bool:
        return image.lower() == 'true'
    elif typ in (dict, list) or (getattr(typ, '_name', None) in ('Dict', 'List', 'Mapping')):
        return json.loads(image)
    elif hasattr(typ, '__dataclass_fields__'):
        mapping = json.loads(image)
        for name, field in typ.__dataclass_fields__.items():
            if name not in mapping:
                raise ValueError(f"Provided value does not mapping to datacalsss {typ}: missing field {name}")
            if hasattr(field.type, '__dataclass_fields__'):
                mapping[name] = from_str(json.dumps(mapping[name]), field.type)
        return typ(**mapping)
    else:
        raise TypeError(f"Unsupported typ for web api: '{typ}'")
