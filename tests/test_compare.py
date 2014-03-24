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


class LegalPerson(Record):
    id = Property(required=True, isa=int)
    name = Property(isa=basestring, coerce=str)


class Person(LegalPerson):
    age = Property(isa=int)
    kids = Property(isa=int, extraneous=True)
    interests = SafeProperty(isa=list)
    info = SafeProperty(isa=dict)
    primary_key = ['id']


class Circle(Record):
    members = ListProperty(of=Person)


class Comment(Record):
    content = Property()
    edited = SafeProperty(required=True, isa=datetime)
    id = Property(required=True, isa=int)
    primary_key = [id]
    poster = Property(isa=Person)


class Post(Record):
    comments = ListProperty(of=Comment)
    content = Property()
    edited = SafeProperty(required=True, isa=datetime)
    post_id = Property(required=True, isa=int)
    wall_id = Property(required=True, isa=int)
    primary_key = [wall_id, post_id]


class Wall(Record):
    id = Property(required=True, isa=int)
    owner = Property(isa=Person)
    posts = ListProperty(of=Post)


# for testing comparison with "alien" classes
class Spartan(object):
    def __init__(self, data):
        for k, v in data.iteritems():
            setattr(self, k, v)


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
            sparta.append(Spartan(member.__getnewargs__()[0]))

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
        gary = dict(
            info={"title": "Superintendent", "manner": "Military"},
            id=1,
            interests=["coffee", "alcohol", "Agnes Skinner"],
            name="Gary Chamlers",
        )
        seymour = dict(
            info={"hair": "grey", "title": "Principal"},
            id=2,
            interests=["quality education", "hounding children"],
            name="Seymour Skinner",
        )
        willie = dict(
            info={"hair": "orange", "title": "Groundskeeper"},
            id=3,
            interests=["wolf wrestling", "swearing at French people"],
            name="Willie McLeod",
        )
        dialogue = [
            (seymour, "S-Superintendent Chalmers!"),
            (gary, "Whose tractor is this?!"),
            (seymour, "I-i-I'll look right into it, sir!"),
            (willie, "It's MINE, ya flippin' sock-sniffin' tatie eater!"),
        ]
        comments = []
        when = 10000000000
        id = 14
        for character, line in dialogue:
            when += 42
            id += 3
            comments.append(dict(id=id, edited=datetime.fromtimestamp(when),
                                 poster=character, content=line))

        wall_one = Wall(
            id=123,
            owner=copy.deepcopy(gary),
            posts=[
                {
                    "comments": copy.deepcopy(comments[0:3]),
                    "content": "SEY-MOUR!!!",
                    "edited": datetime.fromtimestamp(1000000000),
                    "post_id": 1,
                    "wall_id": 123,
                }
            ]
        )

        del gary['interests'][1]
        seymour['info']['birth name'] = "Armin Tamzarian"

        wall_two = Wall(
            id=123,
            owner=gary,
            posts=[
                {
                    "comments": comments[1:],
                    "content": "SEY-MOUR!!!!",
                    "edited": datetime.fromtimestamp(1000000240),
                    "post_id": 1,
                    "wall_id": 123,
                }
            ]
        )
        expected_differences = (
            {
                'REMOVED .posts[0].comments[0]',
                'ADDED .posts[0].comments[2]',
                'MODIFIED .posts[0].content',
                'MODIFIED .posts[0].edited',
                'REMOVED .owner.interests[1]',
                'REMOVED .posts[0].comments[1].poster.interests[1]',
                "ADDED .posts[0].comments[1].poster.info['birth name']",
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
