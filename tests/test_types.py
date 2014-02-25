
import re
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
