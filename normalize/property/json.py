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

from builtins import object
from normalize.property import Property
from normalize.property import SafeProperty
from normalize.property.coll import DictProperty
from normalize.property.coll import ListProperty


class _Default(object):
    def __repr__(self):
        return "<prop.name>"


_default = _Default()


class JsonProperty(Property):
    '''Object property wrapper for record json data'''
    __trait__ = 'json'

    def __init__(self, json_name=_default, json_in=None, json_out=None,
                 **kwargs):
        """Create a new property with JSON mapping overrides.  You
        generally don't need to use this directly; simply specifying the
        options using ``json_``\ *X* to a superclass like ``Property()``
        is sufficient.

        Arguments:
            ``json_name=``\ *STR*
                Specify the key in the input/output dictionary to use
                for this property when marshalling to/from JSON.

            ``json_in=``\ *FUNCTION*
                Specify a function which converts the JSON form of this
                property to the python form.  This is called *before* the
                ``isa=`` check and ``coerce=`` function, and is always
                called if the key exists on the marshaled in structure.
                This function can recurse into
                :py:func:`normalize.record.from_json` if required.

            ``json_out=``\ *FUNCTION*
                Specify a function which converts a property from the
                python form to a form which your JSON library can handle.
                You'll probably want to convert native python objects to
                strings, in a form which can be reversed by the
                ``json_in`` function.

                This function should recurse into
                :py:func:`normalize.record.to_json` if required.
        """
        super(JsonProperty, self).__init__(**kwargs)
        self._json_name = json_name
        self.json_in = json_in
        self.json_out = json_out

    @property
    def json_name(self):
        """Key name for this attribute in JSON dictionary.  Defaults to
        the attribute name in the class it is bound to."""
        return self.name if self._json_name is _default else self._json_name

    def to_json(self, propval, extraneous=False, to_json_func=None):
        """This function calls the ``json_out`` function, if it was specified,
        otherwise continues with JSON conversion of the value in the slot by
        calling ``to_json_func`` on it.
        """
        if self.json_out:
            return self.json_out(propval)
        else:
            if not to_json_func:
                from normalize.record.json import to_json
                to_json_func = to_json
            return to_json_func(propval, extraneous)

    def from_json(self, json_data):
        """This function calls the ``json_in`` function, if it was
        specified, otherwise passes through."""
        return self.json_in(json_data) if self.json_in else json_data


class SafeJsonProperty(JsonProperty, SafeProperty):
    pass


# late imports to allow circular dependencies to proceed
from normalize.record.json import JsonRecordDict  # noqa
from normalize.record.json import JsonRecordList  # noqa


class JsonListProperty(ListProperty, JsonProperty):
    """A property which map to a list of a known item type in JSON.

    It can also map a dictionary with some top level keys (eg, streaming
    information) and a key with the actual list contents.  See
    :py:mod:`normalize.record.json` for more details.
    """
    coll_type = JsonRecordList


class JsonDictProperty(DictProperty, JsonProperty):
    """A property which map to a dictionary of a known item type in JSON.

    Currently the key type is not enforced.
    """
    coll_type = JsonRecordDict


# deprecated compatibility exports
JsonCollectionProperty = JsonListProperty
