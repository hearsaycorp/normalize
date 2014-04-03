
"""Property objects are "new"-style object *data descriptors*.  They define
*getters* and *setters* for object attribute access, and allow the module to
hang on extra information and customize behavior.

For information on data descriptors, see the `Descriptor HowTo Guide
<https://docs.python.org/2/howto/descriptor.html>`_ in the main python
documentation.
"""

from __future__ import absolute_import

import inspect
import weakref

import normalize.exc as exc
from normalize.property.meta import MetaProperty


class _Default(object):
    def __repr__(self):
        return "<not set>"


_none = _Default()


class Property(object):
    """This is the base class for all property types.  It is a data descriptor,
    so care should be taken before adding any ``SPECIALMETHODS`` which might
    change the way it behaves.
    """
    __metaclass__ = MetaProperty

    def __init__(self, isa=None,  coerce=None, check=None,
                 required=False, default=_none, traits=None,
                 extraneous=False):
        """Declares a new standard Property.  Note: if you pass arguments which
        are not understood by this constructor, or pass extra property traits
        to ``traits``, then the call will be redirected to a sub-class; see
        :py:mod:`normalize.property.meta` for more.

        Because of this magic, all ``Property`` arguments *must* be passed in
        keyword argument form.  All arguments are optional.

            ``isa=``\ *TYPE|TUPLE*
                Any assigned property must be one of these types according to
                ``isinstance()``.  Also used by visitor functions which are
                missing an instance, such as marshal in.

                If ``isa`` is not set, then *any* value (including ``None``)
                is acceptable.

            ``coerce=``\ *FUNCTION*
                If the value fails the ``isa`` isinstance check, then this
                function is called with the value, and should return a value of
                a conformant type or throw an exception.

            ``check=``\ *FUNCTION*
                Once the value is of the correct type, this function is called
                and should return something true (according to ``bool()``) if
                the value is acceptable.

            ``required=``\ *BOOL*
                If ``True``, then the value must be passed during construction,
                and may not be ``None`` (this is only meaningful if ``isa=`` is
                not passed)

            ``default=``\ *VALUE|FUNCTION*
                If no value is passed during construction, then use this value
                instead.  If the argument is a function, then the function is
                called and the value it returns used as the default.

            ``traits=``\ *LIST|SEQUENCE*
                Manually specify a list of named Property traits.  The default
                is ``["safe"]``, and any unknown keyword arguments will add
                extra traits on.

            ``extraneous=``\ *BOOL*
                This Property is considered *denormalized* and does not affect
                the ``Record`` equality operator.  Visitor functions typically
                ignore extraneous properties or require an extra option to
                process them.
        """
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
                    raise exc.DefaultSignatureError(
                        func=default,
                        module=default.__module__,
                        nargs=required_args,
                    )
            self.default_wants_arg = bool(required_args)
        self.required = required
        self.check = check
        self.valuetype = isa
        self.coerce = coerce or isa
        if self.coerce and not self.valuetype:
            raise exc.CoerceWithoutType()
        self.extraneous = extraneous

    @property
    def bound(self):
        return bool(self.class_)

    def bind(self, class_, name):
        self.name = name
        self.class_ = weakref.ref(class_)

    @property
    def fullname(self):
        """Returns the name of the ``Record`` class this ``Property`` is
        attached to, and attribute name it is attached as."""
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
                # XXX - only 'lazy' properties should be allowed to do this.
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

    def __str__(self):
        metaclass = str(type(self).__name__)
        return "<%s %s>" % (metaclass, self.fullname)


class LazyProperty(Property):
    """This declares a property which has late evaluation using its 'default'
    method.  This type uses the support built-in to python for lazy attribute
    setting, which means subsequent attribute assignments will not be prevented
    or checked.  See LazySafeProperty for the descriptor version.
    """
    __trait__ = "lazy"

    def __init__(self, lazy=True, **kwargs):
        """Creates a Lazy property.  In addition to the standard Property
        arguments, accepts:

            ``lazy=``\ *BOOL*
                Must be ``True``. Used as a "distinguishing argument" to
                request a lazy Property. Not required if you call
                ``LazyProperty()`` directly.

            ``default=``\ *FUNCTION|METHOD*
                The default value for the property.  Unlike a standard
                ``Property``, the value can also be set to a method, which can
                reference other object properties.
        """
        if not lazy:
            raise exc.LazyIsFalse()
        super(LazyProperty, self).__init__(**kwargs)

    def init_prop(self, obj, value=_Default):
        if value is _Default:
            return
        super(LazyProperty, self).init_prop(obj, value)

    def eager_init(self):
        return False

    def __get__(self, obj, type_=None):
        """This getter is called when there is no value set, and calls the
        default method/function.
        """
        value = self.get_default(obj)

        obj.__dict__[self.name] = self.type_safe_value(value)
        return super(LazyProperty, self).__get__(obj, type_)


class ROProperty(Property):
    """A read-only property throws an exception when the attribute slot is
    assigned to"""
    __trait__ = "ro"

    def __set__(self, obj, value):
        """Raises ``ReadOnlyAttributeError``"""
        raise exc.ReadOnlyAttributeError(attrname=self.fullname)

    def __delete__(self, obj):
        """Raises ``ReadOnlyAttributeError``"""
        raise exc.ReadOnlyAttributeError(attrname=self.fullname)


class SlowLazyProperty(LazyProperty):
    """Base class used by LazySafeProperty and ROLazyProperty"""
    __trait__ = "slow"

    def __get__(self, obj, type_=None):
        """This getter checks to see if the slot is already set in the object
        and if so, returns it."""
        if self.name in obj.__dict__:
            return obj.__dict__[self.name]
        return super(SlowLazyProperty, self).__get__(obj, type_)


class ROLazyProperty(SlowLazyProperty, ROProperty):
    pass


class SafeProperty(Property):
    """A version of Property which always checks all assignments to
    properties.

    Normalize gives you safe properties by default; if you want unsafe
    properties, then you (currently) need to pass ``traits=["unsafe"]`` to the
    ``Property()`` declaration.
    """
    __trait__ = "safe"

    def __set__(self, obj, value):
        """This setter checks the type of the value before allowing it to be
        set."""
        obj.__dict__[self.name] = self.type_safe_value(value)

    def __delete__(self, obj):
        """Checks the property's ``required`` setting, and allows the delete if
        it is false"""
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
