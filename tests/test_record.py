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

        self.assertEqual(sophie.aux_placeholder0, '')
        self.assertEqual(sophie.age0, 0)
        self.assertEqual(sophie.name0, None)
        self.assertEqual(sophie.placeholder0, None)

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
            epoch = Property(empty=lambda: datetime(1970, 1, 1, 0, 0, 0))
            objective = Property(empty=BlahRecord)

        lambda_ = LambdaRecord()

        self.assertTrue(
            lambda_.epoch0.isoformat().startswith("1970-01-01T00:00:00"),
            "lambda empty values are called",
        )
        lambda_.objective0.blah = 123
        self.assertIsNone(lambda_.objective0.blah0,
                          "empty values don't persist")

    def test_bad_constructor(self):
        """Test the 'empty' definition errors happen early"""
        with warnings.catch_warnings(record=True) as w:
            class OhNoRecord(Record):
                lets_go = Property(isa=datetime)

            self.assertEqual(len(w), 1)
            this_file = os.path.basename(__file__)
            bad_file = os.path.basename(w[0].filename)
            self.assertEqual(
                os.path.splitext(this_file)[0],
                os.path.splitext(bad_file)[0],
            )
