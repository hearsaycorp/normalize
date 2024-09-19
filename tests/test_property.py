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

"""tests for the new, mixin-based property/descriptor system"""

from __future__ import absolute_import

from builtins import zip, range
import six
import re
import types
import unittest

from normalize import RecordList
from normalize.coll import ListCollection
import normalize.exc as exc
from normalize.identity import record_id
from normalize.record import Record
from normalize.property import LazyProperty
from normalize.property import LazySafeProperty
from normalize.property import make_property_type
from normalize.property import Property
from normalize.property import ROLazyProperty
from normalize.property import ROProperty
from normalize.property import SafeProperty
from normalize.property.coll import ListProperty
from normalize.property.meta import _merge_camel_case_names
from normalize.property.meta import MetaProperty


class TestProperties(unittest.TestCase):
    """Test that the new data descriptor classes work"""
    def test_0_property(self):
        """Test that unbound Property objects can be created successfully"""
        prop = Property()
        self.assertIsNotNone(prop)
        self.assertIsInstance(prop, Property)
        self.assertIsInstance(type(prop), MetaProperty)
        self.assertRegexpMatches(str(prop), r".*unbound.*", re.I)

        roprop = Property(traits=['ro'])
        self.assertIsNotNone(roprop)
        self.assertIsInstance(roprop, ROProperty)
        self.assertIsInstance(type(prop), MetaProperty)

        roprop = ROProperty()
        self.assertIsNotNone(roprop)
        self.assertIsInstance(roprop, ROProperty)

        lazyprop = Property(lazy=True)
        self.assertIsInstance(lazyprop, LazyProperty)
        self.assertFalse(isinstance(lazyprop, SafeProperty))

        safelazyprop = Property(lazy=True, isa=str)
        self.assertIsInstance(safelazyprop, LazyProperty)
        self.assertIsInstance(safelazyprop, SafeProperty)

        self.assertRaises(exc.LazyIsFalse, Property, lazy=False)
        self.assertRaises(exc.CoerceWithoutType, Property, coerce=lambda x: 1)

    def test_1_basic(self):
        """Test that basic Properties can be defined and used"""
        class BasicRecord(Record):
            name = Property()
            defaulted = Property(default=lambda: [])
            default_none = Property(default=None)

        # test Property.__repr__ includes class & attribute name
        self.assertRegexpMatches(
            str(BasicRecord.__dict__['name']),
            r".*Property.*BasicRecord\.name.*", re.I,
        )

        br = BasicRecord()
        self.assertIsInstance(br, BasicRecord)
        self.assertIsInstance(br.defaulted, list)
        br.defaulted.append("foo")
        self.assertEqual(br.defaulted[0], "foo")
        with self.assertRaisesRegexp(AttributeError, r'BasicRecord.name'):
            br.name
        self.assertEqual(br.default_none, None)

        br = BasicRecord(name="Bromine")
        self.assertEqual(br.name, "Bromine")
        self.assertFalse(br.defaulted)

    def test_2_ro(self):
        """Test Attributes which don't allow being set"""
        class TrivialRecord(Record):
            id = ROProperty()
            name = Property()
        self.assertRegexpMatches(
            str(TrivialRecord.__dict__['id']),
            r".*ROProperty.*TrivialRecord\.id.*", re.I
        )

        tr = TrivialRecord(id=123)
        self.assertEqual(tr.id, 123)
        with self.assertRaisesRegexp(
            AttributeError, r'TrivialRecord.id.*read-only',
        ):
            tr.id = 124

        tr.name = "Travel Guides"
        self.assertEqual(tr.name, "Travel Guides")

    def test_3_lazy(self):
        """Test Attributes which are build-once"""
        _seq_num = [0]

        def _seq():
            _seq_num[0] += 1
            return _seq_num[0]

        def _func_with_default_args(plus=5):
            return _seq() + plus

        class TrapDoorRecord(Record):
            def _shoot(self):
                projectile = self.chamber
                self.chamber = "empty"
                return projectile
            chamber = Property()
            fired = LazyProperty(default=_shoot)
            ask = LazyProperty(default=_seq)
            plus = LazyProperty(default=_func_with_default_args)

        tdr = TrapDoorRecord(chamber="bolt")
        self.assertNotIn(
            "fired", tdr.__dict__, "peek into lazy object's dict"
        )
        self.assertNotIn("ask", tdr.__dict__)
        self.assertEqual(tdr.fired, "bolt")
        self.assertEqual(tdr.chamber, "empty")
        self.assertEqual(tdr.fired, "bolt")
        self.assertEqual(tdr.ask, 1)
        self.assertEqual(tdr.ask, 1)
        self.assertEqual(tdr.plus, 7)

        # lazy properties may be assigned
        tdr.fired = None
        self.assertEqual(tdr.fired, None)
        self.assertEqual(TrapDoorRecord.fired.__get__(tdr), None)

        # delete and start again!
        tdr.chamber = "bullet"
        del tdr.fired
        self.assertEqual(tdr.fired, "bullet")

    def test_4_required_check(self):
        """Test Attributes which are marked as required"""
        class FussyRecord(Record):
            id = Property(required=True, isa=int)
            natural = SafeProperty(check=lambda i: i > 0)
            must = SafeProperty(required=True)
            rbn = SafeProperty(required=True, isa=(str, type(None)))

        with self.assertRaises(ValueError):
            fr = FussyRecord()

        fr = FussyRecord(id=123, must="sugary", rbn="Hello")
        self.assertIn("Hello", str(fr))
        self.assertEqual(fr, eval(repr(fr)))
        with self.assertRaises(ValueError):
            del fr.must
        with self.assertRaises(ValueError):
            fr.must = None
        fr.must = "barmy"
        with self.assertRaises(ValueError):
            del fr.rbn
        fr.rbn = None

        fr.natural = 7
        with self.assertRaises(ValueError):
            fr.natural = 0

    def test_5_raisins_of_etre(self):
        """Check that property types which are mixed-in combinations of types
        work as expected"""
        num = [0]

        def seq():
            num[0] += 1
            return num[0]

        class VariedRecord(Record):
            def _lazy(self):
                return "%s.%d" % (self.must, self.id)
            id = ROLazyProperty(
                required=True, check=lambda i: i > 0, default=seq,
            )
            must = SafeProperty(required=True)
            lazy = LazySafeProperty(
                check=lambda i: re.match(r'\w+\.\d+$', i),
                default=_lazy,
            )

        vr = VariedRecord(must="horn")
        self.assertEqual(vr.lazy, "horn.1")
        self.assertEqual(
            vr.lazy, "horn.1", "lazy, safe attribute not re-computed"
        )
        vr.lazy = "belly.5"
        with self.assertRaises(ValueError):
            vr.lazy = "dog collar.3"

        vr.must = "snout"
        self.assertEqual(vr.lazy, "belly.5")

        with self.assertRaises(AttributeError):
            vr.id = 2
        with self.assertRaises(ValueError):
            vr.must = None

        num[0] = -1
        vr = VariedRecord(must="ears")
        with self.assertRaises(ValueError):
            # test RO lazy value is computed late, and the result is
            # type checked
            vr.id

    def test_list_properties(self):
        """Test that List Properties can be created which are iterable"""
        class Item(Record):
            name = Property()

        class GroupingRecord(Record):
            members = ListProperty(of=Item)

        gr = GroupingRecord(members=[Item(name="bob"), Item(name="bill")])

        self.assertIsInstance(gr.members, ListCollection)
        self.assertIsInstance(gr.members[0], Item)
        members = list(gr.members)
        self.assertEqual(members[0].name, "bob")
        self.assertEqual(members[1].name, "bill")

        class Item(Record):
            age = Property()

        with self.assertRaises(exc.PropertyNotUnique):
            class GR2(Record):
                members = ListProperty(of=Item)

    def test_customized_list_properties(self):
        """Test that list properties with custom collection behavior invoke
        such correctly"""
        class Eyetem(Record):
            name = Property()

        class CustomColl(ListCollection):
            @classmethod
            def coll_to_tuples(cls, values):
                if isinstance(values, six.string_types):
                    values = values.split(',')
                    for i, v in zip(range(0, len(values)), values):
                        yield i, {'name': v}
                else:
                    for x in super(CustomColl, cls).coll_to_tuples(values):
                        yield x

        class GroupingRecord(Record):
            members = ListProperty(coll=CustomColl, of=Eyetem)

        # Instantiating with Python objects should still work...
        gr = GroupingRecord(members=[Eyetem(name="bob"), Eyetem(name="bill")])

        self.assertIsInstance(gr.members, ListCollection)
        self.assertIsInstance(gr.members[0], Eyetem)
        members = list(gr.members)
        self.assertEqual(members[0].name, "bob")
        self.assertEqual(members[1].name, "bill")

        # Instantiating from the dict should work as well, with custom behavior
        gr = GroupingRecord({'members': 'bob,bill'})

        self.assertIsInstance(gr.members, ListCollection)
        self.assertIsInstance(gr.members[0], Eyetem)
        members = list(gr.members)
        self.assertEqual(members[0].name, "bob")
        self.assertEqual(members[1].name, "bill")

    def test_list_records(self):
        """Test that RecordList works"""
        class SingleThing(Record):
            name = Property()

        class ManyThingsRecord(RecordList):
            itemtype = SingleThing

        # note: must pass pre-coerced members to constructor.
        mtr = ManyThingsRecord(
            (SingleThing(name="bert"), SingleThing(name="phil"))
        )
        self.assertEqual(record_id(mtr[0]), ("bert",))
        self.assertEqual(record_id(mtr), (("bert",), ("phil",)))

        self.assertTrue(mtr.__getitem__)
        self.assertIsInstance(mtr, ManyThingsRecord)

        # test construction from generators
        def generator(seq):
            for x in seq:
                yield x

        ManyThingsRecord(generator(mtr))

        # ...iterators...
        ManyThingsRecord(mtr)

    def test_subclassing(self):
        """Test that Record subclasses work"""
        class Thing(Record):
            id = Property()

        class NamedThing(Thing):
            name = Property()

        NamedThing(id=123, name="adam")

    def test_property_meta_names(self):
        """Test the property metaclass creates new property names OK"""
        self.assertEqual(
            _merge_camel_case_names("MetaProperty", "SafeProperty"),
            "SafeMetaProperty",
        )
        self.assertEqual(
            _merge_camel_case_names("LazyListProperty", "SafeJsonProperty"),
            "SafeJsonLazyListProperty",
        )

    def test_property_mixin_ok(self):
        """Test that properties can be mixed in automagically"""

        class MyLittleProperty(Property):
            __trait__ = "mylittle"

            def __init__(self, pony_name=None, **kwargs):
                super(MyLittleProperty, self).__init__(**kwargs)

        mlp = Property(pony_name="Applejack", isa=str)

        self.assertIsInstance(mlp, MyLittleProperty)
        self.assertIsInstance(mlp, SafeProperty)
        self.assertEqual(type(mlp).traits, ("mylittle", "safe"))

        lazypony = Property(pony_name="Persnickety", lazy=lambda: "x")
        self.assertEqual(type(lazypony).traits, ("lazy", "mylittle"))
        self.assertIsInstance(lazypony, MyLittleProperty)
        self.assertIsInstance(lazypony, LazyProperty)

    def test_property_mixin_exc(self):
        """Test that bad property mixes raise the right exceptions"""

        class SuperProperty(SafeProperty):
            __trait__ = "pony"

            def __init__(self, hero_name=None, **kwargs):
                super(SuperProperty, self).__init__(**kwargs)

        Property(hero_name="Bruce Wayne")

        with self.assertRaises(exc.PropertyTypeMixinNotPossible):
            Property(hero_name="Bruce Wayne", traits=['unsafe'])

    def test_make_property_type(self):
        """Test that make_property_type can morph types"""
        SimpleStrProperty = make_property_type(
            "FooProperty", isa=str,
        )
        ssp = SimpleStrProperty()
        self.assertEqual(ssp.valuetype, str)

    def test_isa_coerce_required(self):
        """Test various combinations of isa=, coerce=, required="""
        # should later add more tests for combinations including check= as well

        def positive_int_or_none(x):
            return int(x) if int(x) > 0 else None

        class Mixed(Record):
            id = Property(required=True, isa=int, coerce=positive_int_or_none)
            num = Property(isa=int, coerce=positive_int_or_none)

            def get_what(self):
                return "I'm Mixed %d" % self.id

            what = Property(
                default=get_what,
                isa=int,
                lazy=True,
                required=True,
            )

            def get_hmm(self):
                return positive_int_or_none(self.what)

            hmm = Property(isa=int, required=True, lazy=True, default=get_hmm)

            def get_huh(self):
                return str(self.what)

            huh = Property(isa=int, required=True, lazy=True,
                           coerce=positive_int_or_none, default=get_huh)

        with self.assertRaisesRegexp(exc.ValueCoercionError, r'Mixed.id'):
            mixer = Mixed(id="-1")

        mixer = Mixed(id="1", num="-6")
        with self.assertRaises(AttributeError):
            mixer.num

        with self.assertRaises(TypeError):
            mixer.num = "-2"
        with self.assertRaises(TypeError):
            mixer.id = "-3"

        for i in 1, 2:
            with self.assertRaises(TypeError):
                mixer.what
        mixer.what = 2
        self.assertEqual(mixer.what, 2)

        mixer.num = "3"
        self.assertEqual(mixer.num, 3)
        with self.assertRaises(TypeError):
            mixer.num = "-4"

        mixer.what = -5
        with self.assertRaises(TypeError):
            mixer.hmm
        with self.assertRaises(TypeError):
            mixer.huh

        mixer.what = 4
        self.assertEqual(mixer.hmm, 4)
        self.assertEqual(mixer.huh, 4)

    def test_list_of(self):

        class Person(Record):
            name = Property()

        class Warfare(Record):
            proleteriat = Property(list_of=Person)
            bourgeois = ListProperty(of=Person)

        society = Warfare(
            proleteriat=[{"name": "Joe Bloggs"}],
            bourgeois=[{"name": "Richard B'stard"}],
        )

        self.assertIsInstance(society.proleteriat[0], Person)
        self.assertIsInstance(society.bourgeois[0], Person)

    def test_list_safety(self):
        """Test that ListProperty implies SafeProperty"""

        with self.assertRaises(exc.ListOfWhat):
            self.assertIsInstance(ListProperty(), SafeProperty)

        self.assertIsInstance(ListProperty(of=str), SafeProperty)
        self.assertIsInstance(ListProperty(of=Record), SafeProperty)

    def test_unknown_kwarg(self):
        with self.assertRaisesRegexp(TypeError, r"'yo_momma' of Property"):
            Property(yo_momma="so fat, when she sits around the house, "
                              "she really SITS AROUND THE HOUSE")
