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
from datetime import date
import re
import unittest

from normalize import Property
from normalize import Record
from normalize import RecordList
from normalize.diff import DiffOptions
from normalize.property.coll import ListProperty
from normalize.property.types import DateProperty
from normalize.property.types import IntProperty
from normalize.property.types import StringProperty
from normalize.property.types import UnicodeProperty
from normalize.selector import MultiFieldSelector


class Name(Record):
    given = UnicodeProperty()
    family = UnicodeProperty()


class SurrogatePerson(Record):
    name = Property(isa=Name)
    ssn = Property(isa=str, check=lambda x: re.match(r'\d{3}-\d{2}-\d{4}', x))
    date_of_birth = DateProperty()
    description = UnicodeProperty()
    phone_number = StringProperty()
    primary_key = [ssn]


class PersonWithFriends(SurrogatePerson):
    friends = ListProperty(of=SurrogatePerson)
    primary_key = ["ssn"]


PEOPLE = (
    ("James", "Miller", date(1960, 11, 18), '(239) 978-5912'),
    ("Aaron", "Mora", date(1963, 2, 20), '(262) 860-9595'),
    ("Laura", "Wolf", date(1966, 8, 13), '(480) 851-7810'),
    ("Steve", "Chen", date(1967, 6, 11), '(530) 922-5668'),
    ("Stephanie", "Hart", date(1971, 8, 3), '(614) 608-2940'),
    ("Kara", "Park", date(1972, 11, 22), '(406) 593-8495'),
    ("Ruben", "Haynes", date(1975, 4, 8), '(808) 643-7409'),
)

# simplified NANP regex
phone = re.compile(
    r"^(?:\+?1\s*(?:[.-]\s*)?)?(\d{3})\s*"
    r"(?:[.-]\s*)?(\d{3})\s*(?:[.-]\s*)?"
    r"(\d{4})"
)


def normalize_phone(phoney):
    m = re.match(phone, phoney)
    if m:
        return "(%s) %s-%s" % m.groups()
    else:
        return phoney


def get_person(i, *friends, **kwargs):
    x = PEOPLE[i]
    kwargs = dict(kwargs)
    if friends:
        kwargs["friends"] = list(get_person(x) for x in friends)
    if 'cls' in kwargs:
        cls = kwargs['cls']
        del kwargs['cls']
    else:
        cls = PersonWithFriends

    return cls(
        name=Name(given=x[0], family=x[1]),
        date_of_birth=x[2],
        phone_number=x[3],
        ssn="123-%.2d-%.4d" % (
            x[2].year % 100, x[2].toordinal() % 7919,
        ),
        **kwargs)


class TestDiffWithMultiFieldSelector(unittest.TestCase):

    def assertDifferences(self, iterator, expected):
        differences = set(str(x) for x in iterator)
        self.assertEqual(
            differences,
            set("<DiffInfo: %s>" % x for x in expected)
        )

    def test_diff(self):
        """Check that we still have our sanity..."""
        for x in range(0, len(PEOPLE)):
            person = get_person(x)
            same_person = get_person(x)
            self.assertDifferences(person.diff_iter(same_person), {})

    def test_filtered_diff(self):
        """Test that diff notices when fields are removed"""
        name_mfs = MultiFieldSelector(["name", "given"], ["name", "family"])
        person = get_person(1)
        filtered_person = name_mfs.get(person)
        self.assertDifferences(
            person.diff_iter(filtered_person),
            {"REMOVED .date_of_birth", "REMOVED .ssn",
             "REMOVED .phone_number"},
        )

    def test_filtered_coll_diff(self):
        name_and_friends_mfs = MultiFieldSelector(
            ["name"],
            ["friends", 0],
            ["friends", 2],
        )
        person = get_person(0, 2, 5, 6, 3)
        filtered_person = name_and_friends_mfs.get(person)

        self.assertDifferences(
            person.diff_iter(filtered_person),
            {"REMOVED .date_of_birth", "REMOVED .ssn",
             "REMOVED .phone_number",
             "REMOVED .friends[1]", "REMOVED .friends[3]"},
        )

    def test_filtered_coll_items_diff(self):
        strip_ids_mfs = MultiFieldSelector(
            ["name", "family"], ["date_of_birth"],
            ["friends", None, "name"],
            ["friends", None, "date_of_birth"],
        )
        person = get_person(0, 2, 5, 6, 3)
        filtered_person = strip_ids_mfs.get(person)

        # not terribly useful!
        self.assertDifferences(
            person.diff_iter(filtered_person), {
                "REMOVED .ssn", "REMOVED .phone_number",
                "REMOVED .name.given",
                "REMOVED .friends[0]", "ADDED .friends[0]",
                "REMOVED .friends[1]", "ADDED .friends[1]",
                "REMOVED .friends[2]", "ADDED .friends[2]",
                "REMOVED .friends[3]", "ADDED .friends[3]",
            },
        )

        # however, pass the filter into diff, and it gets it right!
        self.assertDifferences(
            person.diff_iter(filtered_person,
                             compare_filter=strip_ids_mfs), {},
        )

        filtered_person.friends.append(get_person(1))
        del filtered_person.friends[0]

        self.assertDifferences(
            person.diff_iter(filtered_person,
                             compare_filter=strip_ids_mfs),
            {"ADDED .friends[3]", "REMOVED .friends[0]"},
        )

    def test_ignore_empty_and_coll(self):
        person = get_person(6, 0, 3, 4, 5)
        strip_ids_mfs = MultiFieldSelector(
            ["name"], ["description"],
            ["friends", None, "name"],
            ["friends", None, "description"],
        )
        filtered_person = strip_ids_mfs.get(person)

        person.description = ""
        person.friends[0].description = ""

        self.assertDifferences(
            person.diff_iter(filtered_person,
                             compare_filter=strip_ids_mfs,
                             fuzzy_match=False),
            {
                "REMOVED .description",
                "REMOVED .friends[0]", "ADDED .friends[0]",
            },
        )

        self.assertDifferences(
            person.diff_iter(filtered_person,
                             compare_filter=strip_ids_mfs),
            {
                "REMOVED .description",
                "REMOVED .friends[0].description",
            },
        )

        self.assertDifferences(
            person.diff_iter(filtered_person,
                             compare_filter=strip_ids_mfs,
                             ignore_empty_slots=True), {},
        )

    def test_normalize_slot(self):
        person = get_person(3, 0, 2, 4, 6)
        strip_ids_mfs = MultiFieldSelector(
            ["name"], ["phone_number"],
            ["friends", None, "name"],
            ["friends", None, "phone_number"],
        )
        filtered_person = strip_ids_mfs.get(person)

        class MyDiffOptions(DiffOptions):
            def normalize_slot(self, val, prop):
                if "phone" in prop.name and isinstance(val, basestring):
                    val = normalize_phone(val)
                return super(MyDiffOptions, self).normalize_slot(val, prop)

        person.phone_number = '5309225668'
        person.friends[0].phone_number = '+1 239.978.5912'

        # old, non-fuzzy match:
        self.assertDifferences(
            person.diff_iter(filtered_person,
                             compare_filter=strip_ids_mfs,
                             ignore_empty_slots=True,
                             fuzzy_match=False),
            {
                "MODIFIED .phone_number",
                "REMOVED .friends[0]", "ADDED .friends[0]",
            },
        )

        # fuzzy match:
        self.assertDifferences(
            person.diff_iter(filtered_person,
                             compare_filter=strip_ids_mfs,
                             ignore_empty_slots=True),
            {
                "MODIFIED .phone_number",
                "MODIFIED .friends[0].phone_number"
            },
        )

        my_options = MyDiffOptions(
            ignore_empty_slots=True,
            compare_filter=strip_ids_mfs,
        )

        self.assertDifferences(
            person.diff_iter(filtered_person, options=my_options), {},
        )

        friendless = get_person(3)

        self.assertDifferences(
            person.diff_iter(friendless, options=my_options),
            {"REMOVED .friends"},
        )

        ignore_friends = MyDiffOptions(
            ignore_empty_slots=True,
            compare_filter=MultiFieldSelector(
                ["name"], ["phone_number"],
            )
        )

        self.assertDifferences(
            person.diff_iter(friendless, options=ignore_friends), {},
        )

    def test_compare_as_func(self):

        class PersonEasilyComparable(SurrogatePerson):
            primary_key = ['ssn']
            phone_number = StringProperty(compare_as=normalize_phone)

        base = get_person(4, cls=PersonEasilyComparable)
        other = get_person(4, cls=PersonEasilyComparable)
        other.phone_number = '+16146082940'

        self.assertDifferences(base.diff_iter(other), {})

    def test_compare_as_method_with_arg(self):

        class DangerousComparisons(SurrogatePerson):

            def add_area_code(self, number):
                number = normalize_phone(number)
                m = re.match(
                    r"(\d{3})\s*(?:[.-]\s*)?(\d{4})",
                    number,
                )
                if m:
                    return "(%.3d) %s-%s" % (
                        self.area_code, m.group(1), m.group(2),
                    )
                else:
                    return number

            area_code = IntProperty(check=lambda n: 0 < n < 1000)
            phone_number = StringProperty(compare_as=add_area_code)

        base = get_person(4, cls=DangerousComparisons)
        other = get_person(4, cls=DangerousComparisons)
        other.phone_number = '6082940'
        other.area_code = '614'

        self.assertDifferences(base.diff_iter(other), {"ADDED .area_code"})

    def test_compare_as_method(self):

        class CompareThisOrz(SurrogatePerson):

            def full_number(self):
                number = normalize_phone(self.phone_number)
                m = re.match(
                    r"(\d{3})\s*(?:[.-]\s*)?(\d{4})",
                    number,
                )
                if m:
                    return "(%.3d) %s-%s" % (
                        self.area_code, m.group(1), m.group(2),
                    )
                else:
                    return number

            area_code = IntProperty(check=lambda n: 0 < n < 1000)
            phone_number = StringProperty(compare_as=full_number)

        base = get_person(4, cls=CompareThisOrz)
        other = get_person(4, cls=CompareThisOrz)
        other.phone_number = '6082940'
        other.area_code = '614'

        self.assertDifferences(base.diff_iter(other), {"ADDED .area_code"})

    def test_filtered_collection_compare(self):

        class Foo(Record):
            bar = Property()

        class Foos(RecordList):
            itemtype = Foo

        self.assertDifferences(
            Foos().diff_iter(Foos(), compare_filter=MultiFieldSelector()),
            {},
        )

    def test_fuzzy_compare(self):

        person = get_person(3, 0, 2, 4, 6, 4, 1)
        person2 = get_person(3, 0, 1, 2, 3, 4, 5, 6)

        strip_ssn_mfs = MultiFieldSelector(
            ["name"], ["description"],
            ["phone_number"],
            ["friends", None, "name"],
            ["friends", None, "description"],
            ["friends", None, "phone_number"],
        )

        basic_differences = {
            "REMOVED .friends[4]",
            "ADDED .friends[5]",
            "ADDED .friends[3]",
        }
        self.assertDifferences(
            person.diff_iter(person2, compare_filter=strip_ssn_mfs),
            basic_differences,
        )

        person2.friends[0].name.given = "Jim"
        del person2.friends[1].phone_number
        person2.friends[2].name.family = "Woolf"
        person2.friends[6].name.family = "Haines"

        self.assertDifferences(
            person.diff_iter(person2, compare_filter=strip_ssn_mfs),
            basic_differences | {
                'MODIFIED .friends[0].name.given',
                'MODIFIED (.friends[3].name.family/.friends[6].name.family)',
                'REMOVED (.friends[5].phone_number/.friends[1].phone_number)',
                'MODIFIED (.friends[1].name.family/.friends[2].name.family)',
            }
        )

    def test_ignore_empty_items(self):
        person = get_person(3)
        person.friends = []
        person2 = get_person(3, 0, 4, 2, 6)

        no_populated_subfields_mfs = MultiFieldSelector(
            ["name"], ["description"],
            ["phone_number"],
            ["friends", None, "description"],
        )
        self.assertDifferences(
            person.diff_iter(
                person2,
                compare_filter=no_populated_subfields_mfs,
                ignore_empty_items=True,
            ),
            set(),
        )

        some_populated_subfields_mfs = MultiFieldSelector(
            ["name"], ["description"],
            ["phone_number"],
            ["friends", None, "name", "family"],
        )
        self.assertDifferences(
            person.diff_iter(
                person2,
                compare_filter=some_populated_subfields_mfs,
                ignore_empty_items=True,
            ),
            {
                "ADDED .friends[0]",
                "ADDED .friends[1]",
                "ADDED .friends[2]",
                "ADDED .friends[3]",
            }
        )
