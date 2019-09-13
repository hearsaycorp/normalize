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

from past.builtins import basestring
import normalize.exc as exc
from normalize.property import Property


class RecordMeta(type):
    """Metaclass for ``Record`` types.
    """
    def __new__(mcs, name, bases, attrs):
        """Invoked when a new ``Record`` type is declared, and is responsible
        for copying the ``properties`` from superclass ``Record`` classes,
        processing the ``primary_key`` declaration, and calling
        :py:meth:`normalize.property.Property.bind` to link
        :py:class:`normalize.property.Property` instances to their containing
        :py:class:`normalize.record.Record` classes.
        """
        properties = dict()

        for base in bases:
            if hasattr(base, "properties"):
                for propname, prop in base.properties.items():
                    if propname in properties:
                        raise exc.MultipleInheritanceClash(
                            prop=prop,
                            typename=name,
                        )
                    else:
                        properties[propname] = prop

        local_props = dict()
        aux_props = dict()

        for attrname, attrval in list(attrs.items()):
            # don't allow clobbering of these meta-properties in class
            # definitions
            if attrname in frozenset(('properties', 'eager_properties')):
                raise exc.ReservedPropertyName(attrname=attrname)
            if isinstance(attrval, Property):
                properties[attrname] = attrval
                if not attrval.bound:
                    attrval.set_name(attrname)
                    local_props[attrname] = attrval
                    for aux_name, aux_prop in attrval.aux_props():
                        aux_props[aux_name] = aux_prop

        all_properties = set(properties.values())

        def coerce_prop_list(prop_list_field):
            proplist = attrs.get(prop_list_field, None)
            good_props = []
            if proplist:
                for prop in proplist:
                    if isinstance(prop, basestring):
                        prop = properties[prop]
                    if not isinstance(prop, Property) or (
                        prop not in all_properties
                    ):
                        raise exc.PropertiesNotKnown(
                            badprop=repr(prop),
                            proplist=repr(proplist),
                        )
                    good_props.append(prop)
            return tuple(good_props)

        attrs.update(aux_props)
        attrs['primary_key'] = coerce_prop_list('primary_key')
        attrs['properties'] = properties
        attrs['_sorted_properties'] = sorted(
            list(x for x in list(properties.values()) if not x.extraneous),
            key=lambda x: x.name,
        )
        attrs['eager_properties'] = frozenset(
            k for k, v in properties.items() if v.eager_init()
        )

        self = super(RecordMeta, mcs).__new__(mcs, name, bases, attrs)

        for propname, prop in local_props.items():
            prop.bind(self)

        return self
