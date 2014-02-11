
from __future__ import absolute_import

import collections

from normalize.property import SafeProperty
from normalize.coll import Collection
from normalize.record import Record
from normalize.selector import FieldSelector


class DiffTypes(object):
    """
    An "enum" to represent types of diffs
    """
    NO_CHANGE = 1
    ADDED = 2
    REMOVED = 3
    MODIFIED = 4

    reverse = ["ENULL", "UNCHANGED", "ADDED", "REMOVED", "MODIFIED"]


class DiffInfo(Record):
    """
    Container for storing diff information that can be used to reconstruct the
    values diffed.
    """
    diff_type = SafeProperty(isa=int)
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
        difftype = DiffTypes.reverse[self.diff_type]
        return "<DiffInfo: %s %s>" % (difftype, pathinfo)


def compare_record_iter(a, b, fs_a=None, fs_b=None):
    if type(a) != type(b):
        # TODO: no clear, obvious behavior here; but could define it later
        raise TypeError(
            "cannot compare %s with %s" % (type(a).__name__, type(b).__name__)
        )

    if fs_a is None:
        fs_a = FieldSelector(tuple())
        fs_b = FieldSelector(tuple())

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
                propval_a, propval_b, fs_a + [propname], fs_b + [propname]
            ):
                yield diff
        elif propval_a != propval_b:
            yield DiffInfo(
                diff_type=DiffTypes.MODIFIED,
                base=fs_a + [propname],
                other=fs_b + [propname],
            )


# There's a lot of repetition in the following code.  It could be served by one
# function instead of 3, which would be 3 times fewer places to have bugs, but
# it would probably also be more than 3 times as difficult to debug.


def compare_collection_iter(propval_a, propval_b, fs_a=None, fs_b=None):
    if fs_a is None:
        fs_a = FieldSelector(tuple())
        fs_b = FieldSelector(tuple())

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
            pk = v.__pk__
            if compare_values is None:
                compare_values = isinstance(pk, tuple)
            vals.add((pk, seen[pk]))
            rev_key[(pk, seen[pk])] = k
            seen[pk] += 1

    removed = values['a'] - values['b']
    added = values['b'] - values['a']

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
                selector_a, selector_b,
            ):
                yield diff


def compare_list_iter(propval_a, propval_b, fs_a=None, fs_b=None):
    if fs_a is None:
        fs_a = FieldSelector(tuple())
        fs_b = FieldSelector(tuple())
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
            vals.add((v, seen[v]))
            rev_key[(v, seen[v])] = i
            seen[v] += 1
            i += 1

    removed = values['a'] - values['b']
    added = values['b'] - values['a']

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


def compare_dict_iter(propval_a, propval_b, fs_a=None, fs_b=None):
    if fs_a is None:
        fs_a = FieldSelector(tuple())
        fs_b = FieldSelector(tuple())
    propvals = dict(a=propval_a, b=propval_b)
    values = dict()
    rev_keys = dict()
    for x in "a", "b":
        propval_x = propvals[x]
        vals = values[x] = set()
        rev_key = rev_keys[x] = dict()
        seen = collections.Counter()
        for k, v in propval_x.iteritems():
            vals.add((v, seen[v]))
            rev_key[(v, seen[v])] = k
            seen[v] += 1

    removed = values['a'] - values['b']
    added = values['b'] - values['a']

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
