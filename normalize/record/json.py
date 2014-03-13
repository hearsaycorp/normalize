
from __future__ import absolute_import

from copy import deepcopy
import inspect
import json
import types

from normalize.coll import Collection
from normalize.coll import ListCollection as RecordList
from normalize.property.json import JsonProperty
from normalize.record import Record


def json_to_initkwargs(record_type, json_struct, kwargs=None):
    """This function converts a JSON dict (json_struct) to a set of init
    keyword arguments for the passed Record (or JsonRecord).

    It is called by the JsonRecord constructor.
    """
    if kwargs is None:
        kwargs = {}
    if json_struct is None:
        json_struct = {}
    if not isinstance(json_struct, dict):
        raise TypeError(
            "dict expected, found %s" % type(json_struct).__name__
        )
    unknown_keys = set(json_struct.keys())
    for propname, prop in record_type.properties.iteritems():
        # think "does" here rather than "is"; the slot does JSON
        if isinstance(prop, JsonProperty):
            json_name = prop.json_name
            if json_name is not None:
                if json_name in json_struct:
                    if propname not in kwargs:
                        kwargs[propname] = prop.from_json(
                            json_struct[json_name]
                        )
                    unknown_keys.remove(json_name)
        elif prop.name in json_struct:
            json_val = json_struct[prop.name]
            unknown_keys.remove(prop.name)
            if prop.name not in kwargs:
                proptype = prop.valuetype
                if proptype:
                    if hasattr(proptype, "from_json"):
                        kwargs[propname] = proptype.from_json(json_val)
                    elif isinstance(proptype, Record):
                        kwargs[propname] = from_json(proptype, json_val)
                    else:
                        # let the property's 'check' etc figure it out.
                        kwargs[propname] = json_val
    if unknown_keys:
        kwargs["unknown_json_keys"] = dict(
            (k, deepcopy(json_struct[k])) for k in unknown_keys
        )
    return kwargs


def from_json(record_type, json_struct):
    """JSON marshall in function: a 'visitor' function which looks for JSON
    types/hints but does not require them.

    @param json_struct a loaded (via ``json.loads``) data structure
    @param record_type a Record object to load items into
    """
    if issubclass(record_type, JsonRecord):
        return record_type(json_struct)

    elif issubclass(record_type, Record):
        # do what the default JsonRecord __init__ does
        init_kwargs = json_to_initkwargs(record_type, json_struct)
        instance = record_type(**init_kwargs)
        return instance
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
            elif not hasattr(prop, "json_name") or prop.json_name is not None:
                json_name = getattr(prop, "json_name", prop.name)
                try:
                    val = prop.__get__(record)
                except AttributeError:
                    pass
                else:
                    rv_dict[json_name] = (
                        prop.to_json(val) if hasattr(prop, "to_json") else
                        to_json(val)
                    )

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
    """Version of a Record which deals primarily in JSON form.

    This means:

    1. The first argument to the constructor is assumed to be a JSON data
       dictionary, and passed through the class' ``json_to_initkwargs``
       method before being used to set actual properties

    2. Unknown keys are permitted, and saved in the "unknown_json_keys"
       property, which is merged back on output (ie, calling ``.json_data()``
       or ``to_json()``) #TODO
    """
    unknown_json_keys = JsonProperty(json_name=None, extraneous=True)

    def __init__(self, json_data=None, **kwargs):
        """Build a new JsonRecord sub-class.

        @param json_data JSON data (string or already json.load'd)
        @param **kwargs fall-back defaults for properties not passed in via
                        JSON; of a type allowed by the Property.
        """
        if isinstance(json_data, basestring):
            json_data = json.loads(json_data)
        if json_data is not None:
            kwargs = type(self).json_to_initkwargs(json_data, kwargs)
        super(JsonRecord, self).__init__(**kwargs)

    @classmethod
    def json_to_initkwargs(self, json_data, kwargs=None):
        """Subclassing hook to specialize how JSON data is converted
        to keyword arguments"""
        if isinstance(json_data, basestring):
            json_data = json.loads(json_data)
        return json_to_initkwargs(self, json_data, kwargs)

    @classmethod
    def from_json(self, json_data):
        """This method can be overridden to specialize how the class is loaded
        when marshalling in; however beware that it is not invoked when the
        caller uses the ``from_json()`` function directly."""
        return self(json_data)

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
    def json_to_initkwargs(self, json_struct, kwargs=None):
        member_type = self.itemtype
        if kwargs is None:
            kwargs = {}
        if kwargs.get('values', None) is not None:
            kwargs['values'] = values = []
            if not json_struct:
                json_struct = tuple()

            if hasattr(member_type, "from_json"):
                for x in json_struct:
                    values.append(member_type.from_json(x))

            elif isinstance(member_type, Record):
                for x in json_struct:
                    values.append(from_json(member_type, x))
        return kwargs

    def json_data(self):
        return to_json(self)
