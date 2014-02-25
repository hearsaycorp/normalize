
from __future__ import absolute_import

import collections
import re
import unicodedata

from richenum import OrderedRichEnum
from richenum import OrderedRichEnumValue

from normalize.property import SafeProperty
from normalize.coll import Collection
from normalize.record import Record
from normalize.selector import FieldSelector


class DiffTypes(OrderedRichEnum):
    """
    An "enum" to represent types of diffs
    """
    NO_CHANGE = OrderedRichEnumValue(1, "none", "UNCHANGED")
    ADDED = OrderedRichEnumValue(2, "added", "ADDED")
    REMOVED = OrderedRichEnumValue(3, "removed", "REMOVED")
    MODIFIED = OrderedRichEnumValue(4, "modified", "MODIFIED")


def coerce_diff(dt):
    if not isinstance(dt, OrderedRichEnumValue):
        dt = DiffTypes.from_canonical(dt)
    return dt.index


class DiffInfo(Record):
    """
    Container for storing diff information that can be used to reconstruct the
    values diffed.
    """
    diff_type = SafeProperty(
        check=DiffTypes.from_index, coerce=coerce_diff, isa=int,
    )
    base = SafeProperty(isa=FieldSelector)
    other = SafeProperty(isa=FieldSelector)

    def __init__(self, *args, **kwargs):
        super(DiffInfo, self).__init__(*args, **kwargs)
        if not (hasattr(self, "base") or hasattr(self, "other")):
            raise Exception("DiffInfo must have a FieldSelector")

    def __str__(self):
        if hasattr(self, "base"):
            if hasattr(self, "other") and self.base.path != self.other.path:
                pathinfo = "(%s/%s)" % (self.base.path, self.other.path)
            else:
                pathinfo = self.base.path
        else:
            pathinfo = self.other.path
        difftype = DiffTypes.from_index(self.diff_type).display_name
        return "<DiffInfo: %s %s>" % (difftype, pathinfo)


class DiffOptions(object):
    """Optional data structure to pass diff options down"""
    def __init__(self, ignore_ws=True, ignore_case=False,
                 unicode_normal=True, unchanged=False):
        self.ignore_ws = ignore_ws
        self.ignore_case = ignore_case
        self.unicode_normal = unicode_normal
        self.unchanged = unchanged

    def items_equal(self, a, b):
        return self.normalize_val(a) == self.normalize_val(b)

    def normalize_whitespace(self, value):
        if isinstance(value, unicode):
            return u" ".join(
                x for x in re.split(r'\s+', value, flags=re.UNICODE) if
                len(x)
            )
        else:
            return " ".join(value.split())

    def normalize_unf(self, value):
        if isinstance(value, unicode):
            return unicodedata.normalize('NFC', value)
        else:
            return value

    def normalize_case(self, value):
        # FIXME: this will do the wrong thing for letters in some languages, eg
        # Greek, Turkish.  Correct, locale-dependent unicode case folding is
        # left as an exercise for a subclass.
        return value.upper()

    def normalize_val(self, value):
        if isinstance(value, basestring):
            if self.ignore_ws:
                value = self.normalize_whitespace(value)
            if self.ignore_case:
                value = self.normalize_case(value)
            if self.unicode_normal:
                value = self.normalize_unf(value)
        return value

    def record_id(self, record):
        return record.__pk__


def compare_record_iter(a, b, fs_a=None, fs_b=None, options=None):
    if type(a) != type(b):
        # TODO: no clear, obvious behavior here; but could define it later
        raise TypeError(
            "cannot compare %s with %s" % (type(a).__name__, type(b).__name__)
        )

    if fs_a is None:
        fs_a = FieldSelector(tuple())
        fs_b = FieldSelector(tuple())
    if not options:
        options = DiffOptions()

    properties = type(a).properties
    for propname in sorted(properties):

        prop = properties[propname]
        if prop.extraneous:
            continue

        propval_a = getattr(a, propname, None)
        propval_b = getattr(b, propname, None)

        if propval_a is None and propval_b is None:
            continue
        elif propval_a is None and propval_b is not None:
            yield DiffInfo(
                diff_type=DiffTypes.ADDED,
                other=fs_b + [propname],
            )
        elif propval_b is None and propval_a is not None:
            yield DiffInfo(
                diff_type=DiffTypes.REMOVED,
                base=fs_a + [propname],
            )
        elif type(propval_a) == type(propval_b) and \
                isinstance(propval_a, COMPARABLE):
            for types, func in COMPARE_FUNCTIONS.iteritems():
                if isinstance(propval_a, types):
                    break
            for diff in func(
                propval_a, propval_b, fs_a + [propname], fs_b + [propname],
                options,
            ):
                yield diff
        elif not options.items_equal(propval_a, propval_b):
            yield DiffInfo(
                diff_type=DiffTypes.MODIFIED,
                base=fs_a + [propname],
                other=fs_b + [propname],
            )
        elif options.unchanged:
            yield DiffInfo(
                diff_type=DiffTypes.NO_CHANGE,
                base=fs_a + [propname],
                other=fs_b + [propname],
            )


# There's a lot of repetition in the following code.  It could be served by one
# function instead of 3, which would be 3 times fewer places to have bugs, but
# it would probably also be more than 3 times as difficult to debug.


def compare_collection_iter(propval_a, propval_b, fs_a=None, fs_b=None,
                            options=None):
    if fs_a is None:
        fs_a = FieldSelector(tuple())
        fs_b = FieldSelector(tuple())
    if options is None:
        options = DiffOptions()

    propvals = dict(a=propval_a, b=propval_b)
    values = dict()
    rev_keys = dict()
    compare_values = None

    for x in "a", "b":
        propval_x = propvals[x]
        vals = values[x] = set()
        rev_key = rev_keys[x] = dict()

        seen = collections.Counter()

        for k, v in propval_x.itertuples():
            pk = options.record_id(v)
            if compare_values is None:
                compare_values = isinstance(pk, tuple)
            vals.add((pk, seen[pk]))
            rev_key[(pk, seen[pk])] = k
            seen[pk] += 1

    removed = values['a'] - values['b']
    added = values['b'] - values['a']

    if options.unchanged:
        unchanged = values['a'] & values['b']
        for pk, seq in unchanged:
            a_key = rev_keys['a'][pk, seq]
            b_key = rev_keys['b'][pk, seq]
            yield DiffInfo(
                diff_type=DiffTypes.NO_CHANGE,
                base=fs_a + [a_key],
                other=fs_b + [b_key],
            )

    for pk, seq in removed:
        a_key = rev_keys['a'][pk, seq]
        selector = fs_a + [a_key]
        yield DiffInfo(
            diff_type=DiffTypes.REMOVED,
            base=selector,
        )

    for pk, seq in added:
        b_key = rev_keys['b'][pk, seq]
        selector = fs_b + [b_key]
        yield DiffInfo(
            diff_type=DiffTypes.ADDED,
            other=selector,
        )

    if compare_values:
        for pk, seq in values['a'].intersection(values['b']):
            a_key = rev_keys['a'][pk, seq]
            b_key = rev_keys['b'][pk, seq]
            selector_a = fs_a + a_key
            selector_b = fs_b + b_key
            for diff in compare_record_iter(
                propval_a[a_key], propval_b[b_key],
                selector_a, selector_b, options,
            ):
                yield diff


def compare_list_iter(propval_a, propval_b, fs_a=None, fs_b=None,
                      options=None):
    if fs_a is None:
        fs_a = FieldSelector(tuple())
        fs_b = FieldSelector(tuple())
    if not options:
        options = DiffOptions()
    propvals = dict(a=propval_a, b=propval_b)
    values = dict()
    indices = dict()
    for x in "a", "b":
        propval_x = propvals[x]
        vals = values[x] = set()
        rev_key = indices[x] = dict()
        seen = collections.Counter()
        i = 0
        for v in propval_x:
            v = options.normalize_val(v)
            vals.add((v, seen[v]))
            rev_key[(v, seen[v])] = i
            seen[v] += 1
            i += 1

    removed = values['a'] - values['b']
    added = values['b'] - values['a']

    if options.unchanged:
        unchanged = values['a'] & values['b']
        for v, seq in unchanged:
            a_idx = indices['a'][v, seq]
            b_idx = indices['b'][v, seq]
            yield DiffInfo(
                diff_type=DiffTypes.NO_CHANGE,
                base=fs_a + [a_idx],
                other=fs_b + [b_idx],
            )

    for v, seq in removed:
        a_key = indices['a'][v, seq]
        selector = fs_a + [a_key]
        yield DiffInfo(
            diff_type=DiffTypes.REMOVED,
            base=selector,
        )

    for v, seq in added:
        b_key = indices['b'][v, seq]
        selector = fs_b + [b_key]
        yield DiffInfo(
            diff_type=DiffTypes.ADDED,
            other=selector,
        )


def compare_dict_iter(propval_a, propval_b, fs_a=None, fs_b=None,
                      options=None):
    if fs_a is None:
        fs_a = FieldSelector(tuple())
        fs_b = FieldSelector(tuple())
    if not options:
        options = DiffOptions()
    propvals = dict(a=propval_a, b=propval_b)
    values = dict()
    rev_keys = dict()
    for x in "a", "b":
        propval_x = propvals[x]
        vals = values[x] = set()
        rev_key = rev_keys[x] = dict()
        seen = collections.Counter()
        for k, v in propval_x.iteritems():
            v = options.normalize_val(v)
            vals.add((v, seen[v]))
            rev_key[(v, seen[v])] = k
            seen[v] += 1

    removed = values['a'] - values['b']
    added = values['b'] - values['a']

    if options.unchanged:
        unchanged = values['a'] & values['b']
        for v, seq in unchanged:
            a_key = rev_keys['a'][v, seq]
            b_key = rev_keys['b'][v, seq]
            yield DiffInfo(
                diff_type=DiffTypes.NO_CHANGE,
                base=fs_a + [a_key],
                other=fs_b + [b_key],
            )

    for v, seq in removed:
        a_key = rev_keys['a'][v, seq]
        selector = fs_a + [a_key]
        yield DiffInfo(
            diff_type=DiffTypes.REMOVED,
            base=selector,
        )

    for v, seq in added:
        b_key = rev_keys['b'][v, seq]
        selector = fs_b + [b_key]
        yield DiffInfo(
            diff_type=DiffTypes.ADDED,
            other=selector,
        )


COMPARE_FUNCTIONS = {
    list: compare_list_iter,
    tuple: compare_list_iter,
    dict: compare_dict_iter,
    Collection: compare_collection_iter,
    Record: compare_record_iter,
}


COMPARABLE = tuple(COMPARE_FUNCTIONS)
