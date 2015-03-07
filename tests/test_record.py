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

"""tests that look at the wholistic behavior of records"""

from __future__ import absolute_import

from datetime import datetime
import os.path
import unittest2
import warnings

from normalize import ListProperty
from normalize import Property
from normalize import Record
import normalize.exc as exc
from normalize.visitor import VisitorPattern


class TestRecords(unittest2.TestCase):
    """Test that the new data descriptor classes work"""

    def test_false_emptiness(self):
        """Test that Properties with falsy empty values don't throw exceptions"""

        class SophiesRecord(Record):
            placeholder = Property()
            aux_placeholder = Property(empty='')
            age = Property(empty=0)
            name = Property(empty=None)

        sophie = SophiesRecord()
        with self.assertRaises(AttributeError):
            sophie.placeholder
        with self.assertRaises(AttributeError):
            sophie.aux_placeholder

        self.assertFalse(sophie.aux_placeholder0)
        self.assertFalse(sophie.age0)
        self.assertFalse(sophie.name0)
        self.assertFalse(sophie.placeholder0)

        # the properties aren't really set...
        self.assertEqual(VisitorPattern.visit(sophie), {})

        sophie.age = 1
        self.assertEqual(VisitorPattern.visit(sophie), {"age": 1})

        sophie.age = 0
        self.assertEqual(VisitorPattern.visit(sophie), {"age": 0})

        del sophie.age
        self.assertEqual(VisitorPattern.visit(sophie), {})

    def test_functional_emptiness(self):
        """Test that functional empty values are transient"""

        class BlahRecord(Record):
            blah = Property()

        class LambdaRecord(Record):
            epoch = Property(isa=datetime)
            objective = Property(isa=BlahRecord)

        lambda_ = LambdaRecord()

        self.assertFalse(
            lambda_.epoch0.isoformat()[:4].bob.foo,
            "empty values work",
        )
        self.assertFalse(lambda_.objective0.blah0,
                         "empty values don't persist")

        with self.assertRaisesRegexp(AttributeError, r'BlahRecord.*blha0'):
            ph = lambda_.objective0.blha0

        with self.assertRaisesRegexp(
            exc.EmptyAttributeError, r"Can't assign.*BlahRecord"
        ):
            ph = lambda_.objective0.blah = 42

        with self.assertRaisesRegexp(
            exc.EmptyAttributeError, r"Can't assign.*BlahRecord"
        ):
            ph = lambda_.objective0[0] = 42

    def test_bad_constructor(self):
        """Test that 'empty' definition errors are no longer possible"""
        with warnings.catch_warnings(record=True) as w:
            class OhNoRecord(Record):
                lets_go = Property(isa=datetime)

            self.assertEqual(len(w), 0)

    def test_empty_type_inference(self):

        class OneRecord(Record):
            foo = Property()

        class TwoRecord(Record):
            bar = Property()

            def __call__(self):
                return "hi"

        class NumRecord(Record):
            which = Property(isa=(OneRecord, TwoRecord))

        class NumsRecord(Record):
            nums = ListProperty(of=NumRecord)

        nr = NumsRecord()

        with self.assertRaisesRegexp(
            exc.EmptyAttributeError, r"NumRecordList.*attribute 'which'",
        ):
            nr.nums0.which
        self.assertFalse(nr.nums0[1].which)

        with self.assertRaisesRegexp(
            exc.EmptyAttributeError, r"NumRecord\b.*attribute 'blah'",
        ):
            nr.nums0[0].blah

        self.assertFalse(nr.nums0[2].which.foo)
        self.assertFalse(nr.nums0[2].which.bar)

        # 0 forms also work as well
        self.assertFalse(nr.nums0[3].which0.bar0)
        self.assertFalse(nr.nums0[4].which0.foo0)

        # array slicing
        self.assertFalse(nr.nums0[3:-1][0].which0.foo0)

        with self.assertRaisesRegexp(
            exc.NotSubscriptable, r"OneRecord,TwoRecord"
        ):
            nr.nums0[1].which[1]

        # test invoking
        with self.assertRaisesRegexp(exc.NotCallable, r"NumRecord"):
            nr.nums0[1]()

        self.assertFalse(nr.nums0[4].which())

        class MagicRecord(Record):
            def __getattr__(self, whatever):
                return 1

        class MagicList(Record):
            def __getitem__(self, whatever):
                return 1

        class LooseRecord(Record):
            this = Property(isa=(OneRecord, TwoRecord, datetime))
            that = Property(isa=MagicRecord)
            other = Property(isa=MagicList)

        lr = LooseRecord()
        self.assertFalse(lr.this0.date)
        with self.assertRaisesRegexp(exc.NoSuchAttribute, r"TwoRecord,datetime"):
            lr.this0.dote

        self.assertFalse(lr.that0.date)
        with self.assertRaisesRegexp(exc.NotSubscriptable, r"MagicRecord"):
            lr.that0[7]

        self.assertFalse(lr.other0[0].foo.bar())
        with self.assertRaisesRegexp(exc.NoSuchAttribute, r"MagicList"):
            lr.other0.anything
