
from __future__ import absolute_import

from copy import deepcopy
import inspect
import json
import types

from normalize.coll import Collection
from normalize.coll import ListCollection as RecordList
from normalize.diff import Diff
from normalize.diff import DiffInfo
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


# caches for _json_data
has_json_data = dict()
json_data_takes_extraneous = dict()


def _json_data(x, extraneous):
    """This function calls a to_json method, if the type has one, otherwise
    calls back into to_json().  It also check whether the method takes an
    'extraneous' argument and passes that through if possible."""
    if type(x) in has_json_data and has_json_data[type(x)]:
        if json_data_takes_extraneous[type(x)]:
            return x.json_data(extraneous=extraneous)
        else:
            return x.json_data()
    else:
        htj = hasattr(x, "json_data") and callable(x.json_data)
        has_json_data[type(x)] = htj
        if htj:
            argspec = inspect.getargspec(x.json_data)
            tjte = 'extraneous' in argspec.args or argspec.keywords
            json_data_takes_extraneous[type(x)] = tjte
            if tjte:
                return x.json_data(extraneous=extraneous)
            else:
                return x.json_data()
        else:
            return to_json(x, extraneous)


def to_json(record, extraneous=True):
    """JSON marshall out function: a 'visitor' function which implements
    marshall out, honoring JSON property types/hints but does not require
    them."""
    if isinstance(record, Collection):
        return list(_json_data(x, extraneous) for x in record)

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
                    if hasattr(prop, "to_json"):
                        val = prop.to_json(val)
                    rv_dict[json_name] = to_json(val, extraneous)

        return rv_dict

    elif isinstance(record, long):
        return str(record) if abs(record) > 2**50 else record

    elif isinstance(record, dict):
        return dict(
            (k, _json_data(v, extraneous)) for k, v in record.iteritems()
        )

    elif isinstance(record, (list, tuple)):
        return list(_json_data(x, extraneous) for x in record)

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
    def json_to_initkwargs(self, json_data, kwargs):
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

    def json_data(self, extraneous=False):
        jd = to_json(self, extraneous)
        if hasattr(self, "unknown_json_keys"):
            prop = type(self).properties['unknown_json_keys']
            if extraneous or not prop.extraneous:
                for k, v in self.unknown_json_keys.iteritems():
                    if k not in jd:
                        jd[k] = v
        return jd

    def diff_iter(self, other, **kwargs):
        for diff in super(JsonRecord, self).diff_iter(other, **kwargs):
            # TODO: object copy/upgrade constructor
            newargs = diff.__getnewargs__()
            yield JsonDiffInfo(**(newargs[0]))

    def diff(self, other, **kwargs):
        return JsonDiff(
            base_type_name=type(self).__name__,
            other_type_name=type(other).__name__,
            values=self.diff_iter(other, **kwargs),
        )


class JsonRecordList(RecordList, JsonRecord):
    """Version of a RecordList which deals primarily in JSON"""
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
        super(JsonRecordList, self).__init__(**kwargs)

    @classmethod
    def json_to_initkwargs(cls, json_struct, kwargs):
        member_type = cls.itemtype
        if kwargs.get('values', None) is None:
            kwargs['values'] = values = []
            if not json_struct:
                json_struct = tuple()

            if hasattr(member_type, "from_json"):
                for x in json_struct:
                    values.append(member_type.from_json(x))
            elif issubclass(member_type, Record):
                for x in json_struct:
                    values.append(from_json(member_type, x))
            else:
                raise Exception("Collection type %s has no itemtype" % cls)
        return kwargs

    def json_data(self, extraneous=False):
        # this method intentionally does not call the superclass json_data,
        # because this function returns a collection.
        return to_json(self, extraneous)

    def __repr__(self):
        super_repr = super(JsonRecordList, self).__repr__()
        return super_repr.replace("[", "values=[", 1)


class JsonDiffInfo(DiffInfo, JsonRecord):
    """Version of 'DiffInfo' that supports ``.json_data()``"""
    def json_data(self):
        return dict(
            diff_type=self.diff_type.canonical_name,
            base=self.base.selectors,
            other=self.other.selectors,
        )


class JsonDiff(Diff, JsonRecordList):
    """Version of 'Diff' that supports ``.json_data()``"""
    itemtype = JsonDiffInfo
