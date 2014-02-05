
from __future__ import absolute_import

import unittest

from normalize.record import Record
from normalize.property import Property


class BaseRecord(Record):
    id = Property(required=True, isa=int)
    name = Property(isa=basestring, coerce=str)


class KeyedRecord(BaseRecord):
    age = Property(isa=int)
    kids = Property(isa=int, extraneous=True)
    primary_key = ['id']


class TestRecordComparison(unittest.TestCase):
    def setUp(self):
        self.minimal = BaseRecord(id=7)
        self.foo1 = BaseRecord(id="2", name="foo")
        self.foo2 = BaseRecord(id="2", name="foo")

        self.bob1 = KeyedRecord(id=123, name="Bob", age=32)
        self.bill = KeyedRecord(id=123, name="Bill", age=34)
        self.bob2 = KeyedRecord(id=124, name="Bob", age=36)
        self.bob1a = KeyedRecord(id=123, name="Bob", age=32, kids=1)

    def test_stringify(self):
        """Test behavior of Record.__str__"""
        # this actually uses repr()
        self.assertEqual(str(self.foo1), str(self.foo2))

        # primary keys affect stringification
        self.assertEqual(str(self.bob1), str(self.bill))
        self.assertNotEqual(str(self.bob1), str(self.bob2))

        # stringification only defined (informally!) for PK-items
        self.assertEqual(str(self.bob1), "<KeyedRecord 123>")

    def test_repr(self):
        """Test behavior of Record.__repr__"""
        self.assertEqual(repr(self.foo1), "BaseRecord(id=2, name='foo')")
        self.assertEqual(repr(self.minimal), "BaseRecord(id=7)")

    def test_eq(self):
        """Test behavior of Record.__eq__ && .__ne__"""
        self.assertEqual(self.foo1, self.foo2)
        self.assertNotEqual(self.bob1, self.bill)
        self.assertNotEqual(self.bob1, self.bob2)
        self.assertEqual(self.bob1, self.bob1a)
        self.assertNotEqual(self.bob1, self.minimal)
