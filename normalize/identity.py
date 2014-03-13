import normalize.coll
import normalize.record


def record_id(object_, type_=None):
    """Implementation of id() which is overridable and knows about record's
    primary_key property.  Returns if the two objects may be the "same";
    returns None for other types, meaning all bets about identity are off.

    Curiously, this function resembles conversion between a "record" and a
    "tuple": stripping the logical names from the atomic values.
    """
    if type_ is None:
        type_ = type(object_)
    key_vals = list()

    for prop in type_.primary_key or type_._sorted_properties:
        val = getattr(object_, prop.name, None)
        value_type = prop.valuetype
        if val is not None and value_type:
            if issubclass(value_type, normalize.record.Record):
                val = getattr(val, "__pk__", record_id(val, value_type))
            elif issubclass(value_type, normalize.coll.Collection):
                val = tuple(record_id(x, prop.itemtype) for x in val)
        key_vals.append(val)
    return tuple(key_vals)
