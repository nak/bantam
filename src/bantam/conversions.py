"""
package for conversions to/from text or json
"""
import dataclasses
import json
from typing import Type, Any
from enum import Enum


def to_str(val: Any) -> str:
    if hasattr(val, '__dataclass_fields__'):
        mapping = dataclasses.asdict(val)
        for key in mapping.keys():
            if mapping[key] is not None:
                mapping[key] = to_str(mapping[key])
        return json.dumps(mapping)
    elif isinstance(val, Enum):
        return val.value
    elif type(val) in (str, int, float, bool):
        return val
    elif type(val) in [dict, list] or (getattr(type(val), '_name', None) in ('Dict', 'List', 'Mapping')):
        return json.dumps(val)
    raise TypeError(f"Type of value, '{type(val)}' is not supported in web api")


def _issubclass_safe(typ, clazz):
    # noinspection PyBroadException
    try:
        return issubclass(typ, clazz)
    except Exception:
        return False


def from_str(image: str, typ: Type) -> Any:
    if hasattr(typ, '_name') and (str(typ).startswith('typing.Union') or str(typ).startswith('typing.Optional')):
        typ = typ.__args__[0]
    #######
    if _issubclass_safe(typ, Enum):
        return typ(image)
    elif typ == str:
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
                raise ValueError(f"Provided value does not mapping to dataclasss {typ}: missing field {name}")
            if hasattr(field.type, '__dataclass_fields__'):
                mapping[name] = from_str(json.dumps(mapping[name]), field.type)
            else:
                mapping[name] = from_str(mapping[name], field.type)
        return typ(**mapping)
    elif typ is None:
        if image:
            raise ValueError(f"Got a return of {image} for a return type of None")
        return None
    else:
        raise TypeError(f"Unsupported typ for web api: '{typ}'")
