
from __future__ import absolute_import

import abc

"""This class contains container classes which can act like collections but
conform to this package's metaclass API"""


class Collection(object):
    __metaclass__ = abc.ABCMeta

    @abc.abstractproperty
    def itemtype(self):
        pass

    @property
    def record_cls(self):
        return self.itemtype

    """This is the base class for Record property values which contain
    iterable sets of values with a particular common type."""
    def __init__(self, values=None):
        """
        @param of The Record type of members in this collection
        @param values The values of this collection.
        """
        self.init_values(values)

    def __iter__(self):
        for x in self.values:
            yield x

    def __eq__(self, other):
        return self.itemtype == other.itemtype and self.values == other.values

    def __ne__(self, other):
        return not self.__eq__(other)

    def __len__(self):
        return len(self.values)

    @abc.abstractmethod
    def init_values(self, values):
        raise Exception("init_values must be overridden by a subclass")


class KeyedCollection(Collection):
    def __getitem__(self, item):
        return self.values[item]


class DictCollection(KeyedCollection):
    def init_values(self, values):
        self.values = dict()
        if values:
            for k, v in values.iteritems():
                # XXX - is a coerce here sensible?
                self.values[k] = (v if isinstance(v, self.itemtype) else
                                  self.itemtype(v))


class ListCollection(KeyedCollection):
    def init_values(self, values):
        self.values = list()
        if values:
            for k in values:
                self.values.append(k if isinstance(k, self.itemtype) else
                                   self.itemtype(k))

    def append(self, item):
        self.values.append(item)


GENERIC_TYPES = dict()


class _GenericPickler(object):
    """'pickle' doesn't like pickling classes which are dynamically created.
    This object is used instead, to keep pickle happy.
    """
    def __init__(self, typename):
        self.typename = typename

    def __call__(self, values):
        return GENERIC_TYPES[self.typename](values)


class Generic(Collection):
    """A mix-in to mark collection types which are (for example) collections of
    things."""
    def __reduce__(self):
        """helper method for pickling"""
        return (_GenericPickler(type(self).__name__), (self.values,))


def make_generic(of, coll):
    assert(issubclass(coll, Collection))
    generic_name = "%s[%s]" % (coll.__name__, of.__name__)
    if generic_name not in GENERIC_TYPES:
        GENERIC_TYPES[generic_name] = type(
            generic_name, (coll, Generic), dict(itemtype=of)
        )
    return GENERIC_TYPES[generic_name]
