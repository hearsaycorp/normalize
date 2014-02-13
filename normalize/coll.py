
from __future__ import absolute_import

import abc

"""This class contains container classes which can act like collections but
conform to this package's metaclass API"""


class Collection(object):
    """This is the base class for Record property values which contain
    iterable sets of values with a particular common type."""
    def __init__(self, of, values):
        """
        @param of The Record type of members in this collection
        @param values The values of this collection.
        """
        self.itemtype = of  # XXX - type objects inside instances
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
        for k, v in values.iteritems():
            # XXX - is a coerce here sensible?
            self.values[k] = (v if isinstance(v, self.itemtype) else
                              self.itemtype(v))


class ListCollection(KeyedCollection):
    def init_values(self, values):
        self.values = list()
        for k in values:
            self.values.append(k if isinstance(k, self.itemtype) else
                               self.itemtype(k))
