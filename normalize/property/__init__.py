
from __future__ import absolute_import

import inspect
import weakref

from normalize.property.meta import MetaProperty


class _Default():
    pass


_none = _Default()


class Property(object):
    """This is the base class for all property types.  It is a data descriptor,
    so care should be taken before adding any SPECIALMETHODS which might change
    the way it behaves.
    """
    __metaclass__ = MetaProperty

    def __init__(self, default=_none, traits=None, extraneous=False,
                 required=False, check=None, isa=None, coerce=None):
        self.name = None
        self.class_ = None
        super(Property, self).__init__()
        self.default = default
        if callable(default):
            args = inspect.getargspec(default)
            if not args.args:
                required_args = 0
            else:
                required_args = len(args.args)
                if args.defaults:
                    required_args -= len(args.defaults)
                if required_args > 1:
                    raise Exception(
                        "default functions may take 0 or 1 arguments"
                    )
            self.default_wants_arg = bool(required_args)
        self.required = required
        self.check = check
        self.valuetype = isa
        self.coerce = coerce or isa
        if self.coerce and not self.valuetype:
            raise Exception(
                "In order to coerce types, the intended type must be known; "
                "pass isa=TYPE or isa=(TYPE, TYPE, ...) to Property"
            )
        self.extraneous = extraneous

    @property
    def bound(self):
        return bool(self.class_)

    def bind(self, class_, name):
        self.name = name
        self.class_ = weakref.ref(class_)

    @property
    def fullname(self):
        if not self.bound:
            return "(unbound)"
        elif not self.class_():
            classname = "(GC'd class)"
        else:
            classname = self.class_().__name__
        return "%s.%s" % (classname, self.name)

    def type_safe_value(self, value):
        if value is None and self.required and not self.valuetype:
            raise ValueError("%s is required" % self.fullname)
        if self.valuetype and not isinstance(value, self.valuetype):
            value = self.coerce(value)
        if self.check and not self.check(value):
            raise ValueError(
                "%s value '%r' failed type check" % (self.fullname, value)
            )
        return value

    def get_default(self, obj):
        if callable(self.default):
            if self.default_wants_arg:
                rv = self.default(obj)
            else:
                rv = self.default()
        else:
            rv = self.default
        return rv

    def init_prop(self, obj, value=_Default):
        if value is _Default:
            value = self.get_default(obj)

        if value is _none:
            if self.required:
                raise ValueError("%s is required" % self.fullname)
        else:
            obj.__dict__[self.name] = self.type_safe_value(value)

    def eager_init(self):
        return self.required or self.default is not _none

    def __get__(self, obj, type_=None):
        """Default getter; does NOT fall back to regular descriptor behavior
        """
        if self.name not in obj.__dict__:
            raise AttributeError
        return obj.__dict__[self.name]

    def __repr__(self):
        metaclass = str(type(self).__name__)
        return "<%s %s>" % (metaclass, self.fullname)


class LazyProperty(Property):
    """This declares a property which has late evaluation using its 'default'
    method.  This type uses the support built-in to python for lazy attribute
    setting, which means subsequent attribute assignments will not be prevented
    or checked.  See LazySafeProperty for the descriptor version
    """
    __trait__ = "lazy"

    def __init__(self, lazy=True, **kwargs):
        if not lazy:
            raise Exception("To make an eager property, do not pass lazy")
        super(LazyProperty, self).__init__(**kwargs)

    def init_prop(self, obj, value=_Default):
        if value is _Default:
            return
        super(LazyProperty, self).init_prop(obj)

    def eager_init(self):
        return False

    def __get__(self, obj, type_=None):
        value = self.get_default(obj)

        obj.__dict__[self.name] = self.type_safe_value(value)
        return super(LazyProperty, self).__get__(obj, type_)


class ROProperty(Property):
    __trait__ = "ro"

    def __get__(self, obj, type_=None):
        return super(ROProperty, self).__get__(obj, type_)

    def __set__(self, obj, value):
        raise AttributeError("%s is read-only" % self.fullname)

    def __delete__(self, instance):
        """
        Note: instance is normally an instance of a Record
        """
        raise AttributeError("%s is read-only" % self.fullname)


class SlowLazyProperty(LazyProperty):
    __trait__ = "slow"

    def __get__(self, obj, type_=None):
        if self.name in obj.__dict__:
            return obj.__dict__[self.name]
        return super(SlowLazyProperty, self).__get__(obj, type_)


class ROLazyProperty(SlowLazyProperty, ROProperty):
    pass


class SafeProperty(Property):
    """A version of Property which always checks all assignments to
    properties"""
    __trait__ = "safe"

    def __set__(self, obj, value):
        obj.__dict__[self.name] = self.type_safe_value(value)

    def __delete__(self, obj):
        if self.required:
            raise ValueError("%s is required" % self.fullname)
        super(SafeProperty, self).__delete__(obj)


class LazySafeProperty(SafeProperty, SlowLazyProperty):
    pass


trait_num = 0


def make_property_type(name, base_type=Property,
                       attrs=None, trait_name=None,
                       *default_args, **default_kwargs):
    """Makes a new Property type, which supplies the given arguments as
    defaults to the Property() constructor.  Note: defaults which affect the
    property type returned cannot be supplied by this mechanism."""

    if not attrs:
        attrs = {}
    bases = base_type if isinstance(base_type, tuple) else (base_type,)
    self_type = []
    if not trait_name:
        global trait_num
        trait_num += 1
        trait_name = "trait%d" % trait_num

    def __init__(self, *args, **kwargs):
        if not len(args) and len(default_args):
            args = default_args
        for arg, val in default_kwargs.iteritems():
            if arg not in kwargs:
                kwargs[arg] = val
        return super(self_type[0], self).__init__(*args, **kwargs)

    attrs['__init__'] = __init__
    attrs['__trait__'] = trait_name

    new_property_type = type(name, bases, attrs)
    self_type.append(new_property_type)
    return new_property_type
