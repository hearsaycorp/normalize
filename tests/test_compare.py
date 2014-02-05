
from __future__ import absolute_import

import unittest

from normalize.record import Record
from normalize.property import Property


class BaseRecord(Record):
    id = Property(required=True, isa=int)
    name = Property(isa=basestring, coerce=str)


class KeyedRecord(BaseRecord):
    age = Property(isa=int)
    primary_key = ['id']


class TestRecordComparison(unittest.TestCase):
    def setUp(self):
        self.foo1 = BaseRecord(id="2", name="foo")
        self.foo2 = BaseRecord(id="2", name="foo")

        self.bob1 = KeyedRecord(id=123, name="Bob", age=32)
        self.bill = KeyedRecord(id=123, name="Bill", age=34)
        self.bob2 = KeyedRecord(id=124, name="Bob", age=36)

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
        br_partial = BaseRecord(id=7)
        self.assertEqual(repr(br_partial), "BaseRecord(id=7)")
