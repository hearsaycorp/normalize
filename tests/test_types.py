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


from datetime import date
from datetime import datetime
import re
import sys
import unittest2

import normalize.exc as exc
from normalize.record import Record
from normalize.property import LazyProperty
from normalize.property import LazySafeProperty
from normalize.property import Property
from normalize.property import ROLazyProperty
from normalize.property import ROProperty
from normalize.property import SafeProperty
from normalize.property.types import *
from normalize.subtype import subtype


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
            fullname = UnicodeProperty(
                default=lambda self: self.name,
                lazy=True,
            )

        self.assertIsInstance(DemoType.properties['id'], SafeProperty)
        self.assertEqual(DemoType.properties['id'].valuetype, int)

        demo = DemoType(id="345")
        self.assertEqual(demo.id, 345)
        self.assertEqual(demo.seq, 0)
        demo.name = "Foo Bar"
        self.assertEqual(demo.fullname, "Foo Bar")
        self.assertIsInstance(demo.fullname, unicode)

    def test_dates_and_integer_types(self):
        class Props(Record):
            isadate = DateProperty()
            isadatetime = DatetimeProperty()
            integer = IntegerProperty()

        p = Props(isadate="20121212")
        self.assertEqual(p.isadate, date(2012, 12, 12))
        p.isadatetime = "2012-12-12"
        self.assertEqual(p.isadatetime, datetime(2012, 12, 12, 0, 0))
        self.assertEqual(p.isadatetime.isoformat(), '2012-12-12T00:00:00')

        p.isadatetime = "2014-04-02T12:34"
        self.assertEqual(p.isadatetime.isoformat(), '2014-04-02T12:34:00')
        p.isadatetime = "2014-04-02T12:34:12"
        self.assertEqual(p.isadatetime, datetime(2014, 4, 2, 12, 34, 12))
        today = date.today()
        p.isadatetime = today
        self.assertIsInstance(p.isadatetime, datetime)
        p.isadate = p.isadatetime
        self.assertIsInstance(p.isadate, date)

        p.integer = 123
        p.integer = "123125"
        with self.assertRaises(ValueError):
            p.integer = "foo"
        p.integer = 1e20
        self.assertEqual(p.integer, 100000000000000000000L)


class TestSubTypes(unittest2.TestCase):
    """Proof of concept test for coercing between sub-types of real types.
    """
    def test_sub_types(self):
        NaturalNumber = subtype(
            of=int,
            name="NaturalNumber",
            where=lambda i: i > 0,
        )
        self.assertIsInstance(NaturalNumber, type)
        self.assertTrue(issubclass(NaturalNumber, int))
        self.assertIsInstance(50, NaturalNumber)
        self.assertFalse(isinstance(-50, NaturalNumber))
        self.assertEqual(str(NaturalNumber), "<subtype NaturalNumber of int>")

        BigNaturalNumber = subtype(
            of=long,
            name="BigNaturalNumber",
            where=lambda i: i > 0,
        )

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

    def test_subtype_coerce(self):
        NaturalNumber = subtype(
            of=int,
            name="NaturalNumber",
            where=lambda i: i > 0,
        )

        self.assertEqual(NaturalNumber(3), 3)
        with self.assertRaises(exc.CoercionError):
            NaturalNumber(-3)

        ScalarNaturalNumber = subtype(
            of=int,
            name="ScalarNaturalNumber",
            where=lambda i: i > 0,
            coerce=lambda i: abs(i),
        )

        self.assertEqual(ScalarNaturalNumber(3), 3)
        self.assertEqual(ScalarNaturalNumber(-3), 3)
        self.assertRaises(ValueError, ScalarNaturalNumber, 0)

    def test_subtype_subtype(self):
        NaturalNumber = subtype(
            of=int,
            name="NaturalNumber",
            where=lambda i: i > 0,
        )

        SmallNaturalNumber = subtype(
            of=NaturalNumber,
            name="SmallNaturalNumber",
            where=lambda i: i <= 100,
        )

        self.assertTrue(issubclass(SmallNaturalNumber, NaturalNumber))
        self.assertTrue(issubclass(SmallNaturalNumber, int))

        self.assertTrue(isinstance(10, SmallNaturalNumber))
        self.assertFalse(isinstance(101, SmallNaturalNumber))
        self.assertFalse(isinstance(0, SmallNaturalNumber))

    def test_subtype_abstract(self):
        import abc

        class AbstractClass(object):
            __metaclass__ = abc.ABCMeta

            @abc.abstractmethod
            def define_me(self):
                pass

        SubAbstractClass = subtype(
            of=AbstractClass,
            name="SubAbstractClass",
            where=lambda v: v.define_me() > 0
        )
        self.assertEqual(
            str(SubAbstractClass),
            "<ABCMetaSubtype SubAbstractClass of AbstractClass>",
        )

        class ConcreteClass(AbstractClass):
            def __init__(self, what):
                self.what = what

            def define_me(self):
                return self.what

        self.assertIsInstance(ConcreteClass(1), SubAbstractClass)
        self.assertNotIsInstance(ConcreteClass(-1), SubAbstractClass)

    def test_squash_coerce(self):

        # tests that coerce to None on initialization works
        MaybeNaturalNumber = subtype(
            "MaybeNaturalNumber", int, where=lambda i: i > 0,
            coerce=lambda i: abs(int(i)) or None,
        )

        class Squasher(Record):
            number_or_none = Property(isa=MaybeNaturalNumber)

        s = Squasher(number_or_none=0)
        with self.assertRaises(AttributeError):
            s.number_or_none
