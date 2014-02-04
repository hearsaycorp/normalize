
from __future__ import absolute_import

from normalize.property import Property


class RecordMeta(type):
    """Metaclass to reify descriptors properly"""
    def __new__(mcs, name, bases, attrs):

        properties = dict()

        for base in bases:
            if hasattr(base, "properties"):
                for propname, prop in base.properties.iteritems():
                    if propname in properties:
                        raise Exception(
                            "Property '%s' defined by multiple base "
                            "classes of %s" % (propname, name)
                        )
                    else:
                        properties[propname] = prop

        local_props = dict()

        for attrname, attrval in attrs.items():
            if isinstance(attrval, Property):
                properties[attrname] = attrval
                if not attrval.bound:
                    local_props[attrname] = attrval

        attrs['properties'] = properties
        attrs['required'] = frozenset(
            k for k, v in properties.iteritems() if v.required
        )

        self = super(RecordMeta, mcs).__new__(mcs, name, bases, attrs)

        for propname, prop in local_props.iteritems():
            prop.bind(self, propname)

        return self
