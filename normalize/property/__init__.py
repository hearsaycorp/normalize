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


"""Property objects are "new"-style object *data descriptors*.  They define
*getters* and *setters* for object attribute access, and allow the module to
hang on extra information and customize behavior.

For information on data descriptors, see the `Descriptor HowTo Guide
<https://docs.python.org/2/howto/descriptor.html>`_ in the main python
documentation.
"""

from __future__ import absolute_import

import inspect
import warnings
import weakref

import normalize.empty as empty
import normalize.exc as exc
from normalize.property.meta import looks_like_v1_none
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
    __safe_unless_ro__ = False

    def __init__(self, isa=None,  coerce=None, check=None,
                 required=False, default=_none, traits=None,
                 extraneous=False, empty_attr=_none,
                 doc=None):
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

            ``empty_attr=``\ *METHODNAME*
                (deprecated) Specify an auxiliary method name which
                returns the value if the attribute is set, otherwise
                an ``empty`` proxy value.  Defaults to the name of the
                attribute with a ``0`` appended, or ``None`` if the
                attribute already ends with a number (disabling the
                accessor)

            ``extraneous=``\ *BOOL*
                This Property is considered *denormalized* and does not affect
                the ``Record`` equality operator.  Visitor functions typically
                ignore extraneous properties or require an extra option to
                process them.

            ``doc=``\ *STR*
                Specify a docstring for the property.

        """
        self.name = None
        self.class_ = None
        self.__doc__ = doc
        super(Property, self).__init__()
        self.default = default
        if callable(default):
            is_method, nargs = self.func_info(default)
            if nargs:
                if not is_method and nargs == 1:
                    # backwards compatibility; default=lambda x: x.foo was
                    # permitted previously.
                    stacklevel = 1

                    # walk stack back to the actual caller of the original
                    # constructor
                    stack = inspect.stack()
                    while stacklevel <= len(stack):
                        loc = stack[stacklevel - 1][0].f_locals
                        if 'self' not in loc or loc['self'] != self:
                            break
                        stacklevel += 1
                    warnings.warn(
                        "'default' first argument should be called 'self'",
                        stacklevel=stacklevel,
                    )
                    is_method = True
                else:
                    raise exc.DefaultSignatureError(
                        func=default,
                        module=default.__module__,
                        nargs=nargs,
                    )
            self.default_is_method = is_method
        self.required = required
        self.check = check
        self.valuetype = isa
        self.coerce = coerce or isa
        if self.coerce and not self.valuetype:
            raise exc.CoerceWithoutType()
        self.empty_attr = empty_attr
        self.extraneous = extraneous

    def func_info(self, func):
        args = inspect.getargspec(func)
        is_method = False
        if not args.args:
            required_args = 0
        else:
            required_args = len(args.args)
            if args.defaults:
                required_args -= len(args.defaults)
            if required_args and args.args[0] == "self":
                is_method = True
                required_args -= 1
        return is_method, required_args

    @property
    def bound(self):
        return bool(self.class_)

    def set_name(self, name):
        self.name = name
        if self.empty_attr is _none:
            self.empty_attr = (
                (name + "0") if name[-1] not in "0123456789" else None
            )

    def bind(self, class_):
        self.class_ = weakref.ref(class_)

    @property
    def fullname(self):
        """Returns the name of the ``Record`` class this ``Property`` is
        attached to, and attribute name it is attached as."""
        if not self.bound:
            if self.name is not None:
                return "(unbound).%s" % self.name
            else:
                return "(unbound)"
        elif not self.class_():
            classname = "(GC'd class)"
        else:
            classname = self.class_().__name__
        return "%s.%s" % (classname, self.name)

    def type_safe_value(self, value, _none_ok=False):
        if value is None and self.required and not self.valuetype:
            raise exc.PropertyRequired(prop=self)
        if self.valuetype and not isinstance(value, self.valuetype):
            try:
                new_value = self.coerce(value)
            except exc.SubtypeCoerceError as e:
                # this particular coerce error will be re-caught below,
                # unless the coerce method returned None
                new_value = e.coerced
            except Exception as e:
                raise exc.CoerceError(
                    prop=self,
                    passed=value,
                    exc=e,
                    func=(
                        "%s constructor" % self.coerce.__name__ if
                        isinstance(self.coerce, type) else self.coerce
                    ),
                    valuetype=(
                        "(" + ", ".join(
                            x.__name__ for x in self.valuetype
                        ) + ")" if isinstance(self.valuetype, tuple) else
                        self.valuetype.__name__
                    ),
                )
            if not isinstance(new_value, self.valuetype):
                if _none_ok and new_value is None and not self.required:
                    # allow coerce functions to return 'None' to silently
                    # swallow optional properties on initialization
                    return _none
                else:
                    raise exc.ValueCoercionError(
                        prop=self,
                        passed=value,
                        coerced=new_value,
                    )
            else:
                value = new_value
        if self.check and not self.check(value):
            raise exc.ValueCheckError(
                prop=self,
                passed=value,
            )
        return value

    def get_default(self, obj):
        if callable(self.default):
            if self.default_is_method:
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

        new_value = (
            _none if value is _none else
            self.type_safe_value(value, _none_ok=True)
        )

        if new_value is _none:
            if self.required:
                raise exc.PropertyRequired(prop=self)
        else:
            obj.__dict__[self.name] = new_value

    def eager_init(self):
        return self.required or self.default is not _none

    def attribute_error_hook(self):
        raise AttributeError(self.fullname)

    def __get__(self, obj, type_=None):
        """Default getter; does NOT fall back to regular descriptor behavior
        """
        if obj is None:
            return self
        if self.name not in obj.__dict__:
            return self.attribute_error_hook()
        return obj.__dict__[self.name]

    def slot_is_empty(self, obj):
        return self.name not in obj.__dict__

    def __str__(self):
        metaclass = str(type(self).__name__)
        return "<%s %s>" % (metaclass, self.fullname)

    def aux_props(self):
        """This method is available for property traits to provide extra class
        attributes which are added to the class they are defined in during
        class creation.  The default implementation is responsible for defining
        ``empty_attr`` attributes.

        The return value should be an iterable list of 2-tuples, with the first
        member of each 2-tuple being the attribute name and the second being
        the value to insert.
        """
        if self.empty_attr is not None:
            return ((self.empty_attr, EmptyAuxProp(self)), )
        else:
            return ()


class EmptyAuxProp(object):
    def __init__(self, prop):
        self.prop = prop
        self.valuetype = prop.valuetype or any

    def __get__(self, obj, type_=None):
        try:
            return self.prop.__get__(obj)
        except AttributeError:
            return empty.placeholder(self.valuetype)


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
        if obj is None:
            return self

        if self.name not in obj.__dict__:
            value = self.get_default(obj)
            obj.__dict__[self.name] = self.type_safe_value(value)

        return super(LazyProperty, self).__get__(obj, type_)

    def slot_is_empty(self, obj):
        return False


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


class ROLazyProperty(LazyProperty, ROProperty):
    def __get__(self, obj, type_=None):
        """This getter checks to see if the slot is already set in the object
        and if so, returns it."""
        if obj is None:
            return self
        if self.name in obj.__dict__:
            return obj.__dict__[self.name]
        return super(ROLazyProperty, self).__get__(obj, type_)


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
            raise exc.PropertyRequired(prop=self)
        del obj.__dict__[self.name]


class LazySafeProperty(SafeProperty, LazyProperty):
    def __get__(self, obj, type_=None):
        """This getter checks to see if the slot is already set in the object
        and if so, returns it."""
        if obj is None:
            return self
        if self.name in obj.__dict__:
            return obj.__dict__[self.name]
        return super(LazySafeProperty, self).__get__(obj, type_)


class V1Property(SafeProperty):
    __trait__ = "v1"

    def __init__(self, v1_none=_none, **kwargs):
        """Passing 'v1_none=None' or declaring with 'V1Property' will
        suppress AttributeError when the attribute is not set.
        """
        if not v1_none.__hash__:
            raise exc.NoneMutable(passed=v1_none)
        self.v1_upgraded = False
        if v1_none is _none and 'default' in kwargs and \
               looks_like_v1_none(kwargs['default']):
            v1_none = kwargs['default']
            del kwargs['default']
            self.v1_upgraded = True
        super(V1Property, self).__init__(**kwargs)
        self.v1_none = None if v1_none is _none else v1_none
        if self.empty_attr is _none and not self.v1_upgraded:
            self.empty_attr = None

    def slot_is_empty(self, obj):
        if self.v1_upgraded:
            return False
        return super(V1Property, obj).slot_is_empty(obj)

    def attribute_error_hook(self):
        return self.v1_none

    def __set__(self, obj, value):
        """This setter checks the type of the value before allowing it to be
        set."""
        try:
            super(V1Property, self).__set__(obj, value)
        except exc.CoercionError:
            if value is None or value == self.v1_none:
                self.__delete__(obj)
            else:
                raise


class DiffasProperty(Property):
    __trait__ = "diffas"

    def __init__(self, compare_as=None, **kwargs):
        """Specify ``compare_as=`` to pass a clean-up function which is applied
        to the value in the slot, but only during comparison.
        The function can be a method, and can choose to either accept or not
        accept an argument.
        """
        super(DiffasProperty, self).__init__(**kwargs)
        self.compare_as = compare_as
        is_method, nargs = self.func_info(compare_as)
        self.compare_as_info = is_method, nargs
        if nargs > 1:
            raise exc.CompareAsSignatureError(
                func=compare_as,
                module=compare_as.__module__,
                nargs=nargs,
            )


trait_num = 0


def make_property_type(name, base_type=Property,
                       attrs=None, trait_name=None,
                       **default_kwargs):
    """Makes a new ``Property`` type, which supplies the given arguments
    as defaults to the ``Property()`` constructor.

    The typical use of this function is to make types for the API you are
    mapping so that, for instance, any time they use a date you can convert
    it in a consistent way to a ``datetime.date``.

    It's also used by :py:mod:`normalize.property.types` to create all
    of its Property subclasses.

    Args:
        ``name=``\ *STR*
            Specifies the name of the new property type.  This is entirely
            cosmetic, but it is probably a good idea to make this exactly
            the same as the symbol you are assigning the result to.

        ``base_type=``\ *Property sub-class*
            Specifies which property type you are adding defaults to.
            You can pass in a tuple of types here.

        ``attrs=``\ *DICT*
            This lets you pass in a dictionary that will be used as
            the new Property type's class dictionary.  i.e., it gets
            passed as the third argument to ``type(NAME, BASES, ATTRS)``,
            after the properties necessary to implement the defaults
            are added to it.  If you use this for anything less than
            trivial, it may be simpler just to make a whole class
            definition.

        ``trait_name=``\ *STR*
            Specify the unique identifier of the trait that is created.
            This probably doesn't matter, unless you want to use the
            ``traits=`` keyword to ``Property()``.  The default is to
            make up a new numbered trait name, starting with "``trait1``".

        ``**kwargs``
            Everything not known is used as defaults for the eventual
            call to ``Property()``.  If the user of the Property type
            passes it as well, this overrides the defaults passed to
            ``make_property_type``.
    """

    if not attrs:
        attrs = {}
    bases = base_type if isinstance(base_type, tuple) else (base_type,)
    self_type = []
    if not trait_name:
        global trait_num
        trait_num += 1
        trait_name = "trait%d" % trait_num

    def __init__(self, **kwargs):
        for arg, val in default_kwargs.iteritems():
            if arg not in kwargs:
                kwargs[arg] = val
        return super(self_type[0], self).__init__(**kwargs)

    attrs['default_kwargs'] = default_kwargs
    attrs['__init__'] = __init__
    attrs['__trait__'] = trait_name

    new_property_type = type(name, bases, attrs)
    self_type.append(new_property_type)
    return new_property_type
