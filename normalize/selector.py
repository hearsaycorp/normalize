import collections
import functools
import re


class FieldSelectorException(Exception):
    pass


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
                sub_field_selector = FieldSelector(self.selectors[i + 1:])
                return [sub_field_selector.get(r) for r in record]
            elif isinstance(selector, (int, long)):
                try:
                    record = record[selector]
                except LookupError:
                    raise FieldSelectorException(
                        "Could not find Record specified by index: %s." %
                        selector
                    )
            else:
                if not hasattr(record, selector):
                    raise FieldSelectorException(
                        "Could not find Record specified by property "
                        "name: %s." % selector
                    )
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
            sub_selector = FieldSelector(self.selectors[1:])
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
                sub_field_selector = FieldSelector(self.selectors[i + 1:])
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
        FieldSelector([self.selectors[-1]]).put(record, value)
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
            return FieldSelector(self.selectors + [other])
        elif isinstance(other, collections.Iterable):
            return FieldSelector(self.selectors + list(other))
        elif isinstance(other, FieldSelector):
            return FieldSelector(self).extend(other)
        else:
            raise TypeError(
                "Cannot add a %s to a FieldSelector" % type(other).__name__
            )

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
