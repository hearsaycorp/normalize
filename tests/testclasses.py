from datetime import datetime
import unittest

from normalize import (
    JsonCollectionProperty,
    JsonProperty,
    JsonRecord,
    Record,
    RecordList,
)


class MockChildRecord(JsonRecord):
    name = JsonProperty()


class MockDelegateJsonRecord(JsonRecord):
    other = JsonProperty()


class MockJsonRecord(JsonRecord):
    name = JsonProperty()
    age = JsonProperty(isa=int)
    seen = JsonProperty(
        json_name='last_seen', isa=datetime,
        coerce=lambda x: datetime.strptime(x, '%Y-%m-%dT%H:%M:%S'),
    )
    children = JsonCollectionProperty(of=MockChildRecord)


class MockExtraneousJsonRecord(JsonRecord):
    count = JsonProperty(isa=int)
    last_updated = JsonProperty(
        isa=datetime,
        coerce=lambda x: datetime.strptime(x, '%Y-%m-%dT%H:%M:%S'),
        extraneous=False,
    )


class MockRecordList(RecordList):
    itemtype = MockExtraneousJsonRecord
