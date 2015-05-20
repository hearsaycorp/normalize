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
