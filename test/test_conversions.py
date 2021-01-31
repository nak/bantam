import json
from dataclasses import dataclass
from typing import Dict, List

import pytest

from bantam.conversions import to_str, from_str


class Test:
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

    def test_float_from_str(self):
        assert from_str("-9.3345", float) == pytest.approx(-9.3345)

    def test_bool_from_str(self):
        assert from_str("TruE", bool) is True
        assert from_str("false", bool) is False

    def test_list_from_str(self):
        assert from_str("[0, -3834, 3419]", list) == [0, -3834, 3419]

    def test_dict_from_str(self):
        d = {'name': 'Jane', 'val': 34}
        assert from_str(json.dumps(d), dict) == d

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
        image = json.dumps(d)
        d['subdata'] = SubData(**d['subdata'])
        assert from_str(image, Data) == Data(**d)
