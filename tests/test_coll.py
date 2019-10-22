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


from past.builtins import basestring
import unittest2

from normalize import Property
from normalize import Record
from normalize.coll import *
from normalize.diff import DiffTypes
import normalize.exc as exc
from normalize.property.coll import DictProperty
from normalize.property.coll import ListProperty
from normalize.property.json import JsonDictProperty
from normalize.property.json import JsonListProperty


class Item(Record):
    name = Property()


class TestCollections(unittest2.TestCase):

    def test_list_basics(self):

        class Bag(Record):
            items = ListProperty(of=Item)

        bag = Bag()
        bag.items = [{"name": "bob"}]
        self.assertIsInstance(bag.items[0], Item)

    def test_dict_basics(self):

        class Drawer(Record):
            items = DictProperty(of=Item)

        drawer = Drawer()
        drawer.items = {"top": {"name": "bob"}}
        self.assertIsInstance(drawer.items['top'], Item)

    def test_list_of_str(self):

        class Array(Record):
            items = ListProperty(of=str)

        arr = Array()
        arr.items = ["bob", None, 2]
        self.assertEqual(list(arr.items), ["bob", "None", "2"])

    def test_dict_of_str(self):

        class Mapping(Record):
            items = DictProperty(of=str)

        # note: DictProperty does not yet let you specify the key type.
        map_ = Mapping()
        map_.items = {"foo": "bob", "x": None, 3: 2}
        self.assertEqual(dict(map_.items.itertuples()),
                         {"foo": "bob", "x": "None", 3: "2"})

    def test_list_operations(self):
        class Listicle(Record):
            theme = Property()
            witty_examples = ListProperty(of=Item)

        article = Listicle()
        article.witty_examples = []
        wittiness = article.witty_examples
        self.assertEqual(len(article.witty_examples), 0)

        wittiness.append({"name": "Bob"})
        self.assertEqual(len(wittiness), 1)
        self.assertIsInstance(wittiness[0], Item)

        wittiness.extend(
            ({"name": "Jane"}, {"name": "Jill"},)
        )
        self.assertIsInstance(wittiness[2], Item)

        self.assertEqual(wittiness.pop(), Item(name="Jill"))
        self.assertEqual(wittiness, [Item(name="Bob"), Item(name="Jane")])
        self.assertEqual(wittiness.count(Item(name="Bob")), 1)

        self.assertEqual(wittiness.index(Item(name="Bob")), 0)
        wittiness.extend(
            ({"name": "Peter"}, {"name": "Jack"},
             {"name": "Gertrude"}, {"name": "Cuthbert"},)
        )
        w = list(wittiness)  # compare behavior with standard list
        self.assertEqual(wittiness.index(Item(name="Jack")), 3)
        self.assertEqual(w.index(Item(name="Jack")), 3)
        self.assertRaises(ValueError, wittiness.index, Item(name="Jack"), 4)
        self.assertRaises(ValueError, w.index, Item(name="Jack"), 4)
        self.assertRaises(ValueError, wittiness.index, Item(name="Jack"), 1, 2)
        self.assertRaises(ValueError, w.index, Item(name="Jack"), 1, 2)
        self.assertEqual(wittiness.index(Item(name="Jane"), 1, 2), 1)
        self.assertEqual(w.index(Item(name="Jane"), 1, 2), 1)

        self.assertEqual(wittiness.pop(3), Item(name="Jack"))

        wittiness.remove(Item(name="Peter"))
        self.assertEqual(wittiness[-1], Item(name="Cuthbert"))
        del wittiness[-1]
        self.assertEqual(wittiness[-1], Item(name="Gertrude"))

        wittiness.sort(key=lambda item: item.name)
        self.assertEqual(wittiness[-2], Item(name="Gertrude"))

        wittiness.reverse()
        self.assertEqual(wittiness[0], Item(name="Jane"))

        # slicing!
        self.assertEqual(wittiness[0:1], [Item(name="Jane")])
        self.assertEqual(
            wittiness[0:3:2], [Item(name="Jane"), Item(name="Bob")],
        )

        wittiness[1:3] = [{"name": "Worzel"}]
        self.assertEqual(wittiness, [Item(name="Jane"), Item(name="Worzel")])

        wittiness.extend(
            ({"name": "Phil"}, {"name": "Quentin"},
             {"name": "Arthur"}, {"name": "George"},)
        )
        wittiness[1:5:2] = [{"name": "Dagon"}, {"name": "Ruth"}]
        del wittiness[0:-1:2]
        self.assertEqual(
            wittiness,
            [Item(name="Dagon"), Item(name="Ruth"), Item(name="George")],
        )

    def test_dict_operations(self):
        class HashMap(Record):
            intent = Property()
            hashed = DictProperty(of=Item)

        hashmap = HashMap(hashed={})
        dp = hashmap.hashed
        self.assertEqual(len(dp), 0)

        dp['bob'] = Item(name="Bob")
        self.assertIsInstance(dp['bob'], Item)
        dp['bert'] = {"name": "Bert"}
        self.assertIsInstance(dp['bert'], Item)

        dp.update(dict(ernest={"name": "Ernest"},
                       leonard={"name": "Leonard"}))
        self.assertIsInstance(dp['ernest'], Item)

        dp2 = type(dp)()
        dp2.update(dp.itertuples())

        self.assertEqual(len(dp2), len(dp))
        self.assertEqual(dp2, dp)

        self.assertEqual(
            set(dp.keys()),
            {"bob", "bert", "ernest", "leonard"},
        )

        del dp['bob']

        self.assertEqual(
            set(dp.values()),
            {Item(name='Bert'),
             Item(name='Leonard'), Item(name='Ernest')}
        )

        dp2.clear()
        self.assertEqual(dp2, {})

        self.assertEqual(dp.pop("bert"), Item(name="Bert"))
        self.assertEqual(dp.pop("ernest"), Item(name="Ernest"))
        self.assertEqual(dp.popitem(), ("leonard", Item(name="Leonard")))
        self.assertEqual(dp, {})
        self.assertEqual(dp, dp2)

        dp.update(fred=Item(name="Fred"))
        self.assertEqual(dp['fred'], Item(name="Fred"))

    def test_list_of(self):
        los = list_of(str)(["foo", "bar"])
        self.assertEqual(repr(los), "strList(['foo', 'bar'])")

        los += [1]
        self.assertEqual(los[-1], "1")
        self.assertIn("bar", los)
        self.assertIn(1, los)
        self.assertNotIn("quux", los)

        loi = list_of(int)()
        loi.append(1)
        loi += [2, 3]
        with self.assertRaisesRegexp(
            exc.CoercionError,
            r"coerce to int for insertion to intList failed",
        ):
            loi.append("foo")

    def test_dict_of(self):
        dos = dict_of(str)({"foo": "bar"})
        self.assertEqual(repr(dos), "strMap({'foo': 'bar'})")
        self.assertIn("foo", dos)
        self.assertNotIn("bar", dos)
        with self.assertRaises(exc.CoercionError):
            dos = dict_of(str)("foobar")

        # test that these simple collections can be compared
        self.assertEqual(dos.diff(dos), [])
        dos2 = dict_of(str)({"foo": "baz"})
        diffs = dos.diff(dos2)
        self.assertEqual(len(diffs), 1)
        self.assertEqual(diffs[0].base.path, ".foo")

    def test_dict_of_list_of_str(self):
        class MyDoLoS(Record):
            items = DictProperty(of=list_of(str), default={})

        # note: DictProperty does not yet let you specify the key type.
        container = MyDoLoS()
        dolos = container.items

        dolos['bob'] = ["foo", "bar"]
        self.assertEqual(dolos, {"bob": ["foo", "bar"]})
        self.assertEqual(
            repr(dolos), "strListMap({'bob': strList(['foo', 'bar'])})",
        )

        with self.assertRaises(exc.CoercionError):
            dolos['baz'] = "foobar"

        # test that these collections can be compared
        self.assertEqual(dolos.diff(dolos), [])
        dolos2 = type(dolos)({"bob": ["foo", "bar", "frop"]})
        diffs = dolos.diff(dolos2)
        self.assertEqual(len(diffs), 1)
        self.assertEqual(diffs[0].other.path, ".bob[2]")
        self.assertEqual(diffs[0].diff_type, DiffTypes.ADDED)

    def test_json_coll(self):
        class JLR(Record):
            item_list = JsonListProperty(of=Item)
            string_list = JsonListProperty(of=basestring)

        class JDR(Record):
            item_map = JsonDictProperty(of=Item)
            int_map = JsonDictProperty(of=int)

        jlr = JLR({"item_list": [{"name": "Bob"}],
                   "string_list": ["one", "two", "three"]})

        self.assertEqual(jlr.item_list[0].name, "Bob")
        self.assertEqual(jlr.string_list, ["one", "two", "three"])

        jdr = JDR({"item_map": {"bob": {"name": "Bob"}},
                   "int_map": {"one": 1, "two": 2, "three": 3}})

        jdr.item_map = {"bill": jlr.item_list[0]}
        jlr.item_list = list(jdr.item_map.values())

    # TODO type unions for item types
