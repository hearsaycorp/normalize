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


import unittest2

from normalize import Property
from normalize import Record
from normalize.coll import *
from normalize.property.coll import DictProperty
from normalize.property.coll import ListProperty


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
