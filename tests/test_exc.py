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

from builtins import str
import inspect
import sys
import unittest2

import normalize.exc as exc


class TestExceptionSystem(unittest2.TestCase):
    def test_base_class(self):
        foo = exc.StringFormatException()
        self.assertEqual(str(foo), "(uncustomized exception!)")
        self.assertEqual(repr(foo), "exc.StringFormatException()")

    def test_exception_class(self):
        class TestException(exc.StringFormatException):
            message = "{keywords} and positionals: {0}"

        te = TestException("foo", keywords="ok")
        self.assertEqual(str(te), "ok and positionals: foo")
        self.assertEqual(
            repr(te), "TestException('foo', keywords='ok')"
        )
        self.assertEqual(te.keywords, "ok")
        with self.assertRaises(AttributeError):
            te.foo
        self.assertEqual(te[0], "foo")
        with self.assertRaises(IndexError):
            te[1]

        self.assertRaises(
            exc.KeywordExceptionFormatError, TestException, "foo",
        )
        self.assertRaises(
            exc.PositionalExceptionFormatError, TestException,
            keywords="ok",
        )

    def test_all_exceptions_inherit_from_base(self):
        """
        Verify that all exceptions really do subclass NormalizeError so that no end user breaks.
        """
        # https://stackoverflow.com/questions/1796180/how-can-i-get-a-list-of-all-classes-within-current-module-in-python
        for _, obj in inspect.getmembers(sys.modules['normalize.exc'], inspect.isclass):
            if issubclass(obj, Exception):
                self.assertTrue(issubclass(obj, exc.NormalizeError))
