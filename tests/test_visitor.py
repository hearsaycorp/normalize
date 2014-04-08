from __future__ import absolute_import

from datetime import datetime
import json
import unittest

from normalize.visitor import Visitor
from testclasses import wall_one


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
        self.assertEqual(dumpable['posts'][0]['edited'], "2001-09-08T18:46:40")
        json.dumps(dumpable)
