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


class MockUnsanitizedJsonRecord(JsonRecord):
    count = JsonProperty(isa=int)
    last_updated = JsonProperty(
        isa=datetime,
        coerce=lambda x: datetime.strptime(x, '%Y-%m-%dT%H:%M:%S'),
        extraneous=False,
    )


class MockRecordList(RecordList):
    record_cls = MockUnsanitizedJsonRecord


def all_diff_types_equal(record, diff_type):
    """
    Returns True if the given Record's DiffType and Record's Properties'
    DiffTypes are the same as the specified DiffType.
    """
    if record.diff_type != diff_type:
        return False

    for field_name, prop in record._fields.iteritems():
        prop_diff_type = prop.get_diff_info(record).diff_type

        # Property doesn't have a DiffType
        if prop_diff_type is None:
            continue

        if prop_diff_type != diff_type:
            return False
        prop_value = getattr(record, field_name)
        if isinstance(prop_value, Record):
            if not all_diff_types_equal(prop_value, diff_type):
                return False
        #elif isinstance(prop_value, JsonCollectionProperty):
            #if not all(all_diff_types_equal(v, diff_type)
            #           for v in prop_value):
                #return False

    return True


class StructableTestCase(unittest.TestCase):
    def assertAllDiffTypesEqual(self, record, diff_type):
        self.assertTrue(all_diff_types_equal(record, diff_type))
