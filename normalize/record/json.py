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

import collections
from copy import deepcopy
import inspect
import json
import re
import types

from normalize.coll import Collection
from normalize.coll import DictCollection as RecordDict
from normalize.coll import ListCollection as RecordList
from normalize.coll import list_of
from normalize.diff import Diff
from normalize.diff import DiffInfo
import normalize.exc as exc
from normalize.property.json import JsonProperty
from normalize.record import OhPickle
from normalize.record import Record
from normalize.selector import FieldSelector


def _json_to_value_initializer(json_val, proptype):
    if proptype:
        if isinstance(proptype, JsonRecord):
            return json_val
        elif hasattr(proptype, "from_json"):
            return proptype.from_json(json_val)
        elif isinstance(proptype, Record) and isinstance(json_val, dict):
            return from_json(proptype, json_val)

    return json_val


def _box_ingress_error(context, exception):
    error_fs = FieldSelector([context])
    if hasattr(exception, "error_fs"):
        error_fs.extend(exception.error_fs)
    if hasattr(exception, "sub_exception"):
        exception = exception.sub_exception
    return exc.JsonConversionError(
        error_fs=error_fs,
        sub_exception=exception,
    )


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
        raise exc.JsonRecordCoerceError(
            passed=json_struct,
            recordtype=record_type,
        )
    unknown_keys = set(json_struct.keys())
    for propname, prop in record_type.properties.iteritems():
        # think "does" here rather than "is"; the slot does JSON
        if isinstance(prop, JsonProperty):
            json_name = prop.json_name
            if json_name is not None:
                if json_name in json_struct:
                    if propname not in kwargs:
                        try:
                            kwargs[propname] = _json_to_value_initializer(
                                prop.from_json(
                                    json_struct[json_name]
                                ),
                                prop.valuetype,
                            )
                        except Exception as e:
                            raise _box_ingress_error(json_name, e)
                    unknown_keys.remove(json_name)
        elif prop.name in json_struct:
            json_val = json_struct[prop.name]
            unknown_keys.remove(prop.name)
            if prop.name not in kwargs:
                proptype = prop.valuetype
                try:
                    kwargs[propname] = _json_to_value_initializer(
                        json_val, proptype,
                    )
                except Exception as e:
                    raise _box_ingress_error(prop.name, e)
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
        raise exc.CastTypeError(badtype=record_type)


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


def to_json(record, extraneous=True, prop=None):
    """JSON conversion function: a 'visitor' function which implements marshall
    out (to JSON data form), honoring JSON property types/hints but does not
    require them.  To convert to an actual JSON document, pass the return value
    to ``json.dumps`` or a similar function.

    args:
        ``record=``\ *anything*
            This object can be of any type; a best-effort attempt is made to
            convert to a form which ``json.dumps`` can accept; this function
            will call itself recursively, respecting any types which define
            ``.json_data()`` as a method and calling that.

        ``extraneous=``\ *BOOL*
            This parameter is passed through to any ``json_data()`` methods
            which support it.

        ``prop=``\ *PROPNAME*\ |\ *PROPERTY*
            Specifies to return the given property from an object, calling any
            ``to_json`` mapping defined on the property.  Does not catch the
            ``AttributeError`` that is raised by the property not being set.
    """
    if prop:
        if isinstance(prop, basestring):
            prop = type(record).properties[prop]
        val = prop.__get__(record)
        if hasattr(prop, "to_json"):
            return prop.to_json(val, extraneous, _json_data)
        else:
            return _json_data(val, extraneous)

    elif isinstance(record, Collection):
        if isinstance(record, RecordDict):
            return dict(
                (k, _json_data(v, extraneous)) for k, v in record.items()
            )
        else:
            return list(_json_data(x, extraneous) for x in record)

    elif isinstance(record, Record):
        rv_dict = {}
        for propname, prop in type(record).properties.iteritems():
            if not extraneous and prop.extraneous:
                pass
            elif prop.slot_is_empty(record):
                pass
            elif not hasattr(prop, "json_name") or prop.json_name is not None:
                json_name = getattr(prop, "json_name", prop.name)
                try:
                    rv_dict[json_name] = to_json(record, extraneous, prop)
                except AttributeError:
                    pass
        return rv_dict

    elif isinstance(record, long):
        return str(record) if abs(record) > 2**50 else record

    elif isinstance(record, dict):
        return dict(
            (k, _json_data(v, extraneous)) for k, v in record.iteritems()
        )

    elif isinstance(record, (list, tuple, set, frozenset)):
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
                        jd[k] = to_json(v, extraneous)
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
    json_coll_name = "array"

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
        if not member_type:
            raise exc.CollectionDefinitionError(
                coll="JsonRecordList",
                property='itemtype',
            )
        if kwargs.get('values', None) is None:
            kwargs['values'] = values = []
            if json_struct is None:
                json_struct = tuple()
            if not isinstance(json_struct, (list, tuple)):  # sigh
                raise exc.JsonCollectionCoerceError(
                    passed=json_struct,
                    colltype=cls,
                )

            if hasattr(member_type, "from_json"):
                for i, x in cls.coll_to_tuples(json_struct):
                    try:
                        values.append(
                            x if isinstance(x, member_type) else
                            member_type.from_json(x)
                        )
                    except Exception as e:
                        raise _box_ingress_error(i, e)

            elif issubclass(member_type, Record):
                for i, x in cls.coll_to_tuples(json_struct):
                    try:
                        values.append(
                            x if isinstance(x, member_type) else
                            from_json(member_type, x)
                        )
                    except Exception as e:
                        raise _box_ingress_error(i, e)
            else:
                kwargs['values'] = json_struct
        return kwargs

    def json_data(self, extraneous=False):
        # this method intentionally does not call the superclass json_data,
        # because this function returns a collection.
        return to_json(self, extraneous)

    def __repr__(self):
        super_repr = super(JsonRecordList, self).__repr__()
        return super_repr.replace("[", "values=[", 1)


class JsonRecordDict(RecordDict, JsonRecord):
    """Version of a RecordDict which deals primarily in JSON"""
    json_coll_name = "object"

    def __init__(self, json_data=None, **kwargs):
        """Build a new JsonRecord sub-class.

        Args:
            ``json_data=``\ *DICT|other*
                JSON data (string or already ``json.loads``'d)

            ``**kwargs``
                Other initializer attributes, for lists with extra
                attributes (eg, paging information).
        """
        if isinstance(json_data, OhPickle):
            return
        if isinstance(json_data, basestring):
            json_data = json.loads(json_data)
        if json_data is not None:
            kwargs = type(self).json_to_initkwargs(json_data, kwargs)
        super(JsonRecordDict, self).__init__(**kwargs)

    @classmethod
    def json_to_initkwargs(cls, json_struct, kwargs):
        member_type = cls.itemtype
        if not member_type:
            raise exc.CollectionDefinitionError(
                coll="JsonRecordDict",
                property='itemtype',
            )
        if kwargs.get('values', None) is None:
            kwargs['values'] = values = {}
            if json_struct is None:
                json_struct = {}
            if not isinstance(json_struct, collections.Mapping):
                raise exc.JsonCollectionCoerceError(
                    passed=json_struct,
                    colltype=cls,
                )

            if hasattr(member_type, "from_json"):
                for k, x in cls.coll_to_tuples(json_struct):
                    try:
                        values[k] = (
                            x if isinstance(x, member_type) else
                            member_type.from_json(x)
                        )
                    except Exception as e:
                        raise _box_ingress_error(k, e)
            elif issubclass(member_type, Record):
                for k, x in cls.coll_to_tuples(json_struct):
                    try:
                        values[k] = (
                            x if isinstance(x, member_type) else
                            from_json(member_type, x)
                        )
                    except Exception as e:
                        raise _box_ingress_error(k, e)
            else:
                kwargs['values'] = json_struct
        return kwargs

    def json_data(self, extraneous=False):
        # this method intentionally does not call the superclass json_data,
        # because this function returns a collection.
        return to_json(self, extraneous)

    def __repr__(self):
        super_repr = super(JsonRecordList, self).__repr__()
        return super_repr.replace("{", "values={", 1)


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


class AutoJsonRecord(JsonRecord):
    unknown_json_keys = JsonProperty(
        json_name=None, extraneous=False, default=lambda: {},
    )

    @classmethod
    def auto_upgrade_dict(cls, thing):
        return AutoJsonRecord(thing)

    @classmethod
    def auto_upgrade_list(cls, thing):
        if len(thing) and isinstance(thing[0], dict):
            return list_of(AutoJsonRecord)(thing)
        else:
            return thing

    @classmethod
    def auto_upgrade_any(cls, thing):
        if isinstance(thing, dict):
            return cls.auto_upgrade_dict(thing)
        elif isinstance(thing, list):
            return cls.auto_upgrade_list(thing)
        else:
            return thing

    @classmethod
    def convert_json_key_in(cls, key):
        return re.sub(
            r'([a-z\d])([A-Z])',
            lambda m: "%s_%s" % (m.group(1), m.group(2).lower()),
            key,
        )

    @classmethod
    def convert_json_key_out(cls, key):
        return re.sub(
            r'([a-z\d])_([a-z])',
            lambda m: "%s%s" % (m.group(1), m.group(2).upper()),
            key,
        )

    @classmethod
    def json_to_initkwargs(cls, json_data, kwargs):
        kwargs = super(AutoJsonRecord, cls).json_to_initkwargs(
            json_data, kwargs,
        )
        # upgrade any dictionaries to AutoJsonRecord, and
        # any lists of dictionaries to list_of(AutoJsonRecord)
        if 'unknown_json_keys' in kwargs:
            kwargs['unknown_json_keys'] = {
                cls.convert_json_key_in(k): cls.auto_upgrade_any(v) for
                k, v in kwargs['unknown_json_keys'].items()
            }
        return kwargs

    def json_data(self, extraneous=False):
        jd = to_json(self, extraneous)
        if hasattr(self, "unknown_json_keys"):
            prop = type(self).properties['unknown_json_keys']
            if extraneous or not prop.extraneous:
                for k, v in self.unknown_json_keys.iteritems():
                    k = type(self).convert_json_key_out(k)
                    if k not in jd:
                        jd[k] = to_json(v, extraneous)
        return jd

    def __getattr__(self, attr):
        if attr in type(self).properties:
            return type(self).properties[attr].__get__(self)
        else:
            return self.unknown_json_keys[attr]

    def __setattr__(self, attr, value):
        if attr in type(self).properties:
            return type(self).properties[attr].__set__(self)
        else:
            self.unknown_json_keys[attr]

    def __delattr__(self, attr, value):
        if attr in type(self).properties:
            return type(self).properties[attr].__del__(self)
        else:
            del self.unknown_json_keys[attr]


class NCAutoJsonRecord(AutoJsonRecord):
    """A version of AutoJsonRecord which does not convert keys from
    camelCase to python_form"""
    @classmethod
    def convert_json_key_in(cls, key):
        return key

    @classmethod
    def convert_json_key_out(cls, key):
        return key

    @classmethod
    def auto_upgrade_dict(cls, thing):
        return NCAutoJsonRecord(thing)

    @classmethod
    def auto_upgrade_list(cls, thing):
        if len(thing) and isinstance(thing[0], dict):
            return list_of(NCAutoJsonRecord)(thing)
        else:
            return thing
