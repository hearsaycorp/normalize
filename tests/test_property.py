"""tests for the new, mixin-based property/descriptor system"""

from __future__ import absolute_import

import re
import types
import unittest2

from normalize import RecordList
from normalize.coll import ListCollection
from normalize.record import Record
from normalize.property import LazyProperty
from normalize.property import LazySafeProperty
from normalize.property import Property
from normalize.property import ROLazyProperty
from normalize.property import ROProperty
from normalize.property import SafeProperty
from normalize.property.coll import ListProperty
from normalize.property.meta import MetaProperty


class TestProperties(unittest2.TestCase):
    """Test that the new data descriptor classes work"""
    def test_0_property(self):
        """Test that unbound Property objects can be created successfully"""
        prop = Property()
        self.assertIsNotNone(prop)
        self.assertIsInstance(prop, Property)
        self.assertIsInstance(type(prop), MetaProperty)
        self.assertRegexpMatches(str(prop), r".*unbound.*", re.I)
        self.assertIsInstance(prop, SafeProperty)

        roprop = Property(traits=['ro'])
        self.assertIsNotNone(roprop)
        self.assertIsInstance(roprop, ROProperty)
        self.assertIsInstance(type(prop), MetaProperty)

        name = ROProperty()
        self.assertIsNotNone(roprop)
        self.assertIsInstance(roprop, ROProperty)

        lazyprop = Property(lazy=True)
        self.assertIsInstance(lazyprop, LazyProperty)
        self.assertFalse(isinstance(lazyprop, SafeProperty))
        self.assertRaises(Exception, Property, lazy=False)
        self.assertRaises(Exception, Property, coerce=lambda x: 1)

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
        with self.assertRaises(AttributeError):
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
        with self.assertRaises(AttributeError):
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
            rbn = SafeProperty(required=True, isa=(str, types.NoneType))

        with self.assertRaises(ValueError):
            fr = FussyRecord()

        fr = FussyRecord(id=123, must="sugary", rbn="Hello")
        print str(fr)
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

        try:
            class GR2(Record):
                members = ListProperty(of=Item)
        except Exception, e:
            # callers: don't really test using exception string matching
            # like this.  wait or submit a PR for proper exception classes
            self.assertRegexpMatches(str(e), r'sorry Dave')
        else:
            self.fail("should have thrown exception")

    def test_customized_list_properties(self):
        """Test that list properties with custom collection behavior invoke
        such correctly"""
        class Eyetem(Record):
            name = Property()

        class CustomColl(ListCollection):
            @classmethod
            def coll_to_tuples(cls, values):
                if isinstance(values, types.StringType):
                    values = values.split(',')
                    for i, v in zip(xrange(0, len(values)), values):
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

        self.assertTrue(mtr.__getitem__)
        self.assertIsInstance(mtr, ManyThingsRecord)

    def test_subclassing(self):
        """Test that Record subclasses work"""
        class Thing(Record):
            id = Property()

        class NamedThing(Thing):
            name = Property()

        nt = NamedThing(id=123, name="adam")
