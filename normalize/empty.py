
import normalize


EMPTY_VALS = dict()
        

def placeholder(type_):
    typetuple = type_ if isinstance(type_, tuple) else (type_,) 
    if any in typetuple:
        typetuple = any
    if typetuple not in EMPTY_VALS:
        EMPTY_VALS[typetuple] = EmptyVal(typetuple)
    return EMPTY_VALS[typetuple]


def itertypes(iterable):
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
    def __init__(self, typetuple):
        self._typetuple = typetuple
        self._attrs = {}
        self._member_type = None

    def __getattr__(self, attr_name):
        if self._typetuple is any:
            return self
        if attr_name not in self._attrs:
            attrs_found = []
            all_record = None
            for type_ in self._typetuple:
                is_record = issubclass(type_, normalize.record.Record)
                if is_record:
                    if all_record is None:
                        all_record = True
                else:
                    all_record = False
                prop = getattr(type_, attr_name, None)
                if prop is None:
                    if getattr(type_, "__getattr__", None):
                        attrs_found.append(None)
                else:
                    attrs_found.append(prop)
        
            if not attrs_found and all_record:
                raise self._exc(
                    "NoSuchAttribute",
                    attribute=attr_name,
                )
            elif attrs_found:
                self._attrs[attr_name] = placeholder(
                    tuple(itertypes(getattr(attr, "valuetype", any) for
                                    attr in attrs_found))
                )
            else:
                self._attrs[attr_name] = placeholder(any)
        return self._attrs[attr_name]

    def __setattr__(self, item, value):
        if item in ("_typetuple", "_attrs", "_member_type"):
            self.__dict__[item] = value
        else:
            raise self._exc("BadAssignment")

    def __setitem__(self, item):
        raise self._exc("BadAssignment")

    def __call__(self, *args, **kwargs):
        if self._typetuple is any:
            return self
        for type_ in self._typetuple:
            if hasattr(type_, "__call__"):
                return placeholder(any)
            raise self._exc('CannotInvoke')

    def __getitem__(self, item):
        if self._typetuple is any:
            return self
        if isinstance(item, slice):
            return self
        elif self._member_type is None:
            all_record = None
            coll_types = []
            for type_ in self._typetuple:
                is_record = issubclass(type_, normalize.record.Record)
                if is_record:
                    if all_record is None:
                        all_record = True
                    is_coll = issubclass(type_, normalize.coll.Collection)
                    if is_coll:
                        coll_types.append(type_.itemtype)
                else:
                    all_record = False

            if all_record and not coll_types:
                raise self._exc("NotSubscriptable")
            elif coll_types:
                self._member_type = placeholder(tuple(itertypes(coll_types)))
            else:
                self._member_type = placeholder(any)
        return self._member_type

    def __nonzero__(self):
        return False

    def _exc(self, which, **kwargs):
        return getattr(normalize.exc, which)(
            typenames=",".join(
                str(t.__name__) for t in self._typetuple
                    if isinstance(t, type)
            ),
            **kwargs)
