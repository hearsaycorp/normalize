
from __future__ import absolute_import

from normalize.record import Record

"""This class contains container classes which can act like collections but
conform to this package's metaclass API"""


class Collection(Record):
    """All collections are modeled as a mapping from some index to a value.
    Bags are not currently supported, ie the keys must be unique for the diff
    machinery as currently written to function.
    """
    @property
    def itemtype(self):
        raise Exception("itemtype must be defined in a subclass")

    @property
    def record_cls(self):
        return self.itemtype

    """This is the base class for Record property values which contain
    iterable sets of values with a particular common type."""
    def __init__(self, values=None, **kwargs):
        """
        @param of The Record type of members in this collection
        @param values The iterable collection to fill this Collection with
        """
        self.init_values(values)
        super(Collection, self).__init__(**kwargs)

    def __iter__(self):
        for x in self.values:
            yield x

    def __eq__(self, other):
        return self.itemtype == other.itemtype and self.values == other.values

    def __ne__(self, other):
        return not self.__eq__(other)

    def __len__(self):
        return len(self.values)

    def init_values(self, values):
        raise Exception("init_values must be overridden by a subclass")

    def itertuples(self):
        """Iterate over the items in the collection; return (k, v) where k is
        the key, index etc into the collection (or potentially the value
        itself, for sets)"""
        pass

    def walk(self, fs=None):
        if fs is None:
            from normalize.selector import FieldSelector
            fs = FieldSelector([])
        for x in super(Collection, self).walk(fs):
            yield x
        for key, item in self.itertuples():
            key_fs = fs + [key]
            yield (key_fs, None, self, item)
            if isinstance(item, Record):
                for x in item.walk(key_fs):
                    yield x


class KeyedCollection(Collection):
    def __getitem__(self, item):
        return self.values[item]


class DictCollection(KeyedCollection):
    suffix = "Map"

    def init_values(self, values):
        self.values = dict()
        if values:
            for k, v in values.iteritems():
                # XXX - is a coerce here sensible?
                self.values[k] = (v if isinstance(v, self.itemtype) else
                                  self.itemtype(v))

    def itertuples(self):
        return self.values.iteritems()


class ListCollection(KeyedCollection):
    suffix = "List"

    def init_values(self, values):
        self.values = list()
        if values:
            for k in values:
                self.values.append(k if isinstance(k, self.itemtype) else
                                   self.itemtype(k))

    def append(self, item):
        self.values.append(item)

    def itertuples(self):
        for i in range(0, len(self.values)):
            yield (i, self.values[i])

    def __str__(self):
        return "<%s: %d item(s)>" % (
            type(self).__name__, len(self.values)
        )

    def __repr__(self):
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
        return GENERIC_TYPES[self.typekey](values)


class Generic(Collection):
    """A mix-in to mark collection types which are (for example) collections of
    things."""
    def __reduce__(self):
        """helper method for pickling"""
        return (_GenericPickler(type(self).generic_key), (self.values,))


def make_generic(of, coll):
    assert(issubclass(coll, Collection))
    key = (coll.__name__, "%s.%s" % (of.__module__, of.__name__))
    if key in GENERIC_TYPES:
        if GENERIC_TYPES[key].itemtype != of:
            raise Exception(
                "Duplicate ListProperties of the same class name defined "
                "in the same module.  I'm sorry Dave, I'm afraid I can't "
                "let you do that."
            )
    else:
        # oh, we get to name it?  Goodie!
        generic_name = "%s%s" % (of.__name__, coll.suffix)
        GENERIC_TYPES[key] = type(
            generic_name, (coll, Generic), dict(itemtype=of, generic_key=key)
        )
    return GENERIC_TYPES[key]
