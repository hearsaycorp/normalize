from __future__ import absolute_import

from datetime import datetime
import unittest

from normalize import FieldSelector
from normalize import FieldSelectorException
from normalize import JsonCollectionProperty
from normalize import JsonProperty
from normalize import JsonRecord
from normalize import Property
from normalize import Record
from normalize import Record
from normalize import RecordList
from normalize.property.coll import ListProperty
from normalize.selector import MultiFieldSelector


class MockChildRecord(JsonRecord):
    name = JsonProperty()


class MockDelegateJsonRecord(JsonRecord):
    other = JsonProperty()


class MockJsonRecord(JsonRecord):
    name = JsonProperty()
    age = JsonProperty(isa=int)
    seen = JsonProperty(
        json_name='last_seen', isa=datetime,
        coerce=lambda x: datetime.strptime(x, '%Y-%m-%dT%H:%M:%S'),
    )
    children = JsonCollectionProperty(of=MockChildRecord)


class MockExtraneousJsonRecord(JsonRecord):
    count = JsonProperty(isa=int)
    last_updated = JsonProperty(
        isa=datetime,
        coerce=lambda x: datetime.strptime(x, '%Y-%m-%dT%H:%M:%S'),
        extraneous=False,
    )


class MockRecordList(RecordList):
    itemtype = MockExtraneousJsonRecord


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
        # functional extension
        self.assertEqual(
            (fs1 + fs2).selectors, ["foo", "bar", "hello", "world"],
        )
        self.assertEqual(str(fs1 + "baz"), "<FieldSelector: .foo.bar.baz>")
        self.assertEqual(str(fs1 + ["baz"]), "<FieldSelector: .foo.bar.baz>")
        self.assertEqual(str(fs1 + 7), "<FieldSelector: .foo.bar[7]>")
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
            FieldSelectorException, "Could not find property specified "
            "by name: bad_name"
        ):
            fs.get(record)
        fs = FieldSelector(["children", 10])  # bad index
        with self.assertRaisesRegexp(
            FieldSelectorException, "Could not find Record specified by "
            "index: 10"
        ):
            fs.get(record)
        # bad nested property name
        fs = FieldSelector(["children", 1, "bad_name"])
        with self.assertRaisesRegexp(
            FieldSelectorException, "Could not find property specified "
            "by name: bad_name"
        ):
            fs.get(record)

        # bad property name
        fs = FieldSelector(["bad_name"])
        with self.assertRaises(AttributeError):
            fs.get(record)
        # bad index
        fs = FieldSelector(["children", 10])
        with self.assertRaises(KeyError):
            fs.get(record)
        # bad nested property name
        fs = FieldSelector(
            ["children", 1, "bad_name"],
        )
        with self.assertRaises(AttributeError):
            fs.get(record)

    def test_put(self):
        record = MockJsonRecord()

        # Test invalid FieldSelector
        fs = FieldSelector(["name"])
        fs.put(record, "pass")
        # self.assertEqual(record.raw_data, {"children": [], 'name': 'pass'})

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

        # Test addition to collection
        fs = FieldSelector(["children", 1, "name"])
        fs.post(record, "Susan")
        self.assertEqual(record.children[1].name, "Susan")

        # Test invalid addition to collection
        fs = FieldSelector(["children", 9999, "name"])
        with self.assertRaisesRegexp(
            ValueError, "FieldSelector set out of order"
        ):
            fs.post(record, "Joker")

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

    def test_subscripting(self):
        fs = FieldSelector(("somewhere", "over", "the", "rainbow"))
        self.assertEqual(len(fs), 4)
        self.assertEqual(fs[-1], "rainbow")
        shorter = fs[:-1]
        self.assertIsInstance(shorter, FieldSelector)
        self.assertEqual(len(shorter), 3)
        self.assertTrue(fs.startswith(shorter))

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

    def test_multi_selector(self):
        selectors = set(
            (
                ("bar", ),
                ("foo", "bar", 0, "boo"),
                ("foo", "bar", 0, "hiss"),
                ("foo", "bar", 1),
            )
        )

        mfs = MultiFieldSelector(*selectors)
        emitted = set(tuple(x.selectors) for x in mfs)
        self.assertEqual(emitted, selectors)

        # if you add a higher level selector, then more specific paths
        # disappear from the MFS
        mfs2 = MultiFieldSelector(mfs, ["foo", "bar"])
        emitted = set(tuple(x.selectors) for x in mfs2)
        self.assertEqual(emitted, set((("bar",), ("foo", "bar"))))

        data = {
            "bar": [1, 2, 3],
            "foo": {
                "bar": [
                    {"boo": "waa", "frop": "quux"},
                    {"waldo": "grault"},
                    {"fubar": "corge"},
                ],
            },
        }
        selected = mfs.get(data)
        self.assertEqual(
            selected, {
                "bar": [1, 2, 3],
                "foo": {
                    "bar": [
                        {"boo": "waa"},
                        {"waldo": "grault"},
                    ],
                },
            }
        )

        class Octothorpe(Record):
            name = Property()
            boo = Property()
            hiss = Property()

        class Caret(Record):
            bar = ListProperty(of=Octothorpe)

        class Pilcrow(Record):
            bar = ListProperty(of=Octothorpe)
            foo = Property(isa=Caret)
            baz = Property()

        full = Pilcrow(
            bar=[dict(name="Heffalump"), dict(name="Uncle Robert")],
            foo=dict(bar=[dict(name="Owl", hiss="Hunny Bee"),
                          dict(name="Piglet")]),
            baz="Wizzle",
        )
        filtered = mfs.get(full)
        expected = Pilcrow(
            bar=[dict(name="Heffalump"), dict(name="Uncle Robert")],
            foo=dict(bar=[dict(hiss="Hunny Bee"),
                          dict(name="Piglet")]),
        )
        self.assertEqual(filtered, expected)
