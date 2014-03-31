from __future__ import absolute_import

import normalize.exc as exc
from normalize.identity import record_id
from normalize.record.meta import RecordMeta


class _Unset(object):
    pass


class Record(object):
    """Base class for normalize instances"""
    __metaclass__ = RecordMeta

    def __init__(self, init_dict=None, **kwargs):
        if init_dict and kwargs:
            raise exc.AmbiguousConstruction()
        if not init_dict:
            init_dict = kwargs
        for prop, val in init_dict.iteritems():
            meta_prop = type(self).properties.get(prop, None)
            if meta_prop is None:
                raise exc.PropertyNotKnown(
                    propname=prop,
                    typename=type(self).__name__,
                )
            meta_prop.init_prop(self, val)
        missing = type(self).eager_properties - set(init_dict.keys())

        for propname in missing:
            meta_prop = type(self).properties[propname]
            meta_prop.init_prop(self)

    def __getnewargs__(self):
        """Implement saving for pickle API"""
        newdict = dict()
        for name in type(self).properties.keys():
            if hasattr(self, name):
                newdict[name] = getattr(self, name, None)
        return (newdict,)

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

    def diff_iter(self, other, **kwargs):
        from normalize.diff import diff_iter
        return diff_iter(self, other, **kwargs)

    def diff(self, other, **kwargs):
        from normalize.diff import diff
        return diff(self, other, **kwargs)

    def walk(self, fs=None):
        if fs is None:
            from normalize.selector import FieldSelector
            fs = FieldSelector([])
        for name, prop in type(self).properties.iteritems():
            if hasattr(self, name):
                val = getattr(self, name)
                prop_fs = fs + [name]
                yield (prop_fs, prop, self, val)
                if isinstance(val, Record):
                    for x in val.walk(prop_fs):
                        yield x
