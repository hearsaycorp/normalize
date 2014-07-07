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

import copy
from datetime import datetime
import unittest

from normalize.coll import Collection
from normalize.diff import *
from normalize.record import Record
from normalize.property import Property
from normalize.property import SafeProperty
from normalize.property.coll import ListProperty
from testclasses import *


class TestRecordComparison(unittest.TestCase):
    def setUp(self):
        self.minimal = LegalPerson(id=7)
        self.foo1 = LegalPerson(id="2", name="foo")
        self.foo2 = LegalPerson(id="2", name="foo")

        self.bob1 = Person(id=123, name="Bob", age=32)
        self.bill = Person(id=123, name="Bill", age=34)
        self.bob2 = Person(id=124, name="Bob", age=36)
        self.bob1a = Person(id=123, name="Bob", age=32, kids=1)

    def assertDifferences(self, iterator, expected):
        differences = set(str(x) for x in iterator)
        self.assertEqual(
            differences,
            set("<DiffInfo: %s>" % x for x in expected)
        )

    def test_diff_types(self):
        dt = DiffTypes.MODIFIED
        self.assertEqual(dt.canonical_name, "modified")
        self.assertEqual(dt, DiffTypes.from_canonical(dt.canonical_name))

    def test_stringify(self):
        """Test behavior of Record.__str__"""
        # this actually uses repr()
        self.assertEqual(str(self.foo1), str(self.foo2))

        # primary keys affect stringification
        self.assertEqual(str(self.bob1), str(self.bill))
        self.assertNotEqual(str(self.bob1), str(self.bob2))

        # stringification only defined (informally!) for PK-items
        self.assertEqual(str(self.bob1), "<Person 123>")

    def test_repr(self):
        """Test behavior of Record.__repr__"""
        self.assertEqual(repr(self.foo1), "LegalPerson(id=2, name='foo')")
        self.assertEqual(repr(self.minimal), "LegalPerson(id=7)")

    def test_eq(self):
        """Test behavior of Record.__eq__ && .__ne__"""
        self.assertEqual(self.foo1, self.foo2)
        self.assertNotEqual(self.bob1, self.bill)
        self.assertNotEqual(self.bob1, self.bob2)
        self.assertEqual(self.bob1, self.bob1a)
        self.assertNotEqual(self.bob1, self.minimal)

    def test_pk_eq(self):
        """Test behavior of Record.__pk__"""
        self.assertEqual(self.foo1.__pk__, (2, "foo"))
        self.assertEqual(self.bob1.__pk__, (123,))

    def test_diff_collection_complex_pk(self):
        class Component(Record):
            ident = Property(isa=str)
            pk = (ident)

        class Compound(Record):
            part_a = Property(isa=Component)
            part_b = Property(isa=Component)
            pk = [part_a, part_b]

        class CompoundListHolder(Record):
            parts = ListProperty(of=Compound)

        first = Compound(part_a=Component(ident='a'), part_b=Component(ident='b'))
        second = Compound(part_a=Component(ident='a'), part_b=Component(ident='b'))
        holder = CompoundListHolder(parts=[first])
        other_holder = CompoundListHolder(parts=[second])
        diff_a = holder.diff(other_holder)
        self.assertEqual([], diff_a.values)
        second.part_a.ident = 'z'
        diff_b = holder.diff(other_holder)
        self.assertNotEqual([], diff_b.values)

    def test_diff_list(self):
        """Test diff'ing of simple lists/tuples"""
        self.assertDifferences(
            compare_list_iter(["Jokey", "Sweepy", "Baby"],
                              ["Grouchy", "Jokey", "Baby"]),
            ("REMOVED [1]", "ADDED [0]"),
        )

    def test_diff_dict(self):
        """Test diff'ing of dictionaries"""
        self.assertDifferences(
            compare_dict_iter({"FL": "Orange Blossom",
                               "LA": "Magnolia",
                               "MN": "Pink and white lady's-slipper"},
                              {"Kentucky": "Goldenrod",
                               "Louisiana": "Magnolia",
                               "Minnesota": "Pink and white lady's-slipper"}),
            ("REMOVED ['FL']", "ADDED ['Kentucky']"),
        )

        a = {
            "2001": u"Am\xE9lie",
            "1983": u"\xC0 nos amour",
            "1955": "Les Diaboliques",
        }
        b = {
            "2001": u"Ame\u0301lie",
            "1983": u"\xC0 nos\u2003amour",
            "1955": "les Diaboliques",
        }

        self.assertDifferences(
            compare_dict_iter(a, b, options=DiffOptions(ignore_case=True)),
            (),
        )
        self.assertDifferences(
            compare_dict_iter(a, b),
            {"REMOVED ['1955']", "ADDED ['1955']"},  # :-/
        )
        self.assertDifferences(
            compare_dict_iter(a, b, options=DiffOptions(ignore_ws=False,
                                                        ignore_case=True)),
            {"REMOVED ['1983']", "ADDED ['1983']"},
        )
        self.assertDifferences(
            compare_dict_iter(a, b, options=DiffOptions(unicode_normal=False,
                                                        ignore_case=True,
                                                        ignore_ws=True)),
            {"REMOVED ['2001']", "ADDED ['2001']"},
        )

    def test_diff_record(self):
        """Test diff'ing of simple records"""
        self.assertDifferences(
            compare_record_iter(self.bob1, self.bill),
            ("MODIFIED .name", "MODIFIED .age"),
        )
        # test extraneous properties don't make a difference
        self.assertDifferences(
            compare_record_iter(self.bob1, self.bob1a), {}
        )
        with self.assertRaises(TypeError):
            for x in compare_record_iter(self.foo1, self.bob1):
                pass

        self.assertDifferences(
            compare_record_iter(
                self.foo1, self.bob1, options=DiffOptions(duck_type=True),
            ),
            {"MODIFIED .id", "MODIFIED .name"}
        )
        self.assertDifferences(
            compare_record_iter(
                self.bob1, self.foo1, options=DiffOptions(duck_type=True),
            ),
            {"MODIFIED .id", "MODIFIED .name", "REMOVED .age"}
        )

        self.assertDifferences(
            compare_record_iter(
                self.bob1, Person(id=123, name="Bob Dobalina",
                                  interests=["fraudulent behavior"]),
            ),
            {"REMOVED .age", "MODIFIED .name", "ADDED .interests"},
        )

        self.assertDifferences(
            compare_record_iter(
                Person(id=123, name=""), Person(id=123),
            ),
            {"REMOVED .name"},
        )
        self.assertDifferences(
            compare_record_iter(
                Person(id=123, name=""), Person(id=123),
                options=DiffOptions(ignore_empty_slots=True),
            ),
            {},
        )

    def test_diff_unicode(self):
        """Test behavior of unicode string comparisons"""
        ubert = Person(id=123, name=u"Bert")
        bert = Person(id=123, name="Bert")
        self.assertDifferences(
            compare_record_iter(bert, ubert), ()
        )
        bert.name = "Bert "
        self.assertDifferences(compare_record_iter(bert, ubert), ())
        self.assertDifferences(
            compare_record_iter(bert, ubert,
                                options=DiffOptions(ignore_ws=False)),
            {"MODIFIED .name"},
        )

        ubert.name = u"Ba\u0304te"  # closer to "bart", but whatever
        bert.name = u"B\u0101te "
        self.assertDifferences(compare_record_iter(bert, ubert), ())
        self.assertDifferences(
            compare_record_iter(bert, ubert,
                                options=DiffOptions(unicode_normal=False)),
            {"MODIFIED .name"},
        )

        bert.name = bert.name.upper()
        self.assertDifferences(
            compare_record_iter(bert, ubert), {"MODIFIED .name"},
        )
        self.assertDifferences(
            compare_record_iter(bert, ubert,
                                options=DiffOptions(ignore_case=True)),
            (),
        )

    def test_diff_collection(self):
        """Test diff'ing of collections"""
        circle_a = Circle(
            members=(self.bob2, self.bob1, self.bill),
        )
        circle_b = Circle(
            members=(self.bill, Person(id=125, name="Bert")),
        )
        self.assertIsInstance(circle_a.members, Collection)

        expected_a_to_b = {
            "REMOVED [0]",
            "REMOVED [2]",
            "MODIFIED ([1].name/[0].name)",
            "MODIFIED ([1].age/[0].age)",
            "ADDED [1]",
        }
        self.assertDifferences(
            compare_collection_iter(circle_a.members, circle_b.members),
            expected_a_to_b
        )

        sparta = list()
        for member in circle_b.members:
            sparta.append(Spartan(member.__getstate__()))

        self.assertDifferences(
            compare_collection_iter(circle_b.members, sparta,
                                    options=DiffOptions(duck_type=True)),
            {}
        )
        self.assertDifferences(
            compare_collection_iter(circle_a.members, sparta,
                                    options=DiffOptions(duck_type=True)),
            expected_a_to_b
        )

    def test_complex_objects(self):
        """Test that all the pieces work together"""
        expected_differences = (
            {
                'REMOVED .posts[0].comments[0]',
                'ADDED .posts[0].comments[2]',
                'MODIFIED .posts[0].content',
                'MODIFIED .posts[0].edited',
                'REMOVED .owner.interests[1]',
                'REMOVED (.posts[0].comments[1].poster.interests[1]/'
                '.posts[0].comments[0].poster.interests)',
                "ADDED (.posts[0].comments[2].poster.info/"
                ".posts[0].comments[1].poster.info['birth name'])",
            }
        )

        self.assertDifferences(
            compare_record_iter(wall_one, wall_two), expected_differences,
        )
        self.assertDifferences(
            wall_one.diff_iter(wall_two), expected_differences,
        )
        difference = wall_one.diff(wall_two)
        self.assertEqual(len(difference), len(expected_differences))
        self.assertRegexpMatches(
            str(difference), r'<Diff \[Wall\]; \d+ item\(s\)>',
        )

        self.assertDifferences(
            compare_record_iter(wall_one, wall_two,
                                options=DiffOptions(unchanged=True)),
            expected_differences |
            {
                'UNCHANGED ('
                '.owner.interests[2]/'
                '.owner.interests[1])',
                'UNCHANGED ('
                '.posts[0].comments[1].content/'
                '.posts[0].comments[0].content)',
                'UNCHANGED ('
                '.posts[0].comments[1].edited/'
                '.posts[0].comments[0].edited)',
                'UNCHANGED ('
                '.posts[0].comments[1].id/'
                '.posts[0].comments[0].id)',
                'UNCHANGED ('
                '.posts[0].comments[1].poster.id/'
                '.posts[0].comments[0].poster.id)',
                'UNCHANGED ('
                '.posts[0].comments[1].poster.info.manner/'
                '.posts[0].comments[0].poster.info.manner)',
                'UNCHANGED ('
                '.posts[0].comments[1].poster.info.title/'
                '.posts[0].comments[0].poster.info.title)',
                'UNCHANGED ('
                '.posts[0].comments[1].poster.interests[0]/'
                '.posts[0].comments[0].poster.interests[0])',
                'UNCHANGED ('
                '.posts[0].comments[1].poster.interests[2]/'
                '.posts[0].comments[0].poster.interests[1])',
                'UNCHANGED ('
                '.posts[0].comments[1].poster.name/'
                '.posts[0].comments[0].poster.name)',
                'UNCHANGED ('
                '.posts[0].comments[1]/'
                '.posts[0].comments[0])',
                'UNCHANGED ('
                '.posts[0].comments[2].content/'
                '.posts[0].comments[1].content)',
                'UNCHANGED ('
                '.posts[0].comments[2].edited/'
                '.posts[0].comments[1].edited)',
                'UNCHANGED ('
                '.posts[0].comments[2].id/'
                '.posts[0].comments[1].id)',
                'UNCHANGED ('
                '.posts[0].comments[2].poster.id/'
                '.posts[0].comments[1].poster.id)',
                'UNCHANGED ('
                '.posts[0].comments[2].poster.info.hair/'
                '.posts[0].comments[1].poster.info.hair)',
                'UNCHANGED ('
                '.posts[0].comments[2].poster.info.title/'
                '.posts[0].comments[1].poster.info.title)',
                'UNCHANGED ('
                '.posts[0].comments[2].poster.interests[0]/'
                '.posts[0].comments[1].poster.interests[0])',
                'UNCHANGED ('
                '.posts[0].comments[2].poster.interests[1]/'
                '.posts[0].comments[1].poster.interests[1])',
                'UNCHANGED ('
                '.posts[0].comments[2].poster.name/'
                '.posts[0].comments[1].poster.name)',
                'UNCHANGED ('
                '.posts[0].comments[2]/'
                '.posts[0].comments[1])',
                'UNCHANGED .id',
                'UNCHANGED .owner.id',
                'UNCHANGED .owner.info.manner',
                'UNCHANGED .owner.info.title',
                'UNCHANGED .owner.interests[0]',
                'UNCHANGED .owner.name',
                'UNCHANGED .posts[0]',
                'UNCHANGED .posts[0].post_id',
                'UNCHANGED .posts[0].wall_id',
            },
        )
