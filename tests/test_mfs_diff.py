from __future__ import absolute_import

from datetime import date
import re
import unittest2

from normalize import FieldSelector
from normalize import FieldSelectorException
from normalize import JsonCollectionProperty
from normalize import JsonProperty
from normalize import JsonRecord
from normalize import JsonRecordList
from normalize import Property
from normalize import Record
from normalize import Record
from normalize import RecordList
from normalize.property.coll import ListProperty
from normalize.property.types import DateProperty
from normalize.property.types import UnicodeProperty
from normalize.selector import MultiFieldSelector


class SurrogatePerson(Record):
    given_name = UnicodeProperty()
    family_name = UnicodeProperty()
    ssn = Property(isa=str, check=lambda x: re.match(r'\d{3}-\d{2}-\d{4}', x))
    date_of_birth = DateProperty()
    primary_key = [ssn]


class PersonWithFriends(SurrogatePerson):
    friends = ListProperty(of=SurrogatePerson)


PEOPLE = (
    ("James", "Miller", date(1960, 11, 18)),
    ("Aaron", "Mora", date(1963, 2, 20)),
    ("Laura", "Wolf", date(1966, 8, 13)),
    ("Steve", "Chen", date(1967, 6, 11)),
    ("Stephanie", "Hart", date(1971, 8, 3)),
    ("Kara", "Park", date(1972, 11, 22)),
    ("Ruben", "Haynes", date(1975, 4, 8)),
)


def get_person(i, *friends):
    x = PEOPLE[i]
    kwargs = {}
    if friends:
        kwargs["friends"] = list(get_person(x) for x in friends)

    return PersonWithFriends(
        given_name=x[0],
        family_name=x[1],
        date_of_birth=x[2],
        ssn="123-%.2d-%.4d" % (
            x[2].year % 100, x[2].toordinal() % 7919,
        ),
        **kwargs)


class TestDiffWithMultiFieldSelector(unittest2.TestCase):

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
        name_mfs = MultiFieldSelector(["given_name"], ["family_name"])
        person = get_person(1)
        filtered_person = name_mfs.get(person)
        self.assertDifferences(
            person.diff_iter(filtered_person),
            {"REMOVED .date_of_birth", "REMOVED .ssn"},
        )

    def test_filtered_coll_diff(self):
        name_and_friends_mfs = MultiFieldSelector(
            ["given_name"], ["family_name"],
            ["friends", 0],
            ["friends", 2],
        )
        person = get_person(0, 2, 5, 6, 3)
        filtered_person = name_and_friends_mfs.get(person)

        self.assertDifferences(
            person.diff_iter(filtered_person),
            {"REMOVED .date_of_birth", "REMOVED .ssn",
             "REMOVED .friends[1]", "REMOVED .friends[3]"},
        )

    def test_filtered_coll_items_diff(self):
        strip_ids_mfs = MultiFieldSelector(
            ["given_name"], ["family_name"], ["date_of_birth"],
            ["friends", None, "given_name"],
            ["friends", None, "family_name"],
            ["friends", None, "date_of_birth"],
        )
        person = get_person(0, 2, 5, 6, 3)
        filtered_person = strip_ids_mfs.get(person)

        # not terribly useful!
        self.assertDifferences(
            person.diff_iter(filtered_person), {
                "REMOVED .ssn",
                "REMOVED .friends[0]", "ADDED .friends[0]",
                "REMOVED .friends[1]", "ADDED .friends[1]",
                "REMOVED .friends[2]", "ADDED .friends[2]",
                "REMOVED .friends[3]", "ADDED .friends[3]",
            },
        )
