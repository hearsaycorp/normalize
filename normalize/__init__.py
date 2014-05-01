from __future__ import absolute_import

from normalize.coll import DictCollection
from normalize.coll import ListCollection
import normalize.exc as exc
from normalize.property import LazyProperty
from normalize.property import LazySafeProperty
from normalize.property import make_property_type
from normalize.property import Property
from normalize.property import ROProperty
from normalize.property import SafeProperty
from normalize.property.coll import ListProperty
from normalize.property.json import JsonProperty
from normalize.property.json import JsonListProperty
from normalize.property.json import JsonCollectionProperty
from normalize.property.json import SafeJsonProperty
from normalize.record import Record
from normalize.record.meta import RecordMeta
from normalize.record.json import from_json
from normalize.record.json import JsonRecord
from normalize.record.json import JsonRecordList
from normalize.record.json import to_json
from normalize.selector import FieldSelector
from normalize.selector import FieldSelectorException
from normalize.selector import MultiFieldSelector


RecordList = ListCollection
JsonCollection = ListCollection


__all__ = [
    "DictCollection",
    "exc",
    "FieldSelector",
    "FieldSelectorException",
    "from_json",
    "JsonCollection",  # deprecated - use JsonRecordList
    "JsonCollectionProperty",  # deprecated
    "JsonListProperty",
    "JsonProperty",
    "JsonRecord",
    "JsonRecordList",
    "LazyProperty",
    "LazySafeProperty",
    "ListCollection",
    "ListProperty",
    "make_property_type",
    "MultiFieldSelector",
    "Property",
    "ROProperty",
    "Record",
    "RecordList",
    "RecordMeta",
    "SafeJsonProperty",
    "SafeProperty",
    "to_json",
]
