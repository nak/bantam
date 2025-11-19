import datetime
import json
import uuid
from dataclasses import dataclass
from pathlib import Path, PosixPath
from typing import Dict, List, Union, Tuple, Set, Optional

import pytest

from bantam.conversions import to_str, from_str, normalize_from_json


class Test:
    def test_to_str_from_tuple(self):
        assert to_str((1, '2')) == json.dumps([1, '2'])

    def test_to_str_from_set(self):
        assert to_str({1, '2'}) in (json.dumps([1, '2']), json.dumps(['2', 1]))

    def test_to_str_from_int(self):
        assert to_str(1343) == "1343"
        assert to_str(-1343) == "-1343"

    def test_to_str_from_float(self):
        assert to_str(-0.345) == "-0.345"

    def test_to_str_from_bool(self):
        assert to_str(True) == "true"
        assert to_str(False) == "false"

    def test_to_str_from_list(self):
        assert to_str(['a', 'b', 'c']) == json.dumps(['a', 'b', 'c'])

    def test_to_str_from_dict(self):
        assert to_str({'a': 1, 'b': 3, 'c': 'HERE'}) == json.dumps({'a': 1, 'b': 3, 'c': 'HERE'})

    def test_to_str_from_dataclass(self):
        @dataclass
        class SubData:
            s: str
            l: List[int]

        @dataclass
        class Data:
            f: float
            i: int
            d: Dict[str, str]
            subdata: SubData

        fval = 8883.234
        subd = SubData("name", [1, -5, 34])
        data = Data(fval, 99, {'A': 'a'}, subd)
        assert to_str(data) == json.dumps({
            'f': data.f,
            'i': 99,
            'd': {'A': 'a'},
            'subdata': {'s': "name", 'l': [1, -5, 34]}
        })

    def test_int_from_str(self):
        assert from_str("1234", int) == 1234

    def test_uuid_from_str(self):
        u = uuid.uuid4()
        assert from_str(str(u), uuid.UUID) == u

    def test_optional_int_from_str(self):
        assert from_str("1234", Optional[int]) == 1234
        assert from_str('', Optional[int]) == None
        assert from_str('', int | None) == None

    def test_datetime_from_str(self):
        d = datetime.datetime.now()
        assert from_str(d.isoformat(), datetime.datetime) == d
        assert normalize_from_json(d.isoformat(), datetime.datetime) == d

    def test_float_from_str(self):
        assert from_str("-9.3345", float) == pytest.approx(-9.3345)
        assert normalize_from_json('9.3345', float) == pytest.approx(9.3345)

    def test_path_from_str(self):
        assert from_str("/usr/bin", Path) == Path("/usr/bin")
        assert normalize_from_json("/no/path", PosixPath) == Path("/no/path")

    def test_bool_from_str(self):
        assert from_str("TruE", bool) is True
        assert from_str("false", bool) is False
        assert normalize_from_json("true", bool) is True

    def test_list_from_str(self):
        assert from_str("[0, -3834, 3419]", List[int]) == [0, -3834, 3419]
        assert normalize_from_json(['0', '-3834', '3419'], List[int]) == [0, -3834, 3419]

    def test_set_from_str(self):
        assert from_str("[0, -3834, 3419]", Set[int]) == {0, -3834, 3419}
        assert normalize_from_json(['0', '-3834', '3419'], Set[int]) == {0, -3834, 3419}

    def test_tuple_from_str(self):
        assert from_str("[0, -3834, \"hello\"]", Tuple[int, int, str]) == (0, -3834, "hello")
        assert normalize_from_json(['0', '-3834', "hello"], Tuple[int, int, str]) == (0, -3834, "hello")

    def test_dict_from_str(self):
        d = {'name': 'Jane', 'val': 34}
        assert from_str(json.dumps(d), Dict[str, Union[str, int]]) == d
        assert normalize_from_json(d, Dict[str, Union[str, int]]) == d
        assert from_str(json.dumps(d), Dict[str, str | int]) == d
        assert normalize_from_json(d, Dict[str, str | int]) == d

    def test_dataclass_from_str(self):

        @dataclass
        class SubData:
            s: str
            l: List[int]

        @dataclass
        class Data:
            f: float
            i: int
            d: Dict[str, str]
            subdata: SubData

        d = {
            'f': 0.909222,
            'i': 99,
            'd': {'A': 'a'},
            'subdata': {'s': "name", 'l': [1, -5, 34]}
        }
        raw_data = d.copy()
        image = json.dumps(d)
        d['subdata'] = SubData(**d['subdata'])
        assert from_str(image, Data) == Data(**d)
        assert normalize_from_json(raw_data, Data) == Data(**d)
