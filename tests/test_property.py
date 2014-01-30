"""tests for the new, mixin-based property/descriptor system"""

from __future__ import absolute_import

import re
import unittest2

from normalize.record import Record
from normalize.property import LazyProperty
from normalize.property import Property
from normalize.property import ROProperty
from normalize.property import SafeProperty
from normalize.property.meta import MetaProperty


class TestProperties(unittest2.TestCase):
    """Test that the new data descriptor classes work"""
    def test_0_property(self):
        """Test that unbound Property objects can be created successfully"""
        prop = Property()
        self.assertIsNotNone(prop)
        self.assertIsInstance(prop, Property)
        self.assertIsInstance(type(prop), MetaProperty)
        self.assertRegexpMatches(str(prop), r".*unbound.*", re.I)

        roprop = Property(traits=['ro'])
        self.assertIsNotNone(roprop)
        self.assertIsInstance(roprop, ROProperty)
        self.assertIsInstance(type(prop), MetaProperty)

        name = ROProperty()
        self.assertIsNotNone(roprop)
        self.assertIsInstance(roprop, ROProperty)

    def test_1_basic(self):
        """Test that basic Properties can be defined and used"""
        class BasicRecord(Record):
            name = Property()
        self.assertRegexpMatches(
            str(BasicRecord.__dict__['name']),
            r".*Property.*BasicRecord\.name.*", re.I
        )

        br = BasicRecord()
        self.assertIsInstance(br, BasicRecord)
        self.assertRaises(AttributeError, lambda x: x.name, br)

        br = BasicRecord(name="Bromine")
        self.assertEqual(br.name, "Bromine")

    def test_2_ro(self):
        """Test Attributes which don't allow being set"""
        class TrivialRecord(Record):
            id = ROProperty()
            name = Property()
        self.assertRegexpMatches(
            str(TrivialRecord.__dict__['id']),
            r".*ROProperty.*TrivialRecord\.id.*", re.I
        )

        tr = TrivialRecord(id=123)
        self.assertEqual(tr.id, 123)
        with self.assertRaises(AttributeError):
            tr.id = 124

        tr.name = "Travel Guides"
        self.assertEqual(tr.name, "Travel Guides")

    def test_3_lazy(self):
        """Test Attributes which are build-once"""
        class TrapDoorRecord(Record):
            def _shoot(self):
                projectile = self.chamber
                self.chamber = "empty"
                return projectile
            chamber = Property()
            fired = LazyProperty(default=_shoot)

        tdr = TrapDoorRecord(chamber="bolt")
        self.assertNotIn(
            "fired", tdr.__dict__, "peek into lazy object's dict"
        )
        self.assertEqual(tdr.fired, "bolt")
        self.assertEqual(tdr.chamber, "empty")
        self.assertEqual(tdr.fired, "bolt")

    def test_4_required_check(self):
        """Test Attributes which are marked as required"""
        class FussyRecord(Record):
            id = Property(required=True)
            natural = SafeProperty(check=lambda i: i > 0)
            must = SafeProperty(required=True)

        with self.assertRaises(ValueError):
            fr = FussyRecord()

        fr = FussyRecord(id=123, must="sugary")
        with self.assertRaises(ValueError):
            del fr.must
        with self.assertRaises(ValueError):
            fr.must = None
        fr.must = "barmy"

        fr.natural = 7
        with self.assertRaises(ValueError):
            fr.natural = 0
