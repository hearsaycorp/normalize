
import normalize


EMPTY_VALS = dict()


def placeholder(type_):
    """Returns the EmptyVal instance for the given type"""
    typetuple = type_ if isinstance(type_, tuple) else (type_,)
    if any in typetuple:
        typetuple = any
    if typetuple not in EMPTY_VALS:
        EMPTY_VALS[typetuple] = EmptyVal(typetuple)
    return EMPTY_VALS[typetuple]


def itertypes(iterable):
    """Iterates over an iterable containing either type objects or tuples of
    type objects and yields once for every type object found."""
    seen = set()
    for entry in iterable:
        if isinstance(entry, tuple):
            for type_ in entry:
                if type_ not in seen:
                    seen.add(type_)
                    yield type_
        else:
            if entry not in seen:
                seen.add(entry)
                yield entry


class EmptyVal(object):
    """Empty Value placeholder for a given tuple of types.  This object's
    ``__nonzero__`` always returns ``False``, and it knows how to infer types
    as its attributes are accessed and/or lists are de-referenced: so long as
    there are type hints in the places normalize puts them.

    Each set of types gets a single, persistent ``EmptyVal`` object.  The
    special ``EmptyVal(any)`` is used when types cannot be inferred, and never
    raises any errors: it just returns itself when invoked etc.

    If types can be inferred, then exceptions are raised when invalid
    attributes are accessed, or a type which does not implement ``__getitem__``
    is dereferenced, or a type which does not supply ``__call__`` is invoked.

    This function will raise exceptions badly when you try to access variables
    which are only available in a subclass of the declared class on the type
    hint, or when a property attribute is set by a method (eg, ``__init__``)
    rather than declared on the class.
    """
    def __init__(self, typetuple):
        self._typetuple = typetuple
        self._attrs = {}
        self._member_type = None

    def __getattr__(self, attr_name):
        if self._typetuple is any:
            return self
        if attr_name not in self._attrs:
            attrs_found = []
            for type_ in self._typetuple:
                prop = getattr(type_, attr_name, None)
                if prop is None:
                    if '__getattr__' in type_.__dict__:
                        attrs_found.append(None)
                else:
                    attrs_found.append(prop)

            if not attrs_found:
                raise self._exc(
                    "NoSuchAttribute",
                    attribute=attr_name,
                )
            elif attrs_found:
                self._attrs[attr_name] = placeholder(
                    tuple(
                        itertypes(
                            getattr(attr, "valuetype", False) or any for
                            attr in attrs_found
                        )
                    )
                )
        return self._attrs[attr_name]

    def __setattr__(self, item, value):
        if item in ("_typetuple", "_attrs", "_member_type"):
            self.__dict__[item] = value
        else:
            raise self._exc("BadAssignment")

    def __setitem__(self, item, value):
        raise self._exc("BadAssignment")

    def __call__(self, *args, **kwargs):
        if self._typetuple is any:
            return self
        for type_ in self._typetuple:
            if type_.__dict__.get("__call__", False):
                return placeholder(any)
        raise self._exc('NotCallable')

    def __getitem__(self, item):
        if self._typetuple is any:
            return self
        if isinstance(item, slice):
            return self
        elif self._member_type is None:
            coll_types = []
            for type_ in self._typetuple:
                is_coll = issubclass(type_, normalize.coll.Collection)
                if is_coll:
                    coll_types.append(type_.itemtype)
                elif '__getitem__' in type_.__dict__:
                    coll_types.append(any)

            if not coll_types:
                raise self._exc("NotSubscriptable")
            elif coll_types:
                self._member_type = placeholder(tuple(itertypes(coll_types)))
            else:
                self._member_type = placeholder(any)
        return self._member_type

    def __nonzero__(self):
        return False

    def _typelist(self):
        return "any" if self._typetuple is any else ",".join(
            str(t.__name__) for t in self._typetuple if isinstance(t, type)
        )

    def __repr__(self):
        return "normalize.empty.placeholder(%s)" % self._typelist()

    def __str__(self):
        return "False(%s)" % self._typelist()

    def _exc(self, which, **kwargs):
        return getattr(normalize.exc, which)(
            typenames=self._typelist(),
            **kwargs)
