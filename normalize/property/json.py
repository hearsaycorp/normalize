from ..property import Property


class JsonProperty(Property):
    '''Object property wrapper for record json data'''
    __trait__ = 'json'

    def __init__(self, json_name=None, json_in=None, json_out=None, **kwargs):
        super(JsonProperty, self).__init__(**kwargs)
        self._json_name = json_name
        self.json_in = json_in
        self.json_out = json_out

    @property
    def json_name(self):
        """Retrieve field name as present in JSON dictionary"""
        return self._json_name or self.name

    def to_json(self, obj):
        propval = self.__get__(obj)
        return self.json_out(propval) if self.json_out else propval

    def from_json(self, json_data):
        return self.json_in(json_data) if self.json_data else json_data
