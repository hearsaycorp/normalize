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
        return datetime(*(tt[0:6]))
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
        "__doc__": "A property which must hold a python date (or "
                   "datetime); coercion from string is provided via "
                   "``dateutil.parse``.  Note that datetime is a date "
                   "subclass, and supports all its methods, so a "
                   "DateProperty might contain a datetime instance.",
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


__all__ = tuple(k for k in globals().keys() if k.endswith("Property"))
