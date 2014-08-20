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

    This is modeled as a list of either attribute names or collection indices,
    where:

    * A string specifies an attribute of an object (or a dictionary key)
    * An integer specifies an index into a collection.
    * 'None' specifies the full collection.
    """
    def __init__(self, expr=None):
        """Initializer for FieldSelector instances.

        args:

            ``expr=``\ *FieldSelector*\ \|\ *<iterable>*
                Starting expression for the selector; can copy an existing
                FieldSelector or instantiate one from an iterable list of
                attribute names/indices
        """
        self.selectors = []

        if expr:
            if hasattr(expr, "selectors"):
                expr_selectors = expr.selectors
            else:
                expr_selectors = list(expr)

            # Validate the selector
            if any(
                e for e in expr_selectors if not (
                    isinstance(e, basestring) or
                    isinstance(e, (int, long)) or e is None
                )
            ):
                raise ValueError(
                    "FieldSelectors can only contain ints/longs, "
                    "strings, and None"
                )
            # shallow copying via slice is faster than copy.copy()
            self.selectors = expr_selectors[:]

    def add_property(self, prop):
        """Extends the selector, adding a new attribute property lookup at the
        end, specified by name."""
        if not isinstance(prop, basestring):
            raise ValueError(
                "properties must be specified by their string name"
            )
        self.selectors.append(prop)

    def add_index(self, index):
        """Extends the selector, adding a new indexed collection lookup at the
        end."""
        if not isinstance(index, (int, long)):
            raise ValueError("index must be an int or a long")
        self.selectors.append(index)

    def add_full_collection(self):
        """Extends the selector, making it refer to *all* items in the
        collection at this point."""
        self.selectors.append(None)

    def extend(self, other):
        """
        Extends this field selector with another FieldSelector, combining them
        to one longer field selector.
        """
        self.selectors.extend(other.selectors)
        return self  # Useful for chaining

    def __getnewargs__(self):
        """
        The pickle protocol is supported on this type.
        """
        return (tuple(self.selectors),)

    def get(self, record):
        """
        Evaluate the FieldSelector's path to get a specific attribute (or
        collection of attributes, if there is a ``None`` in the selector
        expression) from the passed record.

        If there is a problem, this method will typically raise
        :py:class:`FieldSelectorException`.

        ::

           record.foo = "bar"
           field_selector = FieldSelector(["foo"])
           print field_selector.get(record)  # "bar"
        """
        i = 0
        for selector in self.selectors:
            if selector is None:
                sub_field_selector = type(self)(self.selectors[i + 1:])
                return [sub_field_selector.get(r) for r in record]
            elif isinstance(selector, (int, long)):
                try:
                    record = record[selector]
                except IndexError:
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

        ::

           field_selector.put(record, "baz")
           print record.foo  # "baz"
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

        ::

           field_selector = FieldSelector(["stuff", 0, "name"])
           obj = SomeObject()
           field_selector.post(obj, "Bob")
           print obj.stuff[0].name  # "Bob"
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
        """Implemented; field selectors must have identical paths to compare
        equal."""
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
        """Ordering field selectors makes sure that all integer-indexed
        selectors are incrementing.  This is mainly needed for
        :py:meth:`FieldSelector.post`, which will only auto-extend collections
        items at the end."""
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
        """Returns a compact representation of the field selector, shown as a
        python expression."""
        return "<%s: %s>" % (self.__class__.__name__, self.path)

    def __repr__(self):
        """Returns a evaluable representation of a field selector."""
        return "%s(%r)" % (self.__class__.__name__, self.selectors)

    def __add__(self, other):
        """Creates a new FieldSelector, with the two attribute/index expression
        lists concatenated.  Like :py:meth:`extend` but creates a new
        ``FieldSelector``.

        ::

            fs = FieldSelector(["foo"])
            bar = FieldSelector(["bar"])

            print fs + bar  # <FieldSelector: .foo.bar>
            print fs + [0]  # <FieldSelector: .foo[0]>
        """
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
        """Returns the number of elements in the field selector expression."""
        return len(self.selectors)

    def __getitem__(self, key):
        """Indexing can be used to return a particular item from the selector
        expression, and slicing can be used to make a new FieldSelector which
        has a shorter expression.  For instance, to trim the last:

        ::

           trimmed_fs = field_selector[:-1]
        """
        if isinstance(key, slice):
            return type(self)(self.selectors[key])
        else:
            return self.selectors[key]

    def startswith(self, key_or_fs):
        """Can be used to assert how the field selector begins.

        args:

            ``key_or_fs=``\ *FieldSelector*\ \|\ *<attribute-or-index>*

                If the argument is another FieldSelector (or a tuple/list), it
                checks that the invocant's first selector expression components
                match the components in the selector passed.

                If the argument is a valid index/key or attribute name, it will
                check that the first member in the expression is the same as
                that passed.
        """
        if isinstance(key_or_fs, (FieldSelector, list, tuple)):
            return all(
                key_or_fs[i] == self.selectors[i] for i in range(
                    0, len(key_or_fs),
                )
            )
        else:
            return self.selectors[0] == key_or_fs

    @property
    def path(self):
        """This property returns something that looks a bit like a python
        representation of the implied expression.

        ::

            foo = FieldSelector(["foo", 2, "b ar", None, "baz"])
            print foo.path  # foo[2]['b ar'][*].baz
        """
        return "".join(_fmt_selector_path(x) for x in self.selectors)


def _fmt_selector_path(selector):
    if isinstance(selector, (int, long)):
        return "[%d]" % selector
    elif selector is None:
        return "[*]"
    elif re.search(r'[^a-z_]', selector):
        return "['%s']" % selector.replace("'", "\\'")
    else:
        return ".%s" % selector


def _fmt_mfs_path(head, tail):
    return (
        "%s%s" % (_fmt_selector_path(head), tail.path) if
        isinstance(tail, MultiFieldSelector) else
        _fmt_selector_path(head)
    )


class MultiFieldSelector(object):
    """Version of a FieldSelector which stores multiple FieldSelectors combined
    into a single tree structure."""

    FieldSelector = FieldSelector

    def __init__(self, *others):
        """Returns a MultiFieldSelector based on combining the passed-in
        FieldSelector and MultiFieldSelector objects.

        args:

            ``*others=``\ *FieldSelector*\ \|\ *iterable*

                Each argument is interpreted as either a FieldSelector, or a
                FieldSelector constructor.
        """
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
        """Stringification of a MultiFieldSelector shows just the keys in the
        top level, and an indication of whether a sub-key is filtered.

        ::

           >>> mfs = MultiFieldSelector(["a", "b"], ["a", "d"], ["c"])
           >>> str(mfs)
           '<MultiFieldSelector: a.b|a.d|c>
           >>>
        """
        return "<MultiFieldSelector: %s>" % self.path

    @property
    def path(self):
        if len(self.heads) == 1:
            return _fmt_mfs_path(self.heads.keys()[0], self.heads.values()[0])
        else:
            return "(" + "|".join(
                _fmt_mfs_path(k, v) for (k, v) in self.heads.items()
            ) + ")"

    def __nonzero__(self):
        return bool(len(self.heads))

    def __iter__(self):
        """Generator for all FieldSelectors this MultiFieldSelector
        implicitly contains.

        ::

            >>> mfs = MultiFieldSelector(["a", "b"], ["a", "d"], ["c"])
            >>> for x in mfs:
            ...     print x
            ...
            <FieldSelector: .a.b>
            <FieldSelector: .a.d>
            <FieldSelector: .c>
            >>>
        """
        for head, tail in self.heads.iteritems():
            head_selector = self.FieldSelector((head,))
            if tail is all:
                if head is None:
                    yield self.FieldSelector(())
                yield head_selector
            else:
                for x in tail:
                    yield head_selector + x

    def __getitem__(self, index):
        """Returns the MultiFieldSelector that applies to the specified
        field/key/index.

        ::

            >>> mfs = MultiFieldSelector(["a", "b"], ["a", "d"], ["c"])
            >>> mfs["a"]
            MultiFieldSelector(['b'], ['d'])
            >>>
        """
        if isinstance(index, (FieldSelector, tuple, list)):
            if len(index) == 0:
                return self
            if self.has_none:
                pass
            elif len(index) == 1:
                index = index[0]
            else:
                return self.heads[index[0]][index[1:]]
        if index is any:
            assert len(self.heads) <= 1, "ambigious fetch of 'any'"
            if len(self.heads) == 1:
                index = self.heads.keys()[0]
            else:
                return self

        tail = self.heads[None] if self.has_none else self.heads[index]
        return type(self)([None]) if tail == all else tail

    def __contains__(self, index):
        """Checks to see whether the given item matches the MultiFieldSelector.

        ::

            >>> mfs = MultiFieldSelector(["a", "b"], ["a", "d"], ["c"])
            >>> "a" in mfs
            True
            >>> "b" in mfs
            False
            >>> FieldSelector(["a"]) in mfs
            True
            >>> FieldSelector(["a", "d"]) in mfs
            True
            >>> FieldSelector(["a", "e"]) in mfs
            False
            >>>
        """
        if isinstance(index, (FieldSelector, tuple, list)) and \
                len(index) == 1:
            index = index[0]

        if isinstance(index, (basestring, types.IntType, types.NoneType)):
            return self.has_none or index in self.heads
        elif index is any:
            return True if len(self.heads) else False
        elif len(index) == 0:
            return True
        else:
            head_key = None if self.has_none else index[0]
            return (
                head_key in self.heads and
                index[1:] in self[head_key]
            )

    def __repr__(self):
        """Implemented as per SPECIALMETHODS recommendation to return a full
        python source to reconstruct:

        ::

            >>> mfs = MultiFieldSelector(["a", "b"], ["a", "d"], ["c"])
            >>> mfs
            MultiFieldSelector(['a', 'b'], ['a', 'd'], ['c'])
            >>>
        """
        return "MultiFieldSelector%r" % (tuple(x.selectors for x in self),)

    def _get(self, obj, tail):
        if tail is all:
            return copy.deepcopy(obj)
        else:
            return tail.get(obj)

    def get(self, obj):
        """Creates a copy of the passed object which only contains the parts
        which are pointed to by one of the FieldSelectors that were used to
        construct the MultiFieldSelector.  Can be used to produce 'filtered'
        versions of objects.
        """
        ctor = type(obj)
        if isinstance(obj, (list, ListCollection)):
            if self.has_string:
                raise TypeError(
                    "MultiFieldSelector has string in list collection context"
                )
            if self.has_none:
                tail = self.heads[None]
                vals = list(self._get(x, tail) for x in obj)
            else:
                vals = list(
                    self._get(obj[head], tail) for head, tail in
                    self.heads.iteritems()
                )
            if isinstance(obj, ListCollection):
                return ctor(values=vals)
            else:
                return vals
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
