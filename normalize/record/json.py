
from __future__ import absolute_import

import inspect
import json
import types

from normalize.coll import Collection
from normalize.property.json import JsonProperty
from normalize.record import Record
from normalize.record import RecordList


def from_json(record_type, json_struct, _init=None):
    """JSON marshall in function: a 'visitor' function which looks for JSON
    types/hints but does not require them.

    @param json_struct a loaded (via ``json.loads``) data structure
    @param record_type a Record object to load items into
    @param _init instead of returning a new object, set kwargs for
                 constructing a Record into here and return it
    """

    if issubclass(record_type, RecordList):
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

        if _init is not None:
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
                        kwargs[propname] = prop.from_json(
                            json_struct[json_name]
                        )
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
        if _init is not None:
            return kwargs
        else:
            return record_type(**kwargs)
    else:
        raise Exception("Can't coerce to %r" % record_type)


# caches for _to_json
has_to_json = dict()
to_json_takes_extraneous = dict()


def _to_json(x, extraneous):
    """This function calls a to_json method, if the type has one, otherwise
    calls back into to_json().  It also check whether the method takes an
    'extraneous' argument and passes that through if possible."""
    if type(x) in has_to_json and has_to_json[type(x)]:
        if to_json_takes_extraneous[type(x)]:
            return x.to_json(extraneous=extraneous)
        else:
            return x.to_json()
    else:
        htj = hasattr(x, "to_json") and callable(x.to_json)
        has_to_json[type(x)] = htj
        if htj:
            argspec = inspect.getargspec(x.to_json)
            tjte = 'extraneous' in argspec.args or argspec.keywords
            to_json_takes_extraneous[type(x)] = tjte
            if tjte:
                return x.to_json(extraneous=extraneous)
            else:
                return x.to_json()
        else:
            return to_json(x, extraneous)


def to_json(record, extraneous=True):
    """JSON marshall out function: a 'visitor' function which implements
    marshall out, honoring JSON property types/hints but does not require
    them."""
    if isinstance(record, Collection):
        return list(_to_json(x, extraneous) for x in record)

    elif isinstance(record, Record):
        rv_dict = {}
        for propname, prop in type(record).properties.iteritems():
            if not extraneous and prop.extraneous:
                pass
            else:
                json_name = getattr(prop, "json_name", prop.name)
                rv_dict[json_name] = to_json(prop.__get__(record))

        return rv_dict

    elif isinstance(record, long):
        return str(record) if abs(record) > 2**50 else record

    elif isinstance(record, dict):
        return dict(
            (k, _to_json(v, extraneous)) for k, v in record.iteritems()
        )

    elif isinstance(record, (list, tuple)):
        return list(_to_json(x, extraneous) for x in record)

    elif isinstance(record, (basestring, int, float, types.NoneType)):
        return record

    else:
        raise TypeError(
            "I don't know how to marshall a %s to JSON" %
            type(record).__name__
        )


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

    def json_data(self):
        return to_json(self)


class JsonRecordList(RecordList):
    """Version of a RecordList which deals primarily in JSON"""
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
        super(JsonRecordList, self).__init__(init_list)

    @classmethod
    def from_json(self, init):
        """Class method constructor"""
        return from_json(self, init)

    def json_data(self):
        return to_json(self)
