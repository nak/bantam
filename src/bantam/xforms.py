import base64
import json

from typing import Dict, Any, Type
from typing_extensions import Protocol


class IsDataclass(Protocol):
    # as already noted in comments, checking for this attribute is currently
    # the most reliable way to ascertain that something is a dataclass
    __dataclass_fields__: Dict


def serialize(data: IsDataclass) -> bytes:
    if not hasattr(data, "__dataclass_fields__"):
        raise TypeError(f"Expected a @dataclass, but found type {type(data)}")
    m: Dict[str, Any] = {}
    for field_name, typ in data.__dataclass_fields__:
        value = getattr(data, field_name)
        if isinstance(value, (str, bool, int, float)):
            m[field_name] = value
        elif isinstance(value, bytes):
            m[field_name] = base64.b64encode(value)
        elif hasattr(value, "__dataclass_fields__"):
            # recurse
            m[field_name] = serialize(value)
        else:
            raise TypeError("Excpected field value of one of str, bytes, int, float, bool or a @dataclass")
    obj = json.loads(str(m))
    return json.dumps(obj).encode('utf-8')


def deserialize(data: bytes, typ: Type[IsDataclass]) -> IsDataclass:
    fields = typ.__dataclass_fields__
    obj = json.loads(data.decode('utf-8'))
    for key, value in obj:
        if isinstance(value, dict):
            obj[key] = deserialize(data, fields[key])
        elif fields[key] == bytes:
            obj[key] = value.decode('ascii')
    return typ(**obj)
