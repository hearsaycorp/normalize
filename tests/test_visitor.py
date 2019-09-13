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

from builtins import str, range
from past.builtins import basestring
from datetime import datetime
import six
import json
from time import time
import types
import unittest

import normalize.exc as exc
from normalize.coll import list_of
from normalize.record import Record
from normalize.visitor import VisitorPattern

from .testclasses import (
    acent,
    acent_attributes,
    JsonStarList,
    maia,
    NamedStarList,
    PullRequest,
    StarList,
    StarSystem,
    Wall,
    wall_one
)

JSON_CAN_DUMP = (basestring, float, dict, list, type(None)) + six.integer_types


class SimpleDumper(VisitorPattern):

    @classmethod
    def apply(self, value, *args):
        if isinstance(value, JSON_CAN_DUMP):
            dumpable = value
        elif isinstance(value, datetime):
            dumpable = value.isoformat()
        else:
            raise Exception("Can't dump %r" % value)
        return dumpable


class AssertDiffTest(unittest.TestCase):
    def assertDiffs(self, a, b, expected, **kwargs):
        differences = set(str(x) for x in a.diff(b, **kwargs))
        self.assertEqual(
            differences,
            set("<DiffInfo: %s>" % x for x in expected)
        )


class TestVisitor(AssertDiffTest):
    def setUp(self):
        self.acent_json_data = {
            'name': 'Alpha Centauri',
            'components': [{'hip_id': 71683, 'name': 'Alpha Centauri A'},
                           {'hip_id': 71681, 'name': 'Alpha Centauri B'},
                           {'hip_id': 70890, 'name': 'Alpha Centauri C'}],
            'attributes': acent_attributes,
        }
        self.nsl_json_data = {
            'name': 'Alpha Centauri',
            'values': self.acent_json_data['components']
        }

    def test_simple_dumper(self):
        dumpable = SimpleDumper.visit(wall_one)
        self.assertIsInstance(dumpable['posts'][0], dict)
        self.assertEqual(dumpable['posts'][0]['edited'], "2001-09-09T01:46:40")
        json.dumps(dumpable)  # assert doesn't throw
        wall_roundtripped = SimpleDumper.cast(Wall, dumpable)
        self.assertDiffs(wall_one, wall_roundtripped, {})
        self.assertDiffs(wall_one, Wall(dumpable), {})

    def test_intro_example_dump(self):
        dumped = SimpleDumper.visit(acent)
        self.assertEqual(dumped, self.acent_json_data)

    def test_intro_example_cast(self):
        self.assertDiffs(acent, StarSystem(self.acent_json_data), {})
        self.assertDiffs(
            acent, SimpleDumper.cast(StarSystem, self.acent_json_data),
            {},
        )

    def test_complex_dump(self):
        nsl = NamedStarList(acent.components)
        nsl.name = "Alpha Centauri"
        dumped = SimpleDumper.visit(nsl)
        self.assertEqual(dumped, self.nsl_json_data)

    def test_complex_dump2(self):
        dumped = SimpleDumper.visit(maia)
        maia2 = SimpleDumper.cast(type(maia), dumped)
        self.assertEqual(maia.diff(maia2), [])
        self.assertEqual(maia2.coordinates['ICRS'][2], "49.60656")
        self.assertEqual(maia2.designations['HR'], "1149")

    def test_complex_cast(self):
        nsl = NamedStarList(**(self.nsl_json_data))
        self.assertDiffs(
            nsl, SimpleDumper.cast(NamedStarList, self.nsl_json_data),
            {},
        )

    def test_dump_types(self):
        typeinfo = SimpleDumper.reflect(NamedStarList)
        self.assertEqual(
            typeinfo['itemtype']['properties']['hip_id']['type'],
            'int',
        )
        typeinfo = SimpleDumper.reflect(Wall)
        self.assertEqual(typeinfo['properties']['owner']['name'], 'Person')
        self.assertEqual(
            typeinfo['properties']['owner']['properties']['interests']['type'],
            'list',
        )

    def test_json_dump(self):
        plain_list = StarList(self.acent_json_data['components'])
        json_list = JsonStarList(self.acent_json_data['components'])
        plain_dumped = SimpleDumper.visit(plain_list)
        json_dumped = SimpleDumper.visit(json_list)
        self.assertEqual(plain_dumped, json_dumped)

    def test_cast_garbage(self):
        for garbage in (
            "green cheese", [], (),
            {'values': {"foo": "bar"}},
            self.acent_json_data['components'],
        ):
            with self.assertRaises(exc.VisitorGrokRecordError):
                SimpleDumper.cast(NamedStarList, garbage)

    def test_cast_complex_filtered(self):
        # this works because the properties are filtered out; normally this
        # filtering would be due to 'extraneous' property settings.
        # MultiFieldSelector doesn't currently distinguish between 'None' =>
        # all items in collection vs 'None' => all, so use a filter which
        # mentions each of the items in the set.
        nsl = SimpleDumper.cast(
            NamedStarList,
            self.acent_json_data['components'],
            visit_filter=tuple([x, 'hip_id'] for x in range(0, 3)),
        )
        self.assertEqual(len(nsl), 3)

    def test_visit_complex_filtered(self):
        nsl = NamedStarList(**(self.nsl_json_data))
        visited = SimpleDumper.visit(
            nsl, filter=tuple([x, 'hip_id'] for x in range(0, 3)),
        )
        self.assertEqual(
            visited, list(
                {'hip_id': x['hip_id']} for x in
                self.acent_json_data['components']
            ),
        )


class TestTypeUnionCases(AssertDiffTest):
    def setUp(self):
        self.open_pr = PullRequest(number=123, merged_at=None)
        self.closed_pr = PullRequest(
            number=456,
            merged_at=datetime.fromtimestamp(time() - 20 * 86400),
        )

    def test_type_union_dump(self):
        dumped = SimpleDumper.visit(self.open_pr, ignore_none=False)
        self.assertIn("created_at", dumped)
        self.assertRegexpMatches(
            dumped['created_at'], r'^\d{4}-\d{2}-\d{2}T.*',
        )
        self.assertEqual(dumped['merged_at'], None)

        dumped = SimpleDumper.visit(self.closed_pr)
        self.assertRegexpMatches(
            dumped['created_at'], r'^\d{4}-\d{2}-\d{2}T.*',
        )
        self.assertIn("created_at", dumped)
        self.assertIn('merged_at', dumped)

    def test_type_union_load(self):
        pr_dict = {
            "number": "5125",
            "created_at": "2014-07-23T12:34:56Z",
            "merged_at": None,
        }
        my_pr = PullRequest(pr_dict)
        pr_2 = SimpleDumper.cast(PullRequest, pr_dict, ignore_none=False)
        self.assertDiffs(my_pr, pr_2, {})

    def test_type_union_typeinfo(self):
        schema = SimpleDumper.reflect(PullRequest)
        self.assertEqual(schema['properties']['merged_at']['type'],
                         ["datetime", "NoneType"])

    def test_cast_collection(self):
        RecordList = list_of(Record)
        casted = VisitorPattern.cast(RecordList, [{}, {}])
        self.assertIsInstance(casted[0], Record)
        self.assertIsInstance(casted, RecordList)

        empty_casted = VisitorPattern.cast(RecordList, [])
        self.assertIsInstance(empty_casted, RecordList)
