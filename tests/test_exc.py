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
