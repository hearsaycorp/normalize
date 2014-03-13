from __future__ import absolute_import

from normalize.property import Property
from normalize.property import SafeProperty
from normalize.property.coll import ListProperty
from normalize.coll import ListCollection


class Default(object):
    pass


class JsonProperty(Property):
    '''Object property wrapper for record json data'''
    __trait__ = 'json'

    def __init__(self, json_name=Default, json_in=None, json_out=None,
                 **kwargs):
        super(JsonProperty, self).__init__(**kwargs)
        self._json_name = json_name
        self.json_in = json_in
        self.json_out = json_out

    @property
    def json_name(self):
        """Retrieve field name as present in JSON dictionary"""
        return self.name if self._json_name is Default else self._json_name

    def to_json(self, propval):
        return self.json_out(propval) if self.json_out else propval

    def from_json(self, json_data):
        return self.json_in(json_data) if self.json_in else json_data


class SafeJsonProperty(JsonProperty, SafeProperty):
    pass


class JsonCollectionProperty(ListProperty, JsonProperty):
    pass


class JsonCollection(ListCollection):
    pass


class SafeJsonCollectionProperty(JsonCollectionProperty, SafeProperty):
    pass
