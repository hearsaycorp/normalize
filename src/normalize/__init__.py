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

from normalize.coll import DictCollection
from normalize.coll import ListCollection
from normalize.diff import DiffOptions
from normalize.diff import DiffTypes
import normalize.exc as exc
from normalize.property import LazyProperty
from normalize.property import LazySafeProperty
from normalize.property import make_property_type
from normalize.property import Property
from normalize.property import ROProperty
from normalize.property import SafeProperty
from normalize.property import V1Property
from normalize.property.coll import DictProperty
from normalize.property.coll import ListProperty
from normalize.property.json import JsonProperty
from normalize.property.json import JsonDictProperty
from normalize.property.json import JsonListProperty
from normalize.property.json import JsonCollectionProperty
from normalize.property.json import SafeJsonProperty
from normalize.property.types import DateProperty
from normalize.property.types import DatetimeProperty
from normalize.property.types import FloatProperty
from normalize.property.types import IntegerProperty
from normalize.property.types import IntProperty
from normalize.property.types import LongProperty
from normalize.property.types import NumberProperty
from normalize.property.types import StringProperty
from normalize.property.types import UnicodeProperty
from normalize.record import Record
from normalize.record.meta import RecordMeta
from normalize.record.json import AutoJsonRecord
from normalize.record.json import from_json
from normalize.record.json import JsonRecord
from normalize.record.json import JsonRecordList
from normalize.record.json import NCAutoJsonRecord
from normalize.record.json import to_json
from normalize.selector import FieldSelector
from normalize.selector import FieldSelectorException
from normalize.selector import MultiFieldSelector
from normalize.subtype import subtype
from normalize.visitor import Visitor
from normalize.visitor import VisitorPattern


RecordList = ListCollection
JsonCollection = ListCollection


__all__ = [
    "AutoJsonRecord",
    "DateProperty",
    "DatetimeProperty",
    "DictCollection",
    "DictProperty",
    "DiffOptions",
    "DiffTypes",
    "exc",
    "FieldSelector",
    "FieldSelectorException",
    "FloatProperty",
    "from_json",
    "IntegerProperty",
    "IntProperty",
    "JsonCollection",  # deprecated - use JsonRecordList
    "JsonCollectionProperty",  # deprecated
    "JsonDictProperty",
    "JsonListProperty",
    "JsonProperty",
    "JsonRecord",
    "JsonRecordList",
    "LazyProperty",
    "LazySafeProperty",
    "ListCollection",
    "ListProperty",
    "LongProperty",
    "make_property_type",
    "MultiFieldSelector",
    "NCAutoJsonRecord",
    "NumberProperty",
    "Property",
    "ROProperty",
    "Record",
    "RecordList",
    "RecordMeta",
    "SafeJsonProperty",
    "SafeProperty",
    "StringProperty",
    "subtype",
    "to_json",
    "UnicodeProperty",
    "V1Property",
    "Visitor",
    "VisitorPattern",
]
