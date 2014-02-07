from __future__ import absolute_import

import unittest

from normalize import FieldSelector, FieldSelectorException
from testclasses import MockChildRecord, MockJsonRecord


class MockComplexJsonRecord(MockJsonRecord):
    nested = MockJsonRecord()


class TestStructableFieldSelector(unittest.TestCase):

    def test_init(self):
        # create valid FieldSelectors
        FieldSelector()
        FieldSelector([None])
        fs = FieldSelector(["foo", "bar"])
        self.assertEqual(str(fs), "<FieldSelector: .foo.bar>")
        self.assertEqual(repr(fs), "FieldSelector(['foo', 'bar'])")
        FieldSelector(("foo", "bar"))
        fs = FieldSelector("foobar")
        self.assertEqual(str(fs), "<FieldSelector: .f.o.o.b.a.r>")
        fs = FieldSelector({"foo": "bar"})
        self.assertEqual(str(fs), "<FieldSelector: .foo>")
        FieldSelector(FieldSelector(["foo", "bar"]))
        fs = FieldSelector(["foo", 7, "bar"])
        self.assertEqual(str(fs), "<FieldSelector: .foo[7].bar>")
        self.assertEqual(repr(fs), "FieldSelector(['foo', 7, 'bar'])")

        # Test invalid FieldSelectors
        with self.assertRaisesRegexp(
            ValueError, "FieldSelectors can only contain ints/longs, "
            "strings, and None"
        ):
            FieldSelector({"foo": "bar"}.iteritems())
        with self.assertRaisesRegexp(
            ValueError, "FieldSelectors can only contain ints/longs, "
            "strings, and None"
        ):
            FieldSelector(["foo", "bar", 1.0])

    def test_add_property(self):
        fs = FieldSelector(["foo", "bar"])
        self.assertEqual(fs.selectors, ["foo", "bar"])

        fs.add_property("prop_name")
        self.assertEqual(fs.selectors, ["foo", "bar", "prop_name"])

        with self.assertRaisesRegexp(
            ValueError, "properties must be specified by their string name",
        ):
            fs.add_property({})

        self.assertEqual(fs.selectors, ["foo", "bar", "prop_name"])

    def test_add_index(self):
        fs = FieldSelector(["foo", "bar"])
        self.assertEqual(fs.selectors, ["foo", "bar"])

        fs.add_index(0)
        self.assertEqual(fs.selectors, ["foo", "bar", 0])

        with self.assertRaisesRegexp(
            ValueError, "index must be an int or a long"
        ):
            fs.add_index(0.0)

        self.assertEqual(fs.selectors, ["foo", "bar", 0])

    def test_add_full_collection(self):
        fs = FieldSelector(["foo", "bar"])
        self.assertEqual(fs.selectors, ["foo", "bar"])

        fs.add_full_collection()
        self.assertEqual(fs.selectors, ["foo", "bar", None])
        self.assertEqual(str(fs), "<FieldSelector: .foo.bar[*]>")

    def test_extend(self):
        fs1 = FieldSelector(["foo", "bar"])
        fs2 = FieldSelector(["hello", "world"])
        fs3 = fs1.extend(fs2)

        # Verify that extend works
        self.assertEqual(fs1.selectors, ["foo", "bar", "hello", "world"])
        # Verify that extend chaining works
        self.assertEqual(fs1, fs3)

    def test_get(self):
        record = MockJsonRecord(
            {
                "age": 5,
                "children": [{"name": "foo"}, {"name": "bar"}],
                "name": "case1",
            }
        )
        # test valid field selectors
        fs = FieldSelector(["name"])
        self.assertEqual(fs.get(record), "case1")
        fs = FieldSelector(["age"])
        self.assertEqual(fs.get(record), 5)
        fs = FieldSelector(["children"])
        self.assertEqual(len(fs.get(record)), 2)
        fs = FieldSelector(["children", 1])
        self.assertEqual(fs.get(record).name, "bar")
        self.assertEqual(fs.get(record), MockChildRecord({"name": "bar"}))
        fs = FieldSelector(["children", 1, "name"])
        self.assertEqual(fs.get(record), "bar")
        fs = FieldSelector(["children", None, "name"])
        self.assertEqual(fs.get(record), ["foo", "bar"])

        # test invalid selectors
        fs = FieldSelector(["bad_name"])  # bad property name
        with self.assertRaisesRegexp(
            FieldSelectorException, "Could not find Record specified by "
            "property name: bad_name."
        ):
            fs.get(record)
        fs = FieldSelector(["children", 10])  # bad index
        with self.assertRaisesRegexp(
            FieldSelectorException, "Could not find Record specified by "
            "index: 10."
        ):
            fs.get(record)
        # bad nested property name
        fs = FieldSelector(["children", 1, "bad_name"])
        with self.assertRaisesRegexp(
            FieldSelectorException, "Could not find Record specified by "
            "property name: bad_name."
        ):
            fs.get(record)

        # bad property name
        fs = FieldSelector(["bad_name"])
        #with self.assertRaises(KeyError):
        with self.assertRaises(FieldSelectorException):
            fs.get(record)
        # bad index
        fs = FieldSelector(["children", 10])
        #with self.assertRaises(IndexError):
        with self.assertRaises(FieldSelectorException):
            fs.get(record)
        # bad nested property name
        fs = FieldSelector(
            ["children", 1, "bad_name"],
        )
        #with self.assertRaises(KeyError):
        with self.assertRaises(FieldSelectorException):
            fs.get(record)

    def test_put(self):
        record = MockJsonRecord()

        # Test invalid FieldSelector
        fs = FieldSelector(["name"])
        fs.put(record, "pass")
        #self.assertEqual(record.raw_data, {"children": [], 'name': 'pass'})

        record = MockComplexJsonRecord()

        # Test creation of attribute
        fs = FieldSelector(["name"])
        fs.put(record, "Bobby")
        self.assertEqual(record.name, "Bobby")

        # Test creation of collection and sub-Record
        fs = FieldSelector(["children", 0, "name"])
        with self.assertRaises(FieldSelectorException):
            fs.put(record, "Johnny")

    def test_post(self):
        record = MockComplexJsonRecord()
        fs = FieldSelector(["name"])
        fs.post(record, "Bobby")
        self.assertEqual(record.name, "Bobby")

        fs = FieldSelector(["children", 0, "name"])
        fs.post(record, "Johnny")
        self.assertEqual(record.children[0].name, "Johnny")

        # Test create of sub-Record
        fs = FieldSelector(["nested", "name"])
        fs.put(record, "Nested")
        self.assertEqual(record.nested.name, "Nested")

    def test_eq(self):
        fs1 = FieldSelector(["foo", "bar"])
        fs2 = FieldSelector(["foo", "bar"])
        self.assertEqual(fs1, fs2)

        fs1 = FieldSelector(["foo", "bar"])
        fs2 = FieldSelector(fs1)
        self.assertEqual(fs1, fs2)

    def test_lt(self):
        fs1 = FieldSelector(["foo", "bar"])
        fs2 = FieldSelector(["foo", "bar"])
        self.assertFalse(fs1 < fs2)

        fs1 = FieldSelector(["bar"])
        fs2 = FieldSelector(["foo"])
        self.assertLess(fs1, fs2)

        fs1 = FieldSelector(["foo", "bar", 0])
        fs2 = FieldSelector(["foo", "bar", 1])
        self.assertLess(fs1, fs2)

        fs1 = FieldSelector(["foo", "bar", 0, "boo"])
        fs2 = FieldSelector(["foo", "bar", 0, "hiss"])
        self.assertLess(fs1, fs2)

        fs1 = FieldSelector(["foo", 0])
        fs2 = FieldSelector(["foo", "bar"])
        with self.assertRaisesRegexp(
            TypeError, "Cannot compare incompatible FieldSelectors. "
            "Incompatibility detected at index: 1 for selectors: .* and .*"
        ):
            fs1 < fs2

    def test_sort(self):
        fs1 = FieldSelector(["bar"])
        fs2 = FieldSelector(["foo"])
        fs3 = FieldSelector(["foo", "bar"])
        fs4 = FieldSelector(["foo", "bar", 0])
        fs5 = FieldSelector(["foo", "bar", 0, "boo"])
        fs6 = FieldSelector(["foo", "bar", 0, "hiss"])
        fs7 = FieldSelector(["foo", "bar", 1])

        field_selectors = [fs7, fs6, fs2, fs4, fs3, fs5, fs1]
        field_selectors_sorted = sorted(field_selectors)
        self.assertEqual(field_selectors_sorted,
                         [fs1, fs2, fs3, fs4, fs5, fs6, fs7])
