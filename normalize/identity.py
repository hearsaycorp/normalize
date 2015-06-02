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

import normalize.coll
import normalize.exc as exc
import normalize.record


def record_id(object_, type_=None, selector=None, normalize_object_slot=None):
    """Implementation of id() which is overridable and knows about record's
    primary_key property.  Returns if the two objects may be the "same";
    returns None for other types, meaning all bets about identity are off.

    Curiously, this function resembles conversion between a "record" and a
    "tuple": stripping the logical names from the atomic values.
    """
    if type_ is None or isinstance(type_, tuple):
        type_ = type(object_)

    key_vals = list()
    if hasattr(type_, "primary_key"):
        pk_cols = type_.primary_key
    elif object_.__hash__:
        return object_
    else:
        raise exc.IdentityCrisis(
            val=object_,
            val_repr=repr(object_),
            val_type=type_,
            val_type_name=type_.__name__,
        )
    if selector and pk_cols and not all(
        selector[(x.name,)] for x in pk_cols
    ):
        pk_cols = None

    if not pk_cols and issubclass(
        type_, normalize.coll.Collection
    ):
        # FIXME: unordered collections will rarely match each other
        gen = (
            object_.itertuples() if hasattr(object_, "itertuples") else
            type_.coll_to_tuples(object_)
        )
        return tuple(
            record_id(
                v, type_.itemtype, selector[k], normalize_object_slot,
            ) for k, v in gen if selector[(k,)]
        ) if selector else tuple(
            record_id(v, type_.itemtype, None, normalize_object_slot) for
            k, v in gen
        )

    if not pk_cols:
        all_properties = type_._sorted_properties
        if selector:
            all_properties = tuple(
                x for x in all_properties if selector[(x.name,)]
            )

    for prop in pk_cols or all_properties:
        val = getattr(object_, prop.name, None)
        if normalize_object_slot:
            val = normalize_object_slot(val, prop, object_)
        _none = (
            normalize_object_slot(None, prop, object_) if
            normalize_object_slot else None
        )
        if val is not _none and prop.valuetype:
            value_type_list = (
                prop.valuetype if isinstance(prop.valuetype, tuple) else
                (prop.valuetype,)
            )
            val_pk = ()
            set_elements = 0
            for value_type in value_type_list:
                if issubclass(value_type, normalize.record.Record):
                    pk = record_id(val, value_type,
                                   selector[prop.name] if selector else None,
                                   normalize_object_slot)
                    pk_elements = len([x for x in pk if x is not None])
                    if not val_pk or pk_elements > set_elements:
                        val_pk = pk
                        set_elements = pk_elements

            val_pk = val_pk or val
            try:
                val_pk.__hash__()
            except TypeError:
                raise exc.KeyHashError(
                    prop=str(prop),
                    typename=type_.__name__,
                )
            key_vals.append(val_pk)
        else:
            key_vals.append(val)

    return tuple(key_vals)
