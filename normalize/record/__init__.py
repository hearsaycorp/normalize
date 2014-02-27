from __future__ import absolute_import

from normalize.coll import Collection
from normalize.coll import ListCollection
from normalize.record.meta import RecordMeta


class _Unset(object):
    pass


def record_id(object_, type_=None):
    """Implementation of id() which is overridable and knows about record's
    primary_key property.  Returns if the two objects may be the "same";
    returns None for other types, meaning all bets about identity are off.

    Curiously, this function resembles conversion between a "record" and a
    "tuple": stripping the logical names from the atomic values.
    """
    if type_ is None:
        type_ = type(object_)
    key_vals = list()

    for prop in type_.primary_key or type_._sorted_properties:
        val = getattr(object_, prop.name, None)
        value_type = prop.valuetype
        if val is not None and value_type:
            if issubclass(value_type, Record):
                val = getattr(val, "__pk__", record_id(val, value_type))
            elif issubclass(value_type, Collection):
                val = tuple(record_id(x, prop.itemtype) for x in val)
        key_vals.append(val)
    return tuple(key_vals)


class Record(object):
    """Base class for normalize instances"""
    __metaclass__ = RecordMeta

    def __init__(self, init_dict=None, **kwargs):
        if init_dict and kwargs:
            raise Exception("only init_dict or kwargs may be specified")
        if not init_dict:
            init_dict = kwargs
        for prop, val in init_dict.iteritems():
            meta_prop = type(self).properties.get(prop, None)
            if meta_prop is None:
                raise Exception(
                    "unknown property '%s' in %s" % (prop, type(self).__name__)
                )
            meta_prop.init_prop(self, val)
        missing = type(self).eager_properties - set(init_dict.keys())

        for propname in missing:
            meta_prop = type(self).properties[propname]
            meta_prop.init_prop(self)

    def __iter__(self):
        for name in type(self).properties.keys():
            yield (name, getattr(self, name, None))

    def __getnewargs__(self):
        """Implement saving for pickle API"""
        return (dict(self),)

    def __str__(self):
        """Marshalling to string form"""
        pk = self.__pk__
        return "<%s %s>" % (
            type(self).__name__, repr(pk[0] if len(pk) == 1 else pk)
        )

    def __repr__(self):
        """Marshalling to Python source"""
        typename = type(self).__name__
        values = list()
        for propname in sorted(type(self).properties):
            if propname not in self.__dict__:
                continue
            else:
                values.append("%s=%r" % (propname, self.__dict__[propname]))
        return "%s(%s)" % (typename, ", ".join(values))

    def __eq__(self, other):
        """Compare two Record classes; recursively compares all attributes
        for equality (except those marked 'extraneous')"""
        if type(self) != type(other):
            return False
        for propname, prop in type(self).properties.iteritems():
            if not prop.extraneous:
                if getattr(self, propname, _Unset) != getattr(
                    other, propname, _Unset
                ):
                    return False
        return True

    def __ne__(self, other):
        return not self.__eq__(other)

    @property
    def __pk__(self):
        return record_id(self, type(self))

    def __hash__(self):
        return self.__pk__.__hash__()


RecordList = ListCollection
ListRecord = RecordList  # deprecated; will be removed before public release
