from __future__ import absolute_import

from normalize.property.json import JsonProperty
from normalize.property.json import JsonCollection
from normalize.property.json import JsonCollectionProperty
from normalize.record import Record
from normalize.record.meta import RecordMeta
from normalize.record.json import JsonRecord
from normalize.record.json import JsonListRecord
from normalize.selector import FieldSelector
from normalize.selector import FieldSelectorException


RecordList = JsonListRecord


__all__ = [
    "FieldSelector",
    "FieldSelectorException",
    "JsonCollection",
    "JsonCollectionProperty",
    "JsonListRecord",
    "JsonProperty",
    "JsonRecord",
    "Property",
    "Record",
    "RecordMeta",
]
