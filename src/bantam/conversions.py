"""
package for conversions to/from text or json
"""
import dataclasses
import datetime
import json
import types
import typing
import uuid
from pathlib import Path, WindowsPath, PosixPath
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
    elif type(val) in (str, int, float, bool, PosixPath, WindowsPath, Path):
        json_data = val
    elif type(val) in (datetime.datetime, ):
        json_data = val.isoformat()
    elif type(val) in (uuid.UUID, ):
        json_data = str(val)
    elif type(val) in [dict] or (getattr(type(val), '_name', None) in ('Dict', 'Mapping')):
        json_data = {}
        for key, value in val.items():
            json_data[to_str(key)] = normalize_to_json_compat(value)
    elif type(val) in [list, set, tuple] or (getattr(type(val), '_name', None) in ('List', 'Set', 'Tuple')):
        json_data = []
        for value in val:
            json_data.append(normalize_to_json_compat(value))
    else:
        raise RuntimeError(f"Unsupported type for conversion: {type(val)}")
    return json_data


def normalize_from_json(json_data, typ) -> Any:
    if typ is None or json_data is None:
        return None
    try:
        if isinstance(json_data, str) and str(typ(json_data)) == json_data:
            return typ(json_data)
    except Exception:
        pass
    if isinstance(typ, types.UnionType):
        for arg in typ.__args__:
            if arg in (str, int, float, bool) and type(json_data) == arg:
                return json_data
            elif arg in (PosixPath, WindowsPath, Path, ) and type(json_data) == str:
                return Path(json_data)
            elif json_data == '' and arg is types.NoneType:
                return None
            elif arg in (str, int, float, bool):  # json  data does not match this type
                continue
            # noinspection PyBroadException
            try:
                return normalize_from_json(json_data, arg)  # recurse on arg type
            except Exception:
                continue
        raise TypeError(f"Cannot convert json data '{json_data}' to any of the Union types '{typ}'")
    if hasattr(typ, '_name') and (str(typ).startswith('typing.Union') or str(typ).startswith('typing.Optional')):
        for arg in typ.__args__:
            if arg in (str, int, float, ) and type(json_data) == arg:
                return json_data
            elif json_data == '' and arg is types.NoneType:
                return None
            elif json_data == '' and (arg is types.NoneType or arg is None):
                return None
            elif arg in (str, int, float):
                continue
            # noinspection PyBroadException
            try:
                return normalize_from_json(json_data, arg)
            except Exception:
                continue
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
    elif typ in (int, float, PosixPath, WindowsPath, Path):
        return typ(json_data)
    elif typ in (datetime.datetime, ):
        return datetime.datetime.fromisoformat(json_data)
    elif typ in (uuid.UUID, ):
        return uuid.UUID(json_data)
    elif typ == bool:
        return str(json_data).lower() == 'true'
    elif getattr(typ, '_name', None) in ('Dict', 'Mapping'):
        key_typ, elem_typ = typ.__args__
        return {
            normalize_from_json(k, key_typ):  normalize_from_json(v, elem_typ)
            for k, v in json_data.items()
        }
    elif getattr(typ, '_name', None) in ('List', ):
        return [normalize_from_json(value, typ.__args__[0]) for index, value in enumerate(json_data)]
    elif getattr(typ, '_name', None) in ('Set', ):
        return {normalize_from_json(value, typ.__args__[0]) for index, value in enumerate(json_data)}
    elif getattr(typ, '_name', None) in ('Tuple', ):
        if typ.__args__[-1] == type(None):  # var args
            return tuple(normalize_from_json(value, typ.__args__[0]) for index, value in enumerate(json_data))
        else:
            return tuple(normalize_from_json(value, typ.__args__[index]) for index, value in enumerate(json_data))

    elif hasattr(typ, '__dataclass_fields__'):
        return typ(**{
            name: normalize_from_json(json_data[name], field.type)
            for name, field in typ.__dataclass_fields__.items()
        })
    else:
        raise TypeError(f"Unsupported typ for web api: '{typ}'")


def to_str(val: Any) -> Optional[str]:
    if val is None:
        return None
    try:
        typ = type(val)
        if typ(str(val)) == val:
            return str(val)
    except Exception:
        pass
    if hasattr(val, '__dataclass_fields__'):
        val = normalize_to_json_compat(val)
        return json.dumps(val)
    elif isinstance(val, Enum):
        return val.value
    elif type(val) == bool:
        return str(val).lower()
    elif type(val) in (str, int, float, PosixPath, WindowsPath, Path):
        return str(val)
    elif type(val) in (datetime.datetime, ):
        return val.isoformat()
    elif type(val) in (uuid.UUID, ):
        return str(val)
    elif type(val) in [dict] or (getattr(type(val), '_name', None) in ('Dict', 'Mapping')):
        val = normalize_to_json_compat(val)
        return json.dumps(val)
    elif type(val) in [list] or (getattr(type(val), '_name', None) in ('List', )):
        val = normalize_to_json_compat(val)
        return json.dumps(val)
    elif type(val) in [set, tuple] or (getattr(type(val), '_name', None)) in ('Set', 'Tuple', ):
        val = normalize_to_json_compat(list(val))
        return json.dumps(val)
    raise TypeError(f"Type of value, '{type(val)}' is not supported in web api")


def _issubclass_safe(typ, clazz):
    # noinspection PyBroadException
    try:
        return issubclass(typ, clazz)
    except Exception:
        return False


def from_str(image: str, typ: Type | types.UnionType) -> Any:
    if (hasattr(typ, '_name') and (str(typ).startswith('typing.Union') or str(typ).startswith('typing.Optional')))\
            or isinstance(typ, types.UnionType):
        # noinspection PyUnresolvedReferences
        allow_none = str(typ).startswith('typing.Optional') or None in typ.__args__
        if allow_none and not image:
            # TODO: cannot really distinguish when return type is Optional[bytes] whether
            #   None or bytes() should be returned
            return None
        # noinspection PyUnresolvedReferences
        for arg in typ.__args__:
            try:
                if not image and arg is types.NoneType:
                    return None
                return arg(image)
            except ValueError:
                continue
        typ = typ.__args__[0]
    #######
    if _issubclass_safe(typ, Enum):
        return typ(image)
    elif typ == str:
        return image
    elif typ in (int, float, PosixPath, WindowsPath, Path):
        return typ(image)
    elif typ in (datetime.datetime, ):
        return datetime.datetime.fromisoformat(image)
    elif typ in (uuid.UUID,):
        return uuid.UUID(image)
    elif typ == bool:
        return image.lower() == 'true'
    elif getattr(typ, '_name', None) in ('Dict', 'List', 'Mapping'):
        return normalize_from_json(json.loads(image), typ)
    elif getattr(typ, '_name', None) in ('Set', 'Tuple'):
        return normalize_from_json(json.loads(image), typ)
    elif hasattr(typ, '__dataclass_fields__'):
        return normalize_from_json(json.loads(image), typ)
    elif typ is None:
        if image:
            raise ValueError(f"Got a return of {image} for a return type of None")
        return None
    else:
        raise TypeError(f"Unsupported typ for web api: '{typ}'")
