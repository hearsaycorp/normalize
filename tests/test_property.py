"""tests for the new, mixin-based property/descriptor system"""

from __future__ import absolute_import

import unittest2

from normalize.record import Record
from normalize.property import Property
from normalize.property import RWProperty
from normalize.property.meta import MetaProperty


class TestProperties(unittest2.TestCase):
    """Test that the new data descriptor classes work"""
    def test_0_property(self):
        """Test that unbound Property objects can be created successfully"""
        prop = Property()
        self.assertIsNotNone(prop)
        self.assertIsInstance(prop, Property)
        self.assertIsInstance(type(prop), MetaProperty)

        rwprop = Property(traits=['rw'])
        self.assertIsNotNone(rwprop)
        self.assertIsInstance(rwprop, RWProperty)
        self.assertIsInstance(type(prop), MetaProperty)

    def test_1_basic(self):
        """Test that basic Properties can be defined and used"""
        class BasicRecord(Record):
            name = Property()

        br = BasicRecord()
        self.assertIsInstance(br, BasicRecord)
        self.assertRaises(AttributeError, lambda x: x.name, br)

        br = BasicRecord(name="Bromine")
        self.assertEqual(br.name, "Bromine")

    def test_2_rw(self):
        """Test Attributes which allow being set"""
        class TrivialRecord(Record):
            id = Property()
            name = Property(traits=['rw'])

        tr = TrivialRecord(id=123)
        self.assertEqual(tr.id, 123)
        with self.assertRaises(AttributeError):
            tr.id = 124

        tr.name = "Travel Guides"
        self.assertEqual(tr.name, "Travel Guides")
