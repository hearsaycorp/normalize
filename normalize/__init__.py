from __future__ import absolute_import

from normalize.property import Property
from normalize.property.json import JsonProperty
from normalize.property.json import JsonCollectionProperty
from normalize.record import Record
from normalize.coll import ListCollection
from normalize.record.meta import RecordMeta
from normalize.record.json import JsonRecord
from normalize.record.json import JsonRecordList
from normalize.selector import FieldSelector
from normalize.selector import FieldSelectorException


RecordList = ListCollection
JsonCollection = ListCollection


__all__ = [
    "FieldSelector",
    "FieldSelectorException",
    "JsonCollection",
    "JsonCollectionProperty",
    "JsonRecordList",
    "JsonProperty",
    "JsonRecord",
    "Property",
    "Record",
    "RecordList",
    "RecordMeta",
]
