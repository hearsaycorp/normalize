"""``normalize.property.types`` provides an assortment of pre-generated
types"""

from datetime import date
from datetime import datetime
from sys import maxint

from . import make_property_type

try:
    from dateutil.parser import parse as parse_datetime
except ImportError:
    formats = {
        6: "%y%m%d",
        8: "%Y%m%d",
        13: "%Y%m%d%H:%M",
        14: "%Y%m%d%H:%MZ",
        16: "%Y%m%d%H:%M:%S",
        17: "%Y%m%d%H:%M:%SZ",
    }

    def parse_datetime(not_a_datetime):
        datetime_stripped = not_a_datetime.replace(
            "-", "").replace("T", "").replace(" ", "")
        if len(datetime_stripped) in formats:
            return datetime.strptime(
                datetime_stripped, formats[len(datetime_stripped)],
            )
        else:
            raise Exception(
                "``dateutil`` not installed, so can't parse %r" %
                not_a_datetime
            )


IntProperty = make_property_type(
    "IntProperty", isa=int, trait_name="int",
    attrs={
        "__doc__": "A property which must be an ``int``",
    },
)
LongProperty = make_property_type(
    "LongProperty", isa=long, trait_name="long",
    attrs={
        "__doc__": "A property which must be a ``long``",
    },
)
IntegerProperty = make_property_type(
    "IntegerProperty", isa=(int, long), trait_name="integer",
    coerce=lambda x: (
        int(x) if abs(float(x)) < maxint else long(x)
    ),
    attrs={
        "__doc__": "A property which may be either an int or a long",
    },
)
StringProperty = make_property_type(
    "StringProperty", isa=basestring, coerce=str, trait_name="str",
    attrs={
        "__doc__": "A property which must be a ``basestring``, and if "
                   "not, it is coerced using ``str``",
    },
)
FloatProperty = make_property_type(
    "FloatProperty", isa=float, trait_name="float",
    attrs={
        "__doc__": "A property which must be a floating point number.",
    },
)
UnicodeProperty = make_property_type(
    "UnicodeProperty", base_type=StringProperty,
    isa=unicode, coerce=unicode, trait_name="unicode",
    attrs={
        "__doc__": "A property which must be a ``unicode``, and if "
                   "not, it is coerced using ``unicode``",
    },
)


def coerce_datetime(not_a_datetime):
    if isinstance(not_a_datetime, date):
        tt = not_a_datetime.timetuple()
        return datetime(tt[0:6])
    elif isinstance(not_a_datetime, basestring):
        return parse_datetime(not_a_datetime)
    else:
        raise ValueError(
            "Cannot coerce %r to a date/datetime" % not_a_datetime
        )


def coerce_date(not_a_date):
    if isinstance(not_a_date, datetime) or (
        hasattr(not_a_date, "date") and callable(not_a_date.date)
    ):
        return not_a_date.date()
    else:
        return coerce_datetime(not_a_date).date()


DateProperty = make_property_type(
    "DateProperty",
    trait_name="date", isa=date, coerce=coerce_date,
    attrs={
        "__doc__": "A property which must holds a python date; coercion "
                   "from string is provided via ``dateutil.parse``",
    },
)
DatetimeProperty = make_property_type(
    "DatetimeProperty",
    trait_name="datetime", isa=datetime,
    coerce=coerce_datetime,
    attrs={
        "__doc__": "A property which must holds a python datetime.  "
                   "Correct timezone handling is currently TODO and "
                   "users should not depend on timezone behavior until "
                   "this message is removed (submit tests and a patch!)",
    },
)


# now, go and generate ROLazyUnicodeProperty, SafeStringProperty etc
_prop_types = dict((k, v) for k, v in globals().iteritems() if
                   k.endswith("Property"))

from . import LazyProperty
from . import ROLazyProperty
from . import ROProperty
from . import SafeProperty
from . import SlowLazyProperty

_variants = {
    "Lazy": LazyProperty,
    "RO": ROProperty,
    "ROLazy": ROLazyProperty,
    "Safe": SafeProperty,
    "SlowLazy": SlowLazyProperty,
}

for name, proptype in _prop_types.iteritems():
    for prefix, variant in _variants.iteritems():
        typename = prefix + name
        globals()[typename] = type(typename, (proptype, variant), {})

__all__ = tuple(k for k in globals().keys() if k.endswith("Property"))
