
import re
import sys
import unittest2

from normalize.record import Record
from normalize.property import LazyProperty
from normalize.property import LazySafeProperty
from normalize.property import Property
from normalize.property import ROLazyProperty
from normalize.property import ROProperty
from normalize.property import SafeProperty
from normalize.property.types import *


class TestTypeLibrary(unittest2.TestCase):
    def test_property_types(self):
        seqval = [0]

        def _seq():
            rv = seqval[0]
            seqval[0] += 1
            return rv

        class DemoType(Record):
            id = IntProperty(required=True)
            name = StringProperty()
            seq = IntProperty(lazy=True, default=_seq)
            fullname = ROLazyUnicodeProperty(default=lambda x: x.name)

        self.assertIsInstance(DemoType.properties['id'], SafeProperty)

        demo = DemoType(id="345")
        self.assertEqual(demo.id, 345)
        self.assertEqual(demo.seq, 0)
        demo.name = "Foo Bar"
        self.assertEqual(demo.fullname, "Foo Bar")
        self.assertIsInstance(demo.fullname, unicode)


class TestSubTypes(unittest2.TestCase):
    """Proof of concept test for coercing between sub-types of real types.
    """
    def test_sub_types(self):
        class NaturalNumberMeta(type):
            @classmethod
            def __instancecheck__(cls, val):
                return isinstance(val, (int, long)) and val > 0

        class NaturalNumber(int):
            __metaclass__ = NaturalNumberMeta

        self.assertIsInstance(50, NaturalNumber)
        self.assertFalse(isinstance(-50, NaturalNumber))

        class BigNaturalNumber(long):
            __metaclass__ = NaturalNumberMeta

        class NaturalBornObject(Record):
            count = Property(
                isa=(NaturalNumber, BigNaturalNumber),
                coerce=lambda x: (
                    abs(int(x)) if abs(long(x)) < sys.maxint else
                    abs(long(x))
                ),
                check=lambda N: N > 0,
            )

        nbo = NaturalBornObject()
        # regular coercions: type mismatches
        nbo.count = "256"
        self.assertEqual(nbo.count, 256)
        nbo.count = 1.832e19
        self.assertEqual(nbo.count, 18320000000000000000L)
        # type matches, but subtype doesn't
        nbo.count = -10
        self.assertEqual(nbo.count, 10)
        with self.assertRaises(ValueError):
            nbo.count = 0.5
