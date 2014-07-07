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

from __future__ import absolute_import

from datetime import datetime
import json
import unittest

from normalize.visitor import Visitor
from testclasses import wall_one, acent


JSON_CAN_DUMP = (basestring, int, long, dict, list)


class SimpleDumper(Visitor):
    def apply(self, value, *args):
        if isinstance(value, JSON_CAN_DUMP):
            dumpable = value
        elif isinstance(value, datetime):
            dumpable = value.isoformat()
        else:
            raise Exception("Can't dump %r" % value)
        return dumpable


class TestVisitor(unittest.TestCase):
    def test_simple_dumper(self):
        dumper = SimpleDumper()
        dumpable = dumper.map(wall_one)
        self.assertIsInstance(dumpable['posts'][0], dict)
        self.assertEqual(dumpable['posts'][0]['edited'], "2001-09-09T01:46:40")
        json.dumps(dumpable)

    def test_intro_example(self):
        self.assertEqual(
            SimpleDumper().map(acent),
            {'name': 'Alpha Centauri',
             'components': [{'hip_id': 71683, 'name': 'Alpha Centauri A'},
                            {'hip_id': 71681, 'name': 'Alpha Centauri B'},
                            {'hip_id': 70890, 'name': 'Alpha Centauri C'}]},
        )
