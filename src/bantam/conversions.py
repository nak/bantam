"""
package for conversions to/from text or json
"""
import dataclasses
import json
import typing
from typing import Type, Any, Optional
from enum import Enum
assert typing


def normalize_to_json_compat(val: Any) -> Any:
    if val is None:
        return None
    if hasattr(val, '__dataclass_fields__'):
        json_data = dataclasses.asdict(val)
        for key in json_data.keys():
            if json_data[key] is not None:
                json_data[key] = normalize_to_json_compat(json_data[key])
    elif isinstance(val, Enum):
        json_data = normalize_to_json_compat(val.value)
    elif type(val) in (str, int, float, bool):
        json_data = val
    elif type(val) in [dict] or (getattr(type(val), '_name', None) in ('Dict', 'Mapping')):
        json_data = {}
        for key, value in val.items():
            json_data[key] = normalize_to_json_compat(value)
    elif type(val) in [list] or (getattr(type(val), '_name', None) in ('List', )):
        json_data = []
        for value in val:
            json_data.append(normalize_to_json_compat(value))
    else:
        raise RuntimeError(f"Unsupported type for conversion: {type(val)}")
    return json_data


def normalize_from_json(json_data, typ) -> Any:
    if typ is None or json_data is None:
        return None
    if hasattr(typ, '_name') and (str(typ).startswith('typing.Union') or str(typ).startswith('typing.Optional')):
        typ = typ.__args__[0]
        if str(typ).startswith('typing.Optional') and json_data == 'null':
            return None
    if _issubclass_safe(typ, Enum):
        for key in typ.__members__:
            t = type(typ.__members__[key].value)
            # noinspection PyBroadException
            try:
                v = normalize_from_json(json_data, t)
                return typ(v)
            except Exception:
                continue
        return typ(json_data)
    elif typ == str:
        return json_data
    elif typ in (int, float):
        return json_data
    elif typ == bool:
        return json_data.lower() == 'true'
    elif getattr(typ, '_name', None) in ('Dict', 'Mapping'):
        key_typ, elem_typ = eval(str(typ).split('[', maxsplit=1)[1][:-1])
        d = dict(json_data)
        for k, v in json_data.items():
            d[normalize_from_json(k, key_typ)] = normalize_from_json(v, elem_typ)
        return d
    elif getattr(typ, '_name', None) in ('List', ):
        elem_typ = eval(str(typ).split('[', maxsplit=1)[1][:-1])
        for index, value in enumerate(json_data):
            json_data[index] = normalize_from_json(value, elem_typ)
        return json_data
    elif hasattr(typ, '__dataclass_fields__'):
        for name, field in typ.__dataclass_fields__.items():
            json_data[name] = normalize_from_json(json_data[name], field.type)
        return typ(**json_data)
    else:
        raise TypeError(f"Unsupported typ for web api: '{typ}'")


def to_str(val: Any) -> Optional[str]:
    if val is None:
        return None
    if hasattr(val, '__dataclass_fields__'):
        val = normalize_to_json_compat(val)
        return json.dumps(val)
    elif isinstance(val, Enum):
        return val.value
    elif type(val) in (str, int, float, bool):
        return val
    elif type(val) in [dict] or (getattr(type(val), '_name', None) in ('Dict', 'Mapping')):
        val = normalize_to_json_compat(val)
        return json.dumps(val)
    elif type(val) in [list] or (getattr(type(val), '_name', None) in ('List', )):
        val = normalize_to_json_compat(val)
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
        # noinspection PyUnresolvedReferences
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
        return normalize_from_json(json.loads(image), typ)
    elif hasattr(typ, '__dataclass_fields__'):
        return normalize_from_json(json.loads(image), typ)
    elif typ is None:
        if image:
            raise ValueError(f"Got a return of {image} for a return type of None")
        return None
    else:
        raise TypeError(f"Unsupported typ for web api: '{typ}'")
