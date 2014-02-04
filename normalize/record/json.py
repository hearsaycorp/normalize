
from __future__ import absolute_import

import json

from normalize.property.json import JsonProperty
from normalize.record import ListRecord
from normalize.record import Record


def from_json(record_type, json_struct, _init=None):
    """JSON marshall in function: a 'visitor' function which looks for JSON
    types/hints but does not require them.

    @param json_struct a loaded (via ``json.loads``) data structure
    @param record_type a Record object to load items into
    @param _init instead of returning a new object, set kwargs for
                 constructing a Record into here and return it
    """

    if issubclass(record_type, ListRecord):
        member_type = record_type.record_cls
        init_arg = _init or []
        if not json_struct:
            json_struct = tuple()

        if hasattr(member_type, "from_json"):
            for x in json_struct:
                init_arg.append(member_type.from_json(x))

        elif isinstance(member_type, Record):
            for x in json_struct:
                init_arg.append(from_json(member_type, x))

        if _init:
            return init_arg
        else:
            return record_type(init_arg)

    elif issubclass(record_type, Record):
        kwargs = _init or {}
        if json_struct is None:
            json_struct = {}
        if not isinstance(json_struct, dict):
            raise TypeError(
                "dict expected, found %s" % type(json_struct).__name__
            )
        for propname, prop in record_type.properties.iteritems():
            # think "does" here rather than "is"
            if isinstance(prop, JsonProperty):
                json_name = prop.json_name
                if json_name is not None:
                    if json_name in json_struct:
                        kwargs[propname] = prop.from_json(json_struct[prop])
            elif prop.name in json_struct:
                json_val = json_struct[prop.name]
                proptype = prop.valuetype
                if proptype and hasattr(proptype, "from_json"):
                    kwargs[propname] = proptype.from_json(json_val)
                elif proptype and isinstance(proptype, Record):
                    kwargs[propname] = from_json(proptype, json_val)
                else:
                    # let the property's 'check' etc figure it out.
                    kwargs[propname] = json_val
        if _init:
            return kwargs
        else:
            return record_type(**kwargs)
    else:
        raise Exception("Can't coerce to %r" % record_type)


class JsonRecord(Record):
    """Version of a Record which deals primarily in JSON"""
    def __init__(self, json_data=None, **kwargs):
        """Build a new JsonRecord sub-class.

        @param json_data JSON data (string or already json.load'd)
        @param **kwargs fall-back defaults for properties not passed in via
                        JSON; of a type allowed by the Property.
        """
        if isinstance(json_data, basestring):
            json_data = json.loads(json_data)
        json_data = json_data or {}
        init_kwargs = from_json(type(self), json_data, kwargs)
        super(JsonRecord, self).__init__(**init_kwargs)

    @classmethod
    def from_json(self, json_data):
        """Class method constructor"""
        if isinstance(json_data, basestring):
            json_data = json.loads(json_data)
        return from_json(self, json_data)


class JsonListRecord(ListRecord):
    """Version of a ListRecord which deals primarily in JSON"""
    def __init__(self, json_data=None, **kwargs):
        """Build a new JsonRecord sub-class.

        @param json_data JSON data (string or already json.load'd)
        @param **kwargs fall-back defaults for properties not passed in via
                        JSON; of a type allowed by the Property.
        """
        if isinstance(json_data, basestring):
            json_data = json.loads(json_data)
        json_data = json_data or []
        init_list = from_json(type(self), json_data, kwargs)
        super(JsonListRecord, self).__init__(init_list)

    @classmethod
    def from_json(self, init):
        """Class method constructor"""
        return from_json(self, init)
