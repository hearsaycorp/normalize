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
        self._values = type(self).tuples_to_coll(
            type(self).coll_to_tuples(values)
        )
        super(Collection, self).__init__(**kwargs)

    def __iter__(self):
        """The default iterator always iterates over the *values* of a
        Collection."""
        for x in self._values:
            yield x

    def __contains__(self, item):
        return self.coerce_value(item) in self._values

    def __eq__(self, other):
        """To be ``==``, collections must have exactly the same ``itemtype``
        and ``colltype``, and equal ``values``
        """
        # coerce collections derived from simple python collection types
        if not isinstance(other, type(self)) and \
                isinstance(other, self.colltype):
            other = type(self)(other)
        return self.itemtype == getattr(other, "itemtype", None) and \
            self._values == getattr(other, "_values", None)

    def __ne__(self, other):
        """Implemented, for compatibility"""
        return not self.__eq__(other)

    def __len__(self):
        """Forwarded to the ``values`` property."""
        return len(self._values)

    @classmethod
    def coerce_value(cls, v):
        """Coerce a value to the right type for the collection, or return it if
        it is already of the right type."""
        if isinstance(v, cls.itemtype):
            return v
        else:
            try:
                return cls.coerceitem(v)
            except Exception as e:
                raise exc.CollectionItemCoerceError(
                    itemtype=cls.itemtype,
                    colltype=cls,
                    passed=v,
                    exc=e,
                )

    @classmethod
    def coerce_tuples(cls, generator):
        """This class method converts a generator of ``(K, V)`` tuples (the
        *tuple protocol*), where ``V`` is not yet of the correct type, to a
        generator where it is of the correct type (using the ``coerceitem``
        class property)
        """
        for k, v in generator:
            yield k, cls.coerce_value(v)

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
    def __getitem__(self, key):
        return self._values[key]

    def __setitem__(self, key, item):
        self._values[key] = self.coerce_value(item)

    def __delitem__(self, key):
        del self._values[key]


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
        if isinstance(coll, basestring):
            raise exc.CollectionCoerceError(
                passed=coll,
                colltype=cls,
            )
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
        return self._values.iteritems()

    def iteritems(self):
        return self.itertuples()

    def items(self):
        return self.itertuples()

    def clear(self):
        self._values.clear()

    def iterkeys(self):
        return (k for k, v in self.itertuples())

    def itervalues(self):
        return (v for k, v in self.itertuples())

    def keys(self):
        return self._values.keys()

    def values(self):
        return self._values.values()

    def pop(self, k):
        return self._values.pop(k)

    def popitem(self):
        return self._values.popitem()

    def update(self, iterable=None, **kw):
        keys = getattr(iterable, "keys", None)
        if keys and callable(keys):
            for k in iterable.keys():
                self[k] = self.coerce_value(iterable[k])
        elif iterable is not None:
            for k, v in iterable:
                self[k] = self.coerce_value(v)
        for k, v in kw.items():
            self[k] = self.coerce_value(v)

    def __repr__(self):
        """Implemented: prints a valid constructor.
        """
        property_info = super(DictCollection, self).__repr__()
        dict_info = repr(self._values)
        optional_comma = "" if property_info.endswith("()") else ", "
        return property_info.replace(
            "(", "(" + dict_info + optional_comma, 1)

    def __contains__(self, item):
        # don't fall through, because 'in' checks keys in dicts
        return item in self._values


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
        if isinstance(coll, basestring):
            raise exc.CollectionCoerceError(
                passed=coll,
                colltype=cls,
            )
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
                passed=coll,
                colltype=cls,
            )

    def append(self, item):
        """Adds a new value to the collection, coercing it.
        """
        self._values.append(self.coerce_value(item))

    def extend(self, iterable):
        """Adds new values to the end of the collection, coercing items.
        """
        # perhaps: self[len(self):len(self)] = iterable
        self._values.extend(self.coerce_value(item) for item in iterable)

    def count(self, value):
        return self._values.count(value)

    def index(self, x, i=0, j=None):
        len_ = len(self)
        if i < 0:
            i += len_
            if i < 0:
                i = 0
        if j is None:
            j = len_
        elif j < 0:
            j += len_
            if j < 0:
                j = 0
        for k in xrange(i, j):
            if self[k] == x:
                return k
        raise ValueError("%r is not in list" % x)

    def insert(self, i, x):
        if i < 0:
            i += len(self)
        if i < 0:
            i = 0
        self[i:i] = x

    def pop(self, i=-1):
        if i < 0:
            i += len(self)
            if i < 0:
                i = 0
        x = self[i]
        del self[i]
        return x

    def remove(self, x):
        del self[self.index(x)]

    def reverse(self):
        self._values.reverse()

    def sort(self, *a, **kw):
        self._values.sort(*a, **kw)

    def __setitem__(self, key, value):
        if isinstance(key, slice):
            self._values[key] = (self.coerce_value(item) for item in value)
        else:
            return super(ListCollection, self).__setitem__(key, value)

    def itertuples(self):
        return type(self).coll_to_tuples(self._values)

    def __str__(self):
        """Informal stringification returns the type of collection, and the
        length.  For example, ``<MyRecordList: 8 item(s)>``
        """
        return "<%s: %d item(s)>" % (
            type(self).__name__, len(self._values)
        )

    def __repr__(self):
        """Implemented: prints a valid constructor.
        """
        property_info = super(ListCollection, self).__repr__()
        list_info = "[%s]" % ", ".join(repr(x) for x in self._values)
        optional_comma = "" if property_info.endswith("()") else ", "
        return property_info.replace("(", "(" + list_info + optional_comma, 1)

    def __add__(self, other):
        if not isinstance(other, type(self)) and \
                isinstance(other, self.colltype):
            other = type(self)(other)
        return type(self)(self._values + other._values)

    @property
    def values(self):
        import warnings
        warnings.warn(
            "ListCollection.values is deprecated and will be removed in "
            "a future release; try removing '.values' from the expression",
            stacklevel=2,
        )
        return self

    @values.setter
    def values(self, value):
        import warnings
        warnings.warn(
            "ListCollection.values is deprecated and will be removed in "
            "a future release; assign to the property directly in the parent "
            "object or use slice assignment",
            stacklevel=2,
        )
        self[:] = value


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
        return (_GenericPickler(type(self).generic_key), (self._values,))


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


def list_of(of):
    return _make_generic(of, ListCollection)


def dict_of(of):
    return _make_generic(of, DictCollection)
