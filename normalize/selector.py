from __future__ import absolute_import

import collections
import copy
import functools
import re
import types

from normalize.coll import ListCollection
from normalize.exc import FieldSelectorAttributeError
from normalize.exc import FieldSelectorException
from normalize.exc import FieldSelectorKeyError


@functools.total_ordering
class FieldSelector(object):
    """
    A way to refer to fields/record/properties within a data structure.

    Properties/Indicies are tracked as elements in a list:
    * A string specifies an attribute of an object.
    * An integer specifies an index into a collection.
    * 'None' specifies the full collection.
    """
    def __init__(self, other=None):
        """
        @param other Provides a way to copy an existing FieldSelector or
                     instantiate one from an iterable.
        """
        self.selectors = []

        if other:
            other_selectors = []
            if hasattr(other, "selectors"):
                other_selectors = other.selectors
            else:
                other_selectors = list(other)

            # Validate the selector
            if any(
                e for e in other_selectors if not (
                    isinstance(e, basestring) or
                    isinstance(e, (int, long)) or e is None
                )
            ):
                raise ValueError(
                    "FieldSelectors can only contain ints/longs, "
                    "strings, and None"
                )
            # shallow copying via slice is faster than copy.copy()
            self.selectors = other_selectors[:]

    def add_property(self, prop):
        if not isinstance(prop, basestring):
            raise ValueError(
                "properties must be specified by their string name"
            )
        self.selectors.append(prop)

    def add_index(self, index):
        if not isinstance(index, (int, long)):
            raise ValueError("index must be an int or a long")
        self.selectors.append(index)

    def add_full_collection(self):
        self.selectors.append(None)

    def extend(self, other):
        """
        Extends this field selector with another FieldSelector
        """
        self.selectors.extend(other.selectors)
        return self  # Useful for chaining

    def __getnewargs__(self):
        """
        Serialize as a list.
        """
        return (tuple(self.selectors),)

    def get(self, record):
        """
        Applies this FieldSelector to the specified Record to get the
        field/property/record specified by this FieldSelector
        """
        i = 0
        for selector in self.selectors:
            if selector is None:
                sub_field_selector = type(self)(self.selectors[i + 1:])
                return [sub_field_selector.get(r) for r in record]
            elif isinstance(selector, (int, long)):
                try:
                    record = record[selector]
                except LookupError:
                    raise FieldSelectorKeyError(key=selector)
            else:
                if not hasattr(record, selector):
                    raise FieldSelectorAttributeError(name=selector)
                record = getattr(record, selector)
            i = i + 1
        return record

    def put(self, record, value):
        """
        Sets the field referenced by this field selector for the given Record
        with the given value.

        If put() is going to be called on the same Record from
        multiple/different FieldSelectors, then put() needs to called in
        the sorted order of the FieldSelectors.
        """
        if len(self.selectors) == 1:
            selector = self.selectors[0]
            if selector is None:
                record[:] = value
            elif isinstance(selector, (int, long)):
                try:
                    record[selector] = value
                except LookupError:
                    raise FieldSelectorException(
                        "Could not find Record specified by index: %s." %
                        selector
                    )
            else:
                try:
                    setattr(record, selector, value)
                except AttributeError:
                    raise FieldSelectorException(
                        "Could not find Record specified by property "
                        "name: %s." % selector
                    )
        else:
            selector = self.selectors[0]
            sub_selector = type(self)(self.selectors[1:])
            if selector is None:
                for x in record:
                    sub_selector.put(x, value)
            else:
                if isinstance(selector, (int, long)):
                    try:
                        sub_record = record[selector]
                    except IndexError:
                        raise FieldSelectorException(
                            "Could not find Record specified by index: %s." %
                            selector
                        )
                else:
                    try:
                        sub_record = getattr(record, selector)
                    except AttributeError:
                        raise FieldSelectorException(
                            "Could not find Record specified by property "
                            "name: %s." % selector
                        )
                sub_selector.put(sub_record, value)

    def post(self, record, value):
        """auto-vivifying version of 'put'; if properties are not found along
        the path, attempts are made to set them to empty values.

        Returns the number of values set; may be 0 if there is 'None' in the
        selector and there were no existing items in that collection.
        """
        i = 0
        for selector in self.selectors[:-1]:
            if selector is None:
                sub_field_selector = type(self)(self.selectors[i + 1:])
                return sum(sub_field_selector.post(r) for r in record)
            elif isinstance(selector, (int, long)):
                try:
                    record = record[selector]
                except LookupError:
                    if len(record) != selector:
                        raise ValueError(
                            "FieldSelector set out of order: "
                            "[%d]" % selector
                        )
                    record.append(type(record).itemtype())
                    record = record[selector]
            else:
                if not hasattr(record, selector):
                    prop = type(record).properties[selector]
                    if not prop.valuetype:
                        raise FieldSelectorException(
                            "Must specify default= or isa= to auto-vivify "
                            "%s" % prop
                        )
                    setattr(record, selector, prop.valuetype())
                record = getattr(record, selector)
            i = i + 1
        type(self)([self.selectors[-1]]).put(record, value)
        return 1

    def __eq__(self, other):
        if not isinstance(other, FieldSelector):
            raise TypeError(
                "Cannot compare FieldSelector with %s" % type(other).__name__
            )
        return self.selectors == other.selectors

    def __ne__(self, other):
        """
        functools.total_ordering() currently doesn't take care of __ne__().
        Don't call other comparison methods directly to avoid infinite
        recursion.
        """
        return self.selectors != other.selectors

    def __lt__(self, other):
        end = len(self.selectors)
        if len(self.selectors) > len(other.selectors):
            end = len(other.selectors)
        for i in xrange(end):
            self_selector = self.selectors[i]
            other_selector = other.selectors[i]
            if self_selector == other_selector:
                continue
            if type(self_selector) != type(other_selector):
                raise TypeError(
                    "Cannot compare incompatible FieldSelectors. "
                    "Incompatibility detected at index: %s for selectors: "
                    "%s and %s" % (
                        i, self.selectors, other.selectors,
                    )
                )
            return self_selector < other_selector

        # Individual selectors compared at this point have been the
        # same. Fallback to length.
        return len(self.selectors) < len(other.selectors)

    def __str__(self):
        return "<%s: %s>" % (self.__class__.__name__, self.path)

    def __repr__(self):
        return "FieldSelector(%r)" % self.selectors

    def __add__(self, other):
        if isinstance(other, (basestring, int, long)):
            return type(self)(self.selectors + [other])
        elif isinstance(other, collections.Iterable):
            return type(self)(self.selectors + list(other))
        elif isinstance(other, FieldSelector):
            return type(self)(self).extend(other)
        else:
            raise TypeError(
                "Cannot add a %s to a FieldSelector" % type(other).__name__
            )

    def __len__(self):
        return len(self.selectors)

    def __getitem__(self, key):
        if isinstance(key, slice):
            return type(self)(self.selectors[key])
        else:
            return self.selectors[key]

    def startswith(self, key_or_fs):
        if isinstance(key_or_fs, FieldSelector):
            return all(
                key_or_fs[i] == self.selectors[i] for i in range(
                    0, len(key_or_fs),
                )
            )
        else:
            return self.selectors[0] == key_or_fs

    @property
    def path(self):
        selector_parts = []
        for selector in self.selectors:
            if isinstance(selector, (int, long)):
                selector_parts.append("[%d]" % selector)
            elif selector is None:
                selector_parts.append("[*]")
            elif re.search(r'[^a-z_]', selector):
                selector_parts.append("['%s']" % selector.replace("'", "\\'"))
            else:
                selector_parts.append(".%s" % selector)

        return "".join(selector_parts)


class MultiFieldSelector(object):
    FieldSelector = FieldSelector

    """Version of a FieldSelector which stores 'selectors' as a tree"""
    def __init__(self, *others):
        selectors = list()
        heads = collections.defaultdict(set)
        for other in others:
            if isinstance(other, MultiFieldSelector):
                for head, tail in other.heads.iteritems():
                    heads[head].add(tail)
            elif isinstance(other, FieldSelector):
                selectors.append(other)
            else:
                selectors.append(self.FieldSelector(other))

        for selector in selectors:
            chain = selector.selectors
            if chain:
                head = chain[0]
                tail = self.FieldSelector(chain[1:]) if len(chain) > 1 else all
                heads[head].add(tail)
            else:
                heads[None].add(all)

        self.heads = dict(
            (head, all if all in tail else MultiFieldSelector(*tail))
            for head, tail in heads.iteritems()
        ) if None not in heads or heads[None] is not all else {None: all}

        # sanity assertions follow
        head_types = set(type(x) for x in self.heads)
        self.has_int = int in head_types or long in head_types
        self.has_string = any(issubclass(x, basestring) for x in head_types)
        self.has_none = types.NoneType in head_types
        if self.has_none and (self.has_int or self.has_string):
            # this should be possible, but I'm punting on it for now
            raise ValueError(
                "MultiFieldSelector cannot yet specify a list and a hash/"
                "object at the same level: %r" % self.heads.keys()
            )

    def __str__(self):
        return "<MultiFieldSelector: %s>" % (
            ",".join(head if self.heads[tail] is all else "%s/..." % head for
                     head, tail in self.heads.iteritems)
        )

    def __iter__(self):
        """Generates FieldSelectors from this MultiFieldSelector"""
        for head, tail in self.heads.iteritems():
            head_selector = self.FieldSelector((head,))
            if tail is all:
                if head is None:
                    yield self.FieldSelector(())
                yield head_selector
            else:
                for x in tail:
                    yield head_selector + x

    def __repr__(self):
        return "MultiFieldSelector%r" % tuple(x.selectors for x in self)

    def _get(self, obj, tail):
        if tail is all:
            return copy.deepcopy(obj)
        else:
            return tail.get(obj)

    def get(self, obj):
        ctor = type(obj)
        if isinstance(obj, (list, ListCollection)):
            if self.has_string:
                raise TypeError(
                    "MultiFieldSelector has string in list collection context"
                )
            if self.has_none:
                tail = self.heads[None]
                return ctor(self._get(x, tail) for x in obj)
            else:
                return ctor(
                    self._get(obj[head], tail) for head, tail in
                    self.heads.iteritems()
                )
        elif isinstance(obj, dict):
            if self.has_none:
                tail = self.heads[None]
                return ctor(
                    (k, self._get(v, tail)) for k, v in obj.iteritems()
                )
            else:
                return ctor(
                    (head, self._get(obj[head], tail)) for head, tail in
                    self.heads.iteritems() if head in obj
                )
        else:
            if self.has_int or (self.has_none and self.heads[None] is not all):
                raise TypeError(
                    "MultiFieldSelector has %s in %s context" % (
                        "int" if self.has_int else "none", ctor.__name__
                    )
                )
            if self.has_none:
                return self._get(obj, all)
            else:
                kwargs = dict()
                for head, tail in self.heads.iteritems():
                    val = getattr(obj, head, None)
                    if val is not None:
                        kwargs[head] = self._get(val, tail)
                return ctor(**kwargs)
