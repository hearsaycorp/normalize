
from . import make_property_type

IntProperty = make_property_type(
    "IntProperty", isa=int, trait_name="int",
)
StringProperty = make_property_type(
    "StringProperty", isa=basestring, coerce=str, trait_name="str",
)
FloatProperty = make_property_type(
    "FloatProperty", isa=float, trait_name="float",
)
UnicodeProperty = make_property_type(
    "UnicodeProperty", base_type=StringProperty,
    isa=unicode, coerce=unicode, trait_name="unicode",
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
