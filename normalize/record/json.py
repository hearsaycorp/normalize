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

from copy import deepcopy
import inspect
import json
import types

from normalize.coll import Collection
from normalize.coll import ListCollection as RecordList
from normalize.diff import Diff
from normalize.diff import DiffInfo
import normalize.exc as exc
from normalize.property.json import JsonProperty
from normalize.record import OhPickle
from normalize.record import Record


def _json_to_value_initializer(json_val, proptype):
    if proptype:
        if isinstance(proptype, JsonRecord):
            return json_val
        elif hasattr(proptype, "from_json"):
            return proptype.from_json(json_val)
        elif isinstance(proptype, Record) and isinstance(json_val, dict):
            return from_json(proptype, json_val)

    return json_val


def json_to_initkwargs(record_type, json_struct, kwargs=None):
    """This function converts a JSON dict (json_struct) to a set of init
    keyword arguments for the passed Record (or JsonRecord).

    It is called by the JsonRecord constructor.  This function takes a JSON
    data structure and returns a keyword argument list to be passed to the
    class constructor.  Any keys in the input dictionary which are not known
    are passed as a single ``unknown_json_keys`` value as a dict.

    This function should generally not be called directly, except as a part of
    a ``__init__`` or specialized visitor application.
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
                        kwargs[propname] = _json_to_value_initializer(
                            prop.from_json(
                                json_struct[json_name]
                            ),
                            prop.valuetype,
                        )
                    unknown_keys.remove(json_name)
        elif prop.name in json_struct:
            json_val = json_struct[prop.name]
            unknown_keys.remove(prop.name)
            if prop.name not in kwargs:
                proptype = prop.valuetype
                kwargs[propname] = _json_to_value_initializer(
                    json_val, proptype,
                )
    if unknown_keys:
        kwargs["unknown_json_keys"] = dict(
            (k, deepcopy(json_struct[k])) for k in unknown_keys
        )
    return kwargs


def from_json(record_type, json_struct):
    """JSON marshall in function: a 'visitor' function which looks for JSON
    types/hints on types being converted to, but does not require them.

    Args:
        ``record_type=``\ *TYPE*
            Record type to convert data to

        ``json_struct=``\ *DICT|LIST*
            a loaded (via ``json.loads``) data structure, normally a
            dict or a list.
    """
    if issubclass(record_type, JsonRecord):
        return record_type(json_struct)

    elif issubclass(record_type, Record):
        # do what the default JsonRecord __init__ does
        init_kwargs = json_to_initkwargs(record_type, json_struct)
        instance = record_type(**init_kwargs)
        return instance
    else:
        raise exc.JsonRecordCoerceError(
            given=repr(json_struct),
            type=record_type.__name__,
        )


# caches for _json_data
has_json_data = dict()
json_data_takes_extraneous = dict()


def _json_data(x, extraneous):
    """This function calls a json_json method, if the type has one, otherwise
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
    them.

    args:
        ``record=``\ *anything*
            This object can be of any type; a best-effort attempt is made to
            convert to a form which ``json.dumps`` can accept; this function
            will call itself recursively, respecting any types which define
            ``.json_data()`` as a method and calling that.

        ``extraneous=``\ *BOOL*
            This parameter is passed through to any ``json_data()`` methods
            which support it.
    """
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
                    rv_dict[json_name] = _json_data(val, extraneous)

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
       or ``to_json()``)
    """
    unknown_json_keys = JsonProperty(json_name=None, extraneous=True)

    def __init__(self, json_data=None, **kwargs):
        """Build a new JsonRecord sub-class.

        args:
            ``json_data=``\ *DICT|other*
                JSON data (string or already ``json.loads``'d).  If not
                a JSON dictionary with keys corresponding to the
                ``json_name`` or the properties within, then
                ``json_to_initkwargs`` should be overridden to handle
                the unpacking differently

            ``**kwargs``
                ``JsonRecord`` instances may also be constructed by
                passing in attribute initializers in keyword form.  The
                keys here should be the names of the attributes and the
                python values, not the JSON names or form.
        """
        if isinstance(json_data, OhPickle):
            return
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
        """Returns the JSON data form of this ``JsonRecord``.  The 'unknown'
        JSON keys will be merged back in, if:

        1. the ``extraneous=True`` argument is passed.

        2. the ``unknown_json_keys`` property on this class is replaced by one
           not marked as ``extraneous``
        """
        jd = to_json(self, extraneous)
        if hasattr(self, "unknown_json_keys"):
            prop = type(self).properties['unknown_json_keys']
            if extraneous or not prop.extraneous:
                for k, v in self.unknown_json_keys.iteritems():
                    if k not in jd:
                        jd[k] = v
        return jd

    def diff_iter(self, other, **kwargs):
        """Generator method which returns the differences from the invocant to
        the argument.  This specializes :py:meth:`Record.diff_iter` by
        returning :py:class:`JsonDiffInfo` objects.
        """
        for diff in super(JsonRecord, self).diff_iter(other, **kwargs):
            # TODO: object copy/upgrade constructor
            newargs = diff.__getstate__()
            yield JsonDiffInfo(**(newargs))

    def diff(self, other, **kwargs):
        """Compare an object with another.  This specializes
        :py:meth:`Record.diff` by returning a :py:class:`JsonDiff` object.
        """
        return JsonDiff(
            base_type_name=type(self).__name__,
            other_type_name=type(other).__name__,
            values=self.diff_iter(other, **kwargs),
        )


class JsonRecordList(RecordList, JsonRecord):
    """Version of a RecordList which deals primarily in JSON"""
    def __init__(self, json_data=None, **kwargs):
        """Build a new JsonRecord sub-class.

        Args:
            ``json_data=``\ *LIST|other*
                JSON data (string or already ``json.loads``'d)

            ``**kwargs``
                Other initializer attributes, for lists with extra
                attributes (eg, paging information)
        """
        if isinstance(json_data, OhPickle):
            return
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
                raise exc.CollectionDefinitionError(
                    coll="JsonRecordList",
                    property='itemtype',
                )
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
