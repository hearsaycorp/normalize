from __future__ import absolute_import

import json
from os import environ
import pickle
import re
import unittest2

from normalize.diff import compare_record_iter
from normalize.diff import DiffOptions
from normalize.record import Record
from normalize.record.json import from_json
from normalize.record.json import JsonRecord
from normalize.record.json import JsonRecordList
from normalize.record.json import to_json
from normalize.property import Property
from normalize.property import ROProperty
from normalize.property import SafeProperty
from normalize.property.coll import ListProperty


class CheeseRecord(Record):
    variety = SafeProperty(isa=str)
    smelliness = SafeProperty(isa=float, check=lambda x: 0 < x < 100)


class CheeseCupboardRecord(Record):
    id = ROProperty(required=True, isa=int)
    name = SafeProperty(isa=str)
    best_cheese = SafeProperty(isa=CheeseRecord)
    cheeses = ListProperty(of=CheeseRecord)


json_data_number_types = (basestring, int, long, float)


def decode_json_number(str_or_num):
    """Returns a precise number object from a string or number"""
    if isinstance(str_or_num, basestring):
        if re.match(r'-?\d+$', str_or_num):
            return long(str_or_num)
        if not re.match(r'-?\d+(\.\d+)?([eE][\-+]?\d+)?$', str_or_num):
            raise ValueError("invalid json number: '%s'" % str_or_num)
        return float(str_or_num)
    return str_or_num


class TestRecordMarshaling(unittest2.TestCase):
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
        }

    def assertDataOK(self, ccr):
        self.assertIsInstance(ccr, CheeseCupboardRecord)
        self.assertEqual(ccr.id, 123)
        self.assertEqual(len(ccr.cheeses), 3)
        self.assertEqual(ccr.best_cheese.variety, "Gouda")
        self.assertEqual(ccr.cheeses[1].smelliness, 82)

    def assertJsonDataEqual(self, got, wanted, path=""):
        """Test that two JSON-data structures are the same.  We can't use
        simple assertEqual, because '23' and 23 should compare the same."""
        if isinstance(got, basestring):
            got = unicode(got)
        if isinstance(wanted, basestring):
            wanted = unicode(wanted)

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
            print "%s: ok (%r)" % (pdisp, got)

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
        json_text = json.dumps(json_data)

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
