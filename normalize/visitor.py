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

from normalize.coll import Collection
import normalize.exc as exc
from normalize.record import Record
from normalize.selector import FieldSelector


class Visitor(object):
    """Class for writing Record visitor pattern functions.  This Visitor is
    intended to be subclassed; a generic version which can take the apply and
    reduce functions as arguments may be implemented later.
    """
    def __init__(self, ignore_none=True, ignore_empty_string=False,
                 apply_records=False, apply_empty_slots=False):
        """Create a new visitor.  The built-in parameters, which affect the
        default 'map' function operation, are:

        ``ignore_none`` (bool)
            If the 'apply' function returns ``None``, treat it as if the
            slot or object did not exist.  On by default.

        ``ignore_empty_string`` (bool)
            If the 'apply' function returns the empty string, treat it as if
            the slot or object did not exist.  Not on by default.

        ``apply_records`` (bool)
            Normally, traversal happens in depth-first order, and fields
            which are Records never have ``apply`` called on them.  If you
            want them to, set this field.  This affects the arguments passed
            to ``reduce_record``
            If the ``apply`` function returns
            ``self.StopVisiting`` (or an instance of it), then traversal
            does not descend into the fields of the record.  If it returns
            something else, then ``reduce_record`` is expected to take a
            tuple of the return value, and the dictio

        """
        self.ignore_none = ignore_none
        self.ignore_empty_string = ignore_empty_string
        self.apply_records = apply_records
        self.apply_empty_slots = apply_empty_slots

    def apply(self, value, fs, prop=None, parent_obj=None):
        """'apply' is a general place to put a function which is called
        on every extant record slot.

        Data structures are normally traversed in depth-first order.
        """
        pass

    def reduce_record(self, result_dict, fs, record_type):
        """Hook called for each record, with the results of mapping each
        member."""
        return result_dict

    def reduce_collection(self, result_coll_generator, fs, coll_type):
        """Hook called for each normalize.coll.Collection.  The first argument
        is a generator, which returns (key, value) pairs (like
        Collection.itertuples())
        """
        return coll_type.tuples_to_coll(result_coll_generator, coerce=False)

    def reduce_complex(self, record_result, coll_result, fs, value_type):
        """If a Collection has properties that map to something, this
        reduction."""
        if record_result.get("values", False):
            raise exc.VisitorTooSimple(
                fs=fs,
                value_type_name=value_type.__name__,
                visitor=type(self).__name__,
            )
        record_result['values'] = coll_result
        return record_result

    class StopVisiting(object):
        return_value = None

        def __init__(self, return_value):
            self.return_value = return_value

    def map(self, value, fs=None, value_type=None):
        if not fs:
            fs = FieldSelector([])
        if not value_type:
            value_type = type(value)

        prune = False

        if issubclass(value_type, Record):
            record_mapped = self.map_record(value, fs, value_type)

            if record_mapped == self.StopVisiting or isinstance(
                record_mapped, self.StopVisiting
            ):
                record_mapped = record_mapped.return_value
                prune = True

        if not prune and issubclass(value_type, Collection):
            coll_mapped = self.reduce_collection(
                self.map_collection(value, fs, value_type), fs, value_type,
            )

            if coll_mapped and record_mapped:
                return self.reduce_complex(
                    record_mapped, coll_mapped, fs, value_type,
                )
            elif coll_mapped:
                return coll_mapped

        return record_mapped

    def map_record(self, record, fs, record_type):
        """Function responsible for descending an object.
        """
        if not record_type:
            record_type = type(record)
        if not fs:
            fs = FieldSelector([])

        if self.apply_records:
            result = self.apply(record, fs, None, None)
            if result == self.StopVisiting or \
                    isinstance(result, self.StopVisiting):
                return result.return_value

        result_dict = dict()

        for name, prop in record_type.properties.iteritems():
            mapped = self.map_prop(record, prop, fs)
            if mapped is None and self.ignore_none:
                pass
            elif mapped == "" and self.ignore_empty_string:
                pass
            else:
                result_dict[name] = mapped

        to_reduce = (
            result_dict if not self.apply_records or result is None else
            (result, result_dict)
        )

        return self.reduce_record(to_reduce, fs, record_type)

    def map_prop(self, record, prop, fs):
        if self.apply_empty_slots or hasattr(record, prop.name):
            try:
                value = prop.__get__(record)
            except AttributeError:
                value = None
            fs = fs + [prop.name]
            value_type = prop.valuetype or type(value)
            if issubclass(value_type, Record):
                mapped = self.map(value, fs, value_type)
            else:
                mapped = self.apply(value, fs, prop, record)

            return mapped

    def map_collection(self, coll, fs, coll_type):
        try:
            generator = coll.itertuples()
        except AttributeError:
            generator = coll_type.coll_to_tuples(coll)

        for key, value in generator:
            mapped = self.map(value, fs + [key], coll_type.itemtype)
            if mapped is None and self.ignore_none:
                pass
            elif mapped == "" and self.ignore_empty_string:
                pass
            else:
                yield key, mapped
