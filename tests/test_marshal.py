#
# This file is a part of the normalize python library
#
# normalize is free software: you can redistribute it and/or modify
# it under the terms of the MIT License.
#
# normalize is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# MIT License for more details.
#
# You should have received a copy of the MIT license along with
# normalize.  If not, refer to the upstream repository at
# http://github.com/hearsaycorp/normalize
#

from __future__ import absolute_import
from __future__ import print_function
import six

from builtins import str, zip, range
from past.builtins import basestring
import json
from os import environ
import pickle
import re
import unittest

from richenum import RichEnum
from richenum import RichEnumValue

import normalize.exc as exc
from normalize.record import Record
from normalize.record.json import from_json
from normalize.record.json import JsonRecord
from normalize.record.json import JsonRecordDict
from normalize.record.json import JsonRecordList
from normalize.record.json import to_json
from normalize.property import Property
from normalize.property import ROProperty
from normalize.property import SafeProperty
from normalize.property.coll import DictProperty
from normalize.property.coll import ListProperty
from normalize.property.json import JsonProperty
from normalize.property.json import JsonDictProperty
from normalize.property.json import JsonListProperty


class CheeseRecord(Record):
    variety = SafeProperty(isa=str)
    smelliness = SafeProperty(isa=float, check=lambda x: 0 < x < 100)


class CheeseCupboardRecord(Record):
    id = ROProperty(required=True, isa=int)
    name = SafeProperty(isa=str)
    best_cheese = SafeProperty(isa=CheeseRecord)
    cheeses = ListProperty(of=CheeseRecord)
    favorites = DictProperty(of=CheeseRecord)


json_data_number_types = (basestring, float) + six.integer_types


def decode_json_number(str_or_num):
    """Returns a precise number object from a string or number"""
    if isinstance(str_or_num, basestring):
        if re.match(r'-?\d+$', str_or_num):
            return six.integer_types[-1](str_or_num)
        if not re.match(r'-?\d+(\.\d+)?([eE][\-+]?\d+)?$', str_or_num):
            raise ValueError("invalid json number: '%s'" % str_or_num)
        return float(str_or_num)
    return str_or_num


class TestRecordMarshaling(unittest.TestCase):
    def setUp(self):
        self.primitive = {
            "id": "123",
            "name": "Fridge",
            "best_cheese": dict(variety="Gouda", smelliness="12"),
            "cheeses": [
                dict(variety="Manchego", smelliness="38"),
                dict(variety="Stilton", smelliness="82"),
                dict(variety="Polkobin", smelliness="31"),
            ],
            "favorites": {
                "Dorothy": dict(variety="Stracchinata", smelliness="28"),
                "Walter": dict(variety="Caciobufala", smelliness="32"),
                "Albert": dict(variety="Quartirolo Lombardo", smelliness="53"),
            },
        }

    def assertDataOK(self, ccr):
        self.assertIsInstance(ccr, CheeseCupboardRecord)
        self.assertEqual(ccr.id, 123)
        self.assertEqual(len(ccr.cheeses), 3)
        self.assertEqual(ccr.best_cheese.variety, "Gouda")
        self.assertEqual(ccr.cheeses[1].smelliness, 82)
        self.assertEqual(ccr.favorites['Walter'].variety, "Caciobufala")

    def assertJsonDataEqual(self, got, wanted, path=""):
        """Test that two JSON-data structures are the same.  We can't use
        simple assertEqual, because '23' and 23 should compare the same."""
        if isinstance(got, basestring):
            got = six.text_type(got)
        if isinstance(wanted, basestring):
            wanted = six.text_type(wanted)

        pdisp = path or "top level"

        if type(got) != type(wanted):
            if isinstance(got, json_data_number_types) and \
                    isinstance(wanted, json_data_number_types):
                got = decode_json_number(got)
                wanted = decode_json_number(wanted)
            else:
                raise AssertionError(
                    "types differ at %s: wanted %s, got %s" % (
                        pdisp, type(wanted).__name__, type(got).__name__
                    )
                )
        if type(got) == dict:
            all_keys = sorted(set(got) | set(wanted))
            for key in all_keys:
                if (key in got) != (key in wanted):
                    raise AssertionError(
                        "dictionary differs at %s: key %s is %s" % (
                            pdisp, key,
                            "unexpected" if key in got else "missing"
                        )
                    )
                else:
                    self.assertJsonDataEqual(
                        got[key], wanted[key], path + ("[%r]" % key)
                    )
        elif type(got) == list:
            for i in range(0, max((len(got), len(wanted)))):
                if i >= len(got) or i >= len(wanted):
                    raise AssertionError(
                        "lists differs in length at %s: got %d elements, "
                        "wanted %d" % (pdisp, len(got), len(wanted))
                    )
                else:
                    self.assertJsonDataEqual(
                        got[i], wanted[i], path + ("[%d]" % i)
                    )
        elif got != wanted:
            raise AssertionError(
                "values differ at %s: wanted %r, got %r" % (
                    pdisp, wanted, got
                )
            )
        elif "SHOW_JSON_TESTS" in environ:
            print("%s: ok (%r)" % (pdisp, got))

    def test_assertJsonDataEqual(self):
        """Answering the koan, "Who will test the tests themselves?"
        """
        float("inf")
        self.assertRaises(ValueError, decode_json_number, "inf")

        matches = (
            ("123", "123"), ("123", 123), (123, 123.0), ("123.0", 123),
            ("9223372036854775783", 2**63-25), ("-5e5", -500000),
            ({}, {}), ([], []), ({"foo": "bar"}, {"foo": "bar"}),
            ([{}, "foo", 123], [{}, "foo", 123.0]),
            ({"foo": [1, 2, 3], "bar": {"foo": "baz"}},
             {"foo": [1, 2, 3], "bar": {"foo": "baz"}}),
        )
        for a, b in matches:
            self.assertJsonDataEqual(a, b)

        mismatches = (
            (123, 124), ("foo", "bar"), (123, "foo"), (123, {}),
            ({}, 123), ([], {}), ("inf", float("inf")),
            (9.223372036854776e+18, 2**63-25),
            ({"foo": "bar"}, {"bar": "foo"}),
            ([1, 2, 3], [1, 2]), ([1, 2], [1, 2, 3]),
            ({"foo": [1, 2, 3], "bar": {"foo": "baz"}},
             {"foo": [1, 2, 3], "bar": {"foo": "bat"}}),
        )
        for a, b in mismatches:
            try:
                self.assertJsonDataEqual(a, b)
            except AssertionError:
                pass
            except ValueError:
                pass
            else:
                raise Exception("Compared equal: %r vs %r" % (a, b))

    def test_native_marshall(self):
        """Test coerce from python dicts & pickling"""
        ccr = CheeseCupboardRecord(self.primitive)
        for protocol in range(0, pickle.HIGHEST_PROTOCOL + 1):
            pickled = pickle.dumps(ccr, protocol)
            ccr_copy = pickle.loads(pickled)
            self.assertDataOK(ccr_copy)

    def test_json_marshall(self):
        """Test coerce from JSON & marshall out"""
        json_struct = json.dumps(self.primitive)
        ccr = from_json(CheeseCupboardRecord, json.loads(json_struct))
        self.assertDataOK(ccr)

        class RealWorldCCR(JsonRecord, CheeseCupboardRecord):
            pass

        ccr = RealWorldCCR.from_json(json_struct)
        self.assertDataOK(ccr)

        json_data = ccr.json_data()
        json.dumps(json_data)

        self.assertJsonDataEqual(json_data, self.primitive)

    def test_custom_json_prop_marshall(self):
        """Test customizing JSON marshalling using functions"""

        def date_in(struct):
            return "%.4d-%.2d-%.2d" % (
                struct.get("year", 0), struct.get("month", 0),
                struct.get("day", 0),
            )

        def date_out(val):
            return dict(
                (k, int(v)) for k, v in zip(
                    ("year", "month", "day"), val.split("-")
                ) if int(v) > 0
            )

        class PackedDate(Record):
            created_date = Property(
                check=lambda x: re.match(r'\d{4}-\d{2}-\d{2}', x),
                isa=str,
                json_in=date_in,
                json_name="created",
                json_out=date_out,
            )

        class JsonPackedDate(PackedDate, JsonRecord):
            pass

        json_in = {"created": {"year": 2012, "month": 7, "day": 12}}
        pd = from_json(PackedDate, json_in)
        self.assertEqual(pd.created_date, "2012-07-12")
        self.assertJsonDataEqual(to_json(pd), json_in)
        jpd = JsonPackedDate.from_json(json_in)
        self.assertJsonDataEqual(jpd.json_data(), json_in)

        json_in_2 = {"created": {"year": 2012, "month": 7}}
        jpd = JsonPackedDate.from_json(json_in_2)
        self.assertEqual(jpd.created_date, "2012-07-00")
        self.assertJsonDataEqual(jpd.json_data(), json_in_2)

        self.assertJsonDataEqual(
            to_json(jpd, prop="created_date"), json_in_2['created'],
        )
        self.assertJsonDataEqual(
            to_json(jpd, prop=PackedDate.created_date),
            json_in_2['created'],
        )

        # to_json should not emit keys for undefined values
        self.assertEqual(to_json(PackedDate()), {})
        self.assertEqual(to_json(CheeseRecord()), {})

        # unless they define defaults
        class DefaultNone(Record):
            none = Property(default=None)
            emptystring = Property(default="")
            false = Property(default=False)

        self.assertJsonDataEqual(
            to_json(DefaultNone()), {
                "none": None,
                "emptystring": "",
                "false": False,
            }
        )

    def test_custom_json_class_marshall(self):
        class StreamChunk(JsonRecordList):
            itemtype = CheeseRecord
            next_url = Property()
            previous_url = Property()

            @classmethod
            def json_to_initkwargs(cls, json_data, kwargs):
                paging = json_data.get('paging', {})
                kwargs['next_url'] = paging.get('next', None)
                kwargs['previous_url'] = paging.get('previous', None)
                kwargs = super(StreamChunk, cls).json_to_initkwargs(
                    json_data.get('data', []), kwargs,
                )
                return kwargs

            def json_data(self):
                return dict(
                    data=super(StreamChunk, self).json_data(),
                    paging=dict(
                        next=self.next_url,
                        previous=self.previous_url,
                    ),
                )

        chunk = {"data": self.primitive['cheeses'][0:2],
                 "paging": {"next": "stream_token_3", "previous": None}}

        sc = StreamChunk.from_json(chunk)
        self.assertEqual(sc.next_url, "stream_token_3")
        self.assertEqual(sc[0].smelliness, 38)
        self.assertJsonDataEqual(sc.json_data(), chunk)

        sc2 = StreamChunk(chunk)
        self.assertEqual(sc2.next_url, "stream_token_3")
        self.assertEqual(sc2[1].smelliness, 82)
        self.assertJsonDataEqual(sc2.json_data(), chunk)

        self.assertEqual(sc, sc2)
        sc3 = eval(repr(sc))
        self.assertEqual(sc, sc3)

    def test_json_unknown_keys(self):

        class JsonCheeseRecord(JsonRecord, CheeseRecord):
            unknown_json_keys = Property(json_name=None)

        input_json = dict(
            variety="Manchego",
            smelliness="38",
            origin="Spain",
        )

        jcr = JsonCheeseRecord(input_json)
        self.assertJsonDataEqual(jcr.json_data(), input_json)

        class RegularJsonCheeseRecord(JsonRecord, CheeseRecord):
            pass

        rjcr = RegularJsonCheeseRecord(input_json)
        diff = jcr.diff(rjcr, duck_type=True)
        if diff:
            self.fail("Found a difference: %s" % diff)

        jcr2 = JsonCheeseRecord(input_json)
        jcr2.variety += " (old)"
        jcr2.smelliness -= 5

        diff = jcr.diff(jcr2)
        diff_json = diff.json_data()
        self.assertEqual(len(diff_json), 2)
        self.assertTrue(all(x['diff_type'] == 'modified' for x in diff_json))

        sanitized = rjcr.json_data()
        self.assertNotIn("origin", sanitized)

        self.assertJsonDataEqual(rjcr.json_data(extraneous=True), input_json)

        class NestedJsonRecord(JsonRecord):
            cheese = Property(isa=JsonCheeseRecord)
            cheese_list = ListProperty(of=JsonCheeseRecord)

        nested_input = dict(
            cheese=input_json,
            cheese_list=[
                {"variety": "Cream Havarti",
                 "type": "semi-soft",
                 "color": "pale yellow"},
                {"variety": "Adelost",
                 "type": "semi-soft",
                 "color": "blue"},
            ],
        )

        nested_record = NestedJsonRecord(nested_input)

        self.assertJsonDataEqual(
            nested_record.json_data(extraneous=True),
            nested_input,
        )

    def test_json_round_trip(self):
        class Fruit(JsonRecord):
            protein = Property()
            fat = Property()
            carb = Property()

        class Banana(JsonRecord):
            color = Property(isa=str)
            length = Property(isa=int)
            contents = JsonProperty(isa=Fruit)
            vitamins = JsonProperty(isa=str)

        banana = Banana(
            color="yellow",
            contents={
                "carb": "23%",
                "fat": "0.5%",
                "protein": "1%",
            },
            vitamins={
                "A": "144 IU",
                "C": "19.6 mg",
                "E": "0.2 mg",
            },
            length=6,
        )

        self.assertEqual(
            Banana(banana.json_data(extraneous=True)),
            banana
        )

    def test_marshall_exceptions(self):
        class SomeRecordList(JsonRecordList):
            itemtype = CheeseRecord

        with self.assertRaisesRegexp(
                exc.JsonCollectionCoerceError, r'array expected',
        ):
            SomeRecordList({"foo": "bar"})

        class SomeRecordMap(JsonRecordDict):
            itemtype = CheeseRecord

        with self.assertRaisesRegexp(
                exc.JsonCollectionCoerceError, r'object expected',
        ):
            SomeRecordMap([1, 2, 3])

        class SomeRecord(JsonRecord):
            some_list = JsonListProperty(of=CheeseRecord)
            some_map = JsonDictProperty(of=CheeseRecord)

        with self.assertRaisesRegexp(
                exc.JsonConversionError, r'\.some_list\b.*array expected',
        ):
            SomeRecord({"some_list": {"foo": "bar"}})

        with self.assertRaisesRegexp(
                exc.JsonConversionError, r'\.some_map\b.*object expected',
        ):
            SomeRecord({"some_map": [1, 2, 3]})

        class SomeOtherRecord(JsonRecord):
            foo_bar = Property(isa=SomeRecord, json_name="fooBar")

        with self.assertRaisesRegexp(
            exc.JsonConversionError, r'\.fooBar\.some_list\b.*array expected',
        ):
            SomeOtherRecord({"fooBar": {"some_list": {"foo": "bar"}}})

        class WayRecord(JsonRecord):
            down = JsonListProperty(of=SomeOtherRecord)

        try:
            WayRecord(
                {"down": [
                    {"fooBar": {"some_list": {"foo": "bar"}}},
                ]}
            )
        except exc.JsonConversionError as e:
            self.assertEqual(e.error_fs.path, ".down[0].fooBar.some_list")

        class TurtlesRecord(JsonRecord):
            all_the = JsonDictProperty(json_name="allThe", of=WayRecord)

        try:
            TurtlesRecord(
                {"allThe": {"way": {"down": [
                    {"fooBar": {"some_list": {"foo": "bar"}}},
                ]}}}
            )
        except exc.JsonConversionError as e:
            self.assertEqual(
                e.error_fs.path,
                ".allThe.way.down[0].fooBar.some_list",
            )
            self.assertEqual(
                e.sub_exception.passed, {"foo": "bar"},
            )

    def test_rich_enum(self):
        class MyEnum(RichEnum):
            class EnumValue(RichEnumValue):
                def json_data(self):
                    return self.canonical_name

                @classmethod
                def from_json(self, string):
                    return MyEnum.from_canonical(string)

            ONE = EnumValue('one', "One")
            TWO = EnumValue('two', "Two")

        class EnumsGalore(JsonRecord):
            my_enum = JsonProperty(isa=MyEnum.EnumValue)
            enum_list = JsonListProperty(of=MyEnum.EnumValue)
            enum_map = JsonDictProperty(of=MyEnum.EnumValue)

        json = {"my_enum": "one",
                "enum_list": ["one", "two", "one"],
                "enum_map": {"x": "one", "y": "two", "z": "two"}}

        eg = EnumsGalore(json)
        self.assertEqual(eg.my_enum, MyEnum.ONE)
        self.assertEqual(eg.enum_list[2], MyEnum.ONE)
        self.assertEqual(eg.enum_map["z"], MyEnum.TWO)

        eg_json = eg.json_data()
        self.assertEqual(eg_json, json)
