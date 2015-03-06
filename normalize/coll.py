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

import collections
import sys
import types

import normalize.exc as exc
from normalize.record import Record

"""This class contains container classes which can act like collections but
conform to this package's metaclass API"""


class _classproperty(object):
    def __init__(self, f):
        self.f = f

    def __get__(self, obj, owner):
        return self.f(owner)


class Collection(Record):
    """This is the base class for Record property values which contain
    iterable sets of values with a particular common type.

    All collections are modeled as a mapping from some index to a value.
    Bags are not currently supported, ie the keys must be unique for the diff
    machinery as currently written to function.

    The type of members in the collection is defined using a sub-class API:

        *classproperty* **itemtype**\ =\ *Record sub-class*
            This property must be defined for instances to be instantiable.
            It declares the type of values.

        *classproperty* **coerceitem**\ =\ *FUNC*
            Defaults to *itemtype* and is the function or constructor which
            will accept items during construction of a collection which are not
            already of the correct type.

        *classproperty* **colltype**\ =\ *collection type*
            This is the type of the underlying container.  ``list``, ``dict``,
            etc.
    """
    @_classproperty
    def itemtype(cls):
        raise exc.CollectionDefinitionError(
            property='itemtype',
            coll='Collection',
        )

    @_classproperty
    def coerceitem(cls):
        return cls.itemtype

    @_classproperty
    def colltype(cls):
        raise exc.CollectionDefinitionError(
            property='colltype',
            coll='Collection',
        )

    @classmethod
    def record_cls(cls):
        return cls.itemtype

    def __init__(self, values=None, **kwargs):
        """
        Default collection constructor.

        args:

            ``values=``\ *iterable*
                Specify the initial contents of the collection.  It will be
                converted to the correct type using :py:meth:`coll_to_tuples`
                and :py:meth:`tuples_to_coll`

            ``attribute=``\ *VALUE*
                It is possible to add extra properties to ``Collection``
                objects; this is how you specify them on construction.
        """
        self.values = type(self).tuples_to_coll(
            type(self).coll_to_tuples(values)
        )
        super(Collection, self).__init__(**kwargs)

    def __iter__(self):
        """The default iterator always iterates over the *values* of a
        Collection."""
        for x in self.values:
            yield x

    def __eq__(self, other):
        """To be ``==``, collections must have exactly the same ``itemtype``
        and ``colltype``, and equal ``values``
        """
        return self.itemtype == getattr(other, "itemtype", None) and \
            self.values == getattr(other, "values", None)

    def __ne__(self, other):
        """Implemented, for compatibility"""
        return not self.__eq__(other)

    def __len__(self):
        """Forwarded to the ``values`` property."""
        return len(self.values)

    @classmethod
    def coerce_tuples(cls, generator):
        """This class method converts a generator of ``(K, V)`` tuples (the
        *tuple protocol*), where ``V`` is not yet of the correct type, to a
        generator where it is of the correct type (using the ``coerceitem``
        class property)
        """
        for k, v in generator:
            yield k, v if isinstance(v, cls.itemtype) else cls.coerceitem(v)

    @classmethod
    def tuples_to_coll(cls, generator, coerce=False):
        """*required virtual method* This class method, part of the sub-class
        API, converts a generator of ``(K, V)`` tuples (the *tuple protocol*)
        to one of the underlying collection type.
        """
        if cls != Collection:
            raise exc.CollectionDefinitionError(
                property='tuples_to_coll',
                coll='Collection',
            )

    def itertuples(self):
        """Iterate over the items in the collection; return (k, v) where k is
        the key, index etc into the collection (or potentially the value
        itself, for sets).  This form is the *tuple protocol*"""
        raise exc.CollectionDefinitionError(
            property='itertuples',
            coll='Collection',
        )

    @classmethod
    def coll_to_tuples(cls, coll):
        """Generate 'conformant' tuples from an input collection, similar to
        itertuples"""
        raise exc.CollectionDefinitionError(
            property='coll_to_tuples',
            coll='Collection',
        )


class KeyedCollection(Collection):
    def __getitem__(self, item):
        return self.values[item]


class DictCollection(KeyedCollection):
    """An implementation of keyed collections which obey the `Record` property
    protocol and the tuple collection protocol.  *Warning*: largely untested,
    patches welcome.
    """
    suffix = "Map"
    colltype = dict

    @classmethod
    def tuples_to_coll(cls, generator, coerce=True):
        return cls.colltype(
            cls.coerce_tuples(generator) if coerce else generator
        )

    @classmethod
    def coll_to_tuples(cls, coll):
        if isinstance(coll, collections.Mapping):
            for k, v in coll.iteritems():
                yield k, v
        elif isinstance(coll, collections.Sequence):
            i = 0
            for v in coll:
                yield (i, v)
                i += 1
        elif hasattr(coll, "next") and callable(coll.next):
            i = 0
            for v in coll:
                if isinstance(v, tuple) and len(v) == 2:
                    yield v
                else:
                    yield (i, v)
                i += 1

    def itertuples(self):
        return self.values.iteritems()


class ListCollection(KeyedCollection):
    """An implementation of sequences which obey the `Record` property protocol
    and the tuple collection protocol.
    """
    suffix = "List"
    colltype = list

    @classmethod
    def tuples_to_coll(cls, generator, coerce=True):
        tuples = cls.coerce_tuples(generator) if coerce else generator
        return cls.colltype(v for k, v in tuples)

    @classmethod
    def coll_to_tuples(cls, coll):
        """``coll_to_tuples`` is capable of unpacking its own collection types
        (`list`), ``collections.Mapping`` objects, as well generators,
        sequences and iterators.  Returns ``(*int*, Value)``.  Does not coerce
        items.
        """
        if isinstance(coll, collections.Mapping):
            i = 0
            for k in sorted(coll.keys()):
                yield (i, coll[k])
        elif isinstance(coll, (collections.Sequence, types.GeneratorType)) or (
            hasattr(coll, "next") and callable(coll.next)
        ) or (
            hasattr(coll, "__iter__") and callable(coll.__iter__)
        ):
            i = 0
            for v in coll:
                yield i, v
                i += 1
        elif not coll:
            return
        else:
            raise exc.CollectionCoerceError(
                giventype=type(coll).__name__,
                fortype=cls.__name__,
            )

    def append(self, item):
        """``Sequence`` API, currently passed through to underlying collection.
        Type-checking is currently TODO.
        """
        self.values.append(item)

    def itertuples(self):
        return type(self).coll_to_tuples(self.values)

    def __str__(self):
        """Informal stringification returns the type of collection, and the
        length.  For example, ``<MyRecordList: 8 item(s)>``
        """
        return "<%s: %d item(s)>" % (
            type(self).__name__, len(self.values)
        )

    def __repr__(self):
        """Implemented: prints a valid constructor.
        """
        property_info = super(ListCollection, self).__repr__()
        list_info = "[%s]" % ", ".join(repr(x) for x in self.values)
        optional_comma = "" if property_info.endswith("()") else ", "
        return property_info.replace("(", "(" + list_info + optional_comma, 1)


GENERIC_TYPES = dict()


class _GenericPickler(object):
    """'pickle' doesn't like pickling classes which are dynamically created.
    This object is used instead, to keep pickle happy.
    """
    def __init__(self, typekey):
        self.typekey = typekey

    def __call__(self, values):
        return GENERIC_TYPES[self.typekey](values=values)


class _Generic(Collection):
    """A mix-in to mark collection types which are (for example) collections of
    things."""
    def __reduce__(self):
        """helper method for pickling"""
        return (_GenericPickler(type(self).generic_key), (self.values,))


def _make_generic(of, coll):
    """Used to make a new Collection type, without that type having to be
    defined explicitly.  Generates a new type name using the item type and a
    'suffix' Collection class property.

    args:

        ``of=``\ *Record type*
            The type of values of the collection

        ``coll=``\ *Collection sub-class*
            The container class.
    """

    assert(issubclass(coll, Collection))
    key = (coll.__name__, "%s.%s" % (of.__module__, of.__name__))
    if key in GENERIC_TYPES:
        if GENERIC_TYPES[key].itemtype != of:
            raise exc.PropertyNotUnique(key=key)
    else:
        # oh, we get to name it?  Goodie!
        generic_name = "%s%s" % (of.__name__, coll.suffix)
        GENERIC_TYPES[key] = type(
            generic_name, (coll, _Generic), dict(itemtype=of, generic_key=key)
        )
        mod = sys.modules[of.__module__]
        if not hasattr(mod, generic_name):
            setattr(mod, generic_name, GENERIC_TYPES[key])
    return GENERIC_TYPES[key]
