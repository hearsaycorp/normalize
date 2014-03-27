from __future__ import absolute_import

from normalize.coll import DictCollection
from normalize.coll import ListCollection
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
from normalize.property.json import LazyJsonProperty
from normalize.property.json import SafeJsonProperty
from normalize.property.json import SafeJsonListProperty
from normalize.property.json import LazySafeJsonProperty
from normalize.record import Record
from normalize.record.meta import RecordMeta
from normalize.record.json import JsonRecord
from normalize.record.json import JsonRecordList
from normalize.selector import FieldSelector
from normalize.selector import FieldSelectorException


RecordList = ListCollection
JsonCollection = ListCollection


__all__ = [
    "DictCollection",
    "FieldSelector",
    "FieldSelectorException",
    "JsonCollection",  # deprecated - use JsonRecordList
    "JsonCollectionProperty",  # deprecated
    "JsonListProperty",
    "JsonProperty",
    "JsonRecord",
    "JsonRecordList",
    "LazyJsonProperty",
    "LazyProperty",
    "LazySafeJsonProperty",
    "LazySafeProperty",
    "ListCollection",
    "ListProperty",
    "Property",
    "ROProperty",
    "Record",
    "RecordList",
    "RecordMeta",
    "SafeJsonListProperty",
    "SafeJsonProperty",
    "SafeProperty",
    "make_property_type",
]
