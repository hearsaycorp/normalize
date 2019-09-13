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

from builtins import str, zip
from datetime import datetime
import six
import re
import unittest

from normalize import FieldSelector
from normalize import FieldSelectorException
from normalize import JsonCollectionProperty
from normalize import JsonProperty
from normalize import JsonRecord
from normalize import JsonRecordList
from normalize import Property
from normalize import Record
from normalize import RecordList
from normalize.coll import list_of
from normalize.property.coll import DictProperty
from normalize.property.coll import ListProperty
from normalize.selector import MultiFieldSelector

from .testclasses import Person, wall_one


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
            FieldSelector(iter({"foo": "bar"}.items()))
        with self.assertRaisesRegexp(
            ValueError, "FieldSelectors can only contain ints/longs, "
            "strings, and None"
        ):
            FieldSelector(["foo", "bar", 1.0])

    def test_path_marshal(self):
        for path in (
            ("foo", "bar"),
            (None, ),
            (None, "bob", 6, "frop"),
            ("window", "setTimeout", "100"),
            ("wind0w", "setT1meout", "_100"),
            (),
            ("Bob", "one flew over the cuckoo's nest"),
            ("Leaning", "toothpick", "syndrome", "\\/\"/"),
            (u"\u2620",)
        ):
            fs = FieldSelector(path)
            fs_path = fs.path
            fs_2 = FieldSelector.from_path(fs_path)
            self.assertEqual(fs.path, fs_2.path)
            self.assertEqual(fs.selectors, fs_2.selectors)

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
        self.assertIsNone(fs.get_or_none(record))
        fs = FieldSelector(["children", 10])  # bad index
        with self.assertRaisesRegexp(
            FieldSelectorException, "Could not find Record specified by "
            "index: 10"
        ):
            fs.get(record)
        self.assertIsNone(fs.get_or_none(record))
        # bad nested property name
        fs = FieldSelector(["children", 1, "bad_name"])
        with self.assertRaisesRegexp(
            FieldSelectorException, "Could not find property specified "
            "by name: bad_name"
        ):
            fs.get(record)
        self.assertIsNone(fs.get_or_none(record))

        # bad property name
        fs = FieldSelector(["bad_name"])
        with self.assertRaises(AttributeError):
            fs.get(record)
        self.assertIsNone(fs.get_or_none(record))
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
        self.assertIsNone(fs.get_or_none(record))

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

    def test_post_required(self):
        class FussyRecord(Record):
            id = Property(required=True)

        class FussPot(Record):
            fuss_list = ListProperty(of=FussyRecord)
            fuss_map = DictProperty(of=FussyRecord)
            top_fuss = Property(isa=FussyRecord)

        fp = FussPot()
        fs1 = FieldSelector(("top_fuss", "id"))
        fs2 = FieldSelector(("fuss_map", "phew", "id"))
        fs3 = FieldSelector(("fuss_list", 0, "id"))
        fs1.post(fp, 1)
        fs2.post(fp, 2)
        fs3.post(fp, 3)
        fp2 = FussPot(
            top_fuss={"id": 1},
            fuss_map={"phew": {"id": 2}},
            fuss_list=[{"id": 3}],
        )
        self.assertEqual(fp, fp2)

    def test_delete(self):

        class MyObj(Record):
            foo = Property()
            bar = Property()

        class OtherObj(Record):
            objs = ListProperty(of=MyObj)

        mo = MyObj(foo="bar")
        fs1 = FieldSelector(["foo"])
        self.assertEqual(fs1.get(mo), "bar")
        fs1.delete(mo)
        self.assertRaises(AttributeError, fs1.get, mo)

        oo = OtherObj(objs=[{"foo": "bar"}, {"foo": "frop"}])

        fs2 = FieldSelector(["objs", 0, "foo"])
        self.assertEqual(fs2.get(oo), "bar")
        fs2.delete(oo)
        self.assertRaises(AttributeError, fs2.get, mo)
        fs2.put(oo, "hey")

        fs3 = FieldSelector(["objs", None, "foo"])
        self.assertEqual(fs3.get(oo), ["hey", "frop"])
        fs3.delete(oo)
        self.assertEqual(oo, OtherObj(objs=[{}, {}]))

        oo = OtherObj(objs=[{"foo": "baz"}, {"bar": "quux"}])
        self.assertEqual(fs3.get(oo), ["baz", None])
        fs3.delete(oo)
        self.assertEqual(oo, OtherObj(objs=[{}, {"bar": "quux"}]))

        fs4 = FieldSelector(["objs", None, "bar", "foo"])
        self.assertRaises(FieldSelectorException, fs4.get, oo)

        oo = OtherObj(objs=[{"foo": "baz"}, {"bar": MyObj(foo="bob")}])
        self.assertEqual(fs4.get(oo), [None, "bob"])
        fs4.delete(oo)
        self.assertRaises(FieldSelectorException, fs4.get, oo)

        fs5 = FieldSelector(["objs", 1])
        fs5.delete(oo)
        self.assertEqual(oo, OtherObj(objs=[{"foo": "baz"}]))

        fs6 = FieldSelector(["objs", None])
        fs6.delete(oo)
        self.assertEqual(oo, OtherObj(objs=[]))

    def test_dict(self):
        from normalize.coll import dict_of
        Rolodeck = dict_of(Person)

        deck = Rolodeck({
            "bob": Person(id=123, name="Bob"),
            "peter": Person(id=124, name="Peter"),
            "eve": Person(id=125, name="Steve"),
        })

        fs1 = FieldSelector(["bob", "id"])
        self.assertEqual(fs1.get(deck), 123)
        self.assertRaisesRegexp(
            ValueError, r'id is required', fs1.delete, deck,
        )

        fs2 = FieldSelector(["cuthbert", "id"])
        fs2.post(deck, 923)
        self.assertEqual(deck['cuthbert'].id, 923)
        FieldSelector(["ruth"]).post(deck, {"id": 523, "name": "Ruth"})
        self.assertEqual(deck['ruth'].name, "Ruth")

        FieldSelector(["bob"]).delete(deck)
        self.assertNotIn("bob", deck)

        FieldSelector([None]).delete(deck)
        self.assertEqual(deck, {})

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
        # match, eg <MultiFieldSelector: (.foo.bar([0](.hiss|.boo)|[1])|.bar)>
        #  but also <MultiFieldSelector: (.bar|.foo.bar([1]|[0](.boo|.hiss)))>
        regexp = re.compile(
            r"""<MultiFieldSelector:\s+\(
                (?:
                  (?: .foo.bar \(
                      (?:
                          (?: \[0\] \(
                              (?:
                                  (?: .hiss | .boo ) \|?
                              ){2} \)
                            | \[1\] ) \|?
                      ){2} \)
                    | .bar ) \|?
                ){2}
            \)>""", re.X,
        )
        self.assertRegexpMatches(str(mfs), regexp)
        mfs_dupe = eval(repr(mfs))
        emitted = set(tuple(x.selectors) for x in mfs_dupe)
        self.assertEqual(emitted, selectors)

        # test various dict-like functions
        self.assertIn("foo", mfs)
        self.assertIn("bar", mfs)
        self.assertNotIn("baz", mfs)
        self.assertIn('bar', mfs['foo'])
        self.assertIn(0, mfs['foo']['bar'])
        self.assertIn('hiss', mfs['foo']['bar'][0])
        self.assertNotIn('miss', mfs['foo']['bar'][0])
        self.assertIn('baz', mfs['bar'])
        self.assertIn('baz', mfs['bar']['frop']['quux']['fred'])

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
            quux = DictProperty(of=str)
            frop = DictProperty(of=list_of(six.text_type))

        full = Pilcrow(
            bar=[dict(name="Heffalump"), dict(name="Uncle Robert")],
            foo=dict(bar=[dict(name="Owl", hiss="Hunny Bee"),
                          dict(name="Piglet")]),
            baz="Wizzle",
            quux={"protagonist": "Winnie_the_Pooh",
                  "antagonist": "Alexander_Beetle"},
            frop={"lighting": ["Uncle_Robert", "Kanga", "Small"],
                  "story": ["Smallest_of_all", "Eeyore",
                            "Christopher_Robin"]},
        )
        selectors.add(("quux", "protagonist"))
        self.assertEqual(
            FieldSelector(("quux", "protagonist")).get(full),
            "Winnie_the_Pooh",
        )
        selectors.add(("frop", "story"))
        mfs = MultiFieldSelector(*selectors)
        filtered = mfs.get(full)
        expected = Pilcrow(
            bar=[dict(name="Heffalump"), dict(name="Uncle Robert")],
            foo=dict(bar=[dict(hiss="Hunny Bee"),
                          dict(name="Piglet")]),
            quux={"protagonist": "Winnie_the_Pooh"},
            frop={"story": ["Smallest_of_all", "Eeyore",
                            "Christopher_Robin"]},
        )
        self.assertEqual(filtered, expected)

    def test_mfs_subscript_identity(self):
        """MultiFieldSelector subscript has an identity value"""
        mfs = MultiFieldSelector([None, "foo"])
        self.assertEqual(mfs.path, "[*].foo")
        self.assertEqual(mfs[FieldSelector(())].path, mfs.path)
        self.assertEqual(mfs[()].path, mfs.path)

    def test_mfs_subscript_by_selector(self):
        """MultiFieldSelector subscript using FieldSelector"""
        mfs = MultiFieldSelector([None, "foo"])
        self.assertEqual(mfs.path, "[*].foo")
        x = mfs[(1, "none")]
        self.assertEqual(x, None)
        self.assertEqual(mfs[FieldSelector((1, "none"))], None)

    def test_mfs_json(self):
        """MultiFieldSelector can work on JsonRecordList objects"""

        class Thing(JsonRecord):
            flintstone = JsonProperty()
            element = JsonProperty()

        class Things(JsonRecordList):
            itemtype = Thing

        flintstones = ("dino", "bammbamm", "wilma", "fred")
        elements = ("Rb", "At", "Pm", "Fl")
        data = list(
            {"flintstone": x[0], "element": x[1]} for x in
            zip(flintstones, elements)
        )

        all_the_things = Things(data)

        mfs = MultiFieldSelector([None, "flintstone"])
        self.assertEqual(
            mfs.get(all_the_things).json_data(),
            list(dict(flintstone=x) for x in flintstones),
        )

        mfs = MultiFieldSelector([None, "flintstone"], [None, "element"])
        self.assertEqual(mfs.get(all_the_things), all_the_things)

    def test_multi_selector_in(self):
        """Test FieldSelectors can be checked against MultiFieldSelectors"""
        mfs = MultiFieldSelector(
            ["rakkk", None, "awkkkkkk"],
            ["rakkk", None, "zgruppp"],
            ["cr_r_a_a_ck", "rip"],
            ["cr_r_a_a_ck", "aiieee"],
        )

        self.assertIn("rakkk", mfs)
        self.assertNotIn("ouch", mfs)
        self.assertIn(any, mfs)

        fs_in = tuple(
            FieldSelector(x) for x in (
                ("rakkk", 1, "zgruppp"),
                ("rakkk", None, "zgruppp"),
                ("rakkk", 2, "awkkkkkk", "bap"),
                ("cr_r_a_a_ck", "rip"),
                ("cr_r_a_a_ck", "rip", "spla_a_t"),
            )
        )

        for fs in fs_in:
            self.assertIn(fs, mfs, fs.path)

        fs_not_in = tuple(
            FieldSelector(x) for x in (
                ("rakkk",),
                ("rakkk", 0),
                ("rakkk", None),
                ("rakkk", 0, "aiee"),
                ("rakkk", "clank"),
                ("ouch",),
                ("cr_r_a_a_ck",),
                ("cr_r_a_a_ck", "zlopp"),
                ("rakkk", 1, "pow"),
            )
        )

        for fs in fs_not_in:
            self.assertNotIn(fs, mfs, fs.path)

        fs_some = fs_in + tuple(
            FieldSelector(x) for x in (
                ("rakkk",),
                ("rakkk", 0),
                ("cr_r_a_a_ck",),
            )
        )

        for fs in fs_some:
            self.assertIsNotNone(mfs[fs], fs.path)

        fs_not_any = tuple(
            FieldSelector(x) for x in (
                ("ouch",),
                ("cr_r_a_a_ck", "zlopp"),
                ("rakkk", 1, "pow"),
            )
        )

        for fs in fs_not_any:
            self.assertIsNone(mfs[fs], fs.path)

    def test_null_mfs(self):
        null_mfs = MultiFieldSelector()
        self.assertNotIn(any, null_mfs)
        self.assertFalse(null_mfs)
        self.assertFalse(null_mfs[any])

    def test_complete_mfs(self):
        complete_mfs = MultiFieldSelector.complete_mfs()
        fses = list(complete_mfs)
        self.assertEqual(len(fses), 1)
        self.assertEqual(fses[0].path, "[*]")

    def test_mfs_apply_ops(self):
        from copy import deepcopy
        from normalize.diff import DiffTypes

        selectors = (
            ("owner",),
            ("posts", 0, "comments", 0, "poster"),
            ("posts", 0, "comments", 1, "content"),
        )
        required_fields = (
            ("id",),
            ("posts", 0, "edited"),
            ("posts", 0, "post_id"),
            ("posts", 0, "wall_id"),
            ("posts", 0, "comments", 0, "edited"),
            ("posts", 0, "comments", 0, "id"),
            ("posts", 0, "comments", 1, "edited"),
            ("posts", 0, "comments", 1, "id"),
        )
        deletable_mfs = MultiFieldSelector(*selectors)
        skeleton_mfs = MultiFieldSelector(*(required_fields + selectors))

        scratch_wall = deepcopy(wall_one)
        saved_fields = skeleton_mfs.get(scratch_wall)
        deletable_mfs.delete(scratch_wall)
        removed = set(
            tuple(x.base) for x in wall_one.diff_iter(scratch_wall)
            if x.diff_type == DiffTypes.REMOVED
        )
        self.assertEqual(
            removed, set(selectors),
            "MultiFieldSelector.delete() can delete named attributes",
        )

        deletable_mfs.patch(scratch_wall, saved_fields)
        self.assertFalse(
            scratch_wall.diff(wall_one),
            "MultiFieldSelector.patch() can copy named attributes",
        )

        del saved_fields.owner
        deletable_mfs.patch(scratch_wall, saved_fields)
        self.assertFalse(
            hasattr(scratch_wall, "owner"),
            "MultiFieldSelector.patch() can delete missing attributes",
        )

    def test_mfs_marshal(self):
        mfs = MultiFieldSelector(
            ["rakkk", None, "awkkkkkk"],
            ["rakkk", None, "zgruppp"],
            ["cr_r_a_a_ck", "rip"],
            ["cr_r_a_a_ck", "aiieee"],
        )

        path = mfs.path

        new_mfs = MultiFieldSelector.from_path(path)
        for fs in mfs:
            self.assertIn(fs, new_mfs)
            parts = list(fs)
            self.assertIsNotNone(parts[-1])

        for fs in new_mfs:
            self.assertIn(fs, mfs)

        self.assertEqual(len(mfs.path), len(new_mfs.path))

        for path in (".foo", ".foo[*]", ".foo.bar[*]"):
            mfs = MultiFieldSelector.from_path(path)
            self.assertEqual(mfs.path, path)

        for mfs_fs in (
            ((),),
            (("foo",),),
            ((1,), (2,)),
            ((None,)),
            (("foo", "bar", None),),
        ):
            mfs = MultiFieldSelector(*mfs_fs)
            path = mfs.path
            mfs_loop = MultiFieldSelector.from_path(path)
            self.assertEqual(mfs_loop.path, path)
            self.assertEqual(list(fs.path for fs in mfs),
                             list(fs.path for fs in mfs_loop))
