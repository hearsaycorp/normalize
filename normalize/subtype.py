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

from . import exc


class subtype(type):
    """A subtype is a special type object that can be used anywhere a
    regular type object is expected in normalize, but refers to a
    subset of all of the possible values of the type it is created
    from.  This allows additional checks for the value in a property
    which apply at the type coercion stage.
    """
    def __instancecheck__(cls, instance):
        try:
            ok = isinstance(instance, cls.of) and (
                all(where(instance) for where in cls.where_funcs)
            )
        except:
            ok = False
        return ok

    def __str__(cls):
        return "<%s %s of %s>" % (
            type(cls).__name__, cls.__name__, cls.of.__name__,
        )

    def __new__(typcls, name, of, where, coerce=None):
        if not isinstance(of, type):
            raise exc.SubtypeOfWhat(of=of)

        # for classes with a custom metaclass, we'll need to whip up a new
        # metaclass for them, then construct that.
        if not issubclass(typcls, type(of)):
            typcls = type(
                type(of).__name__ + typcls.__name__.capitalize(),
                (typcls, type(of)), {})
            return typcls(name, of, where, coerce)

        cls_a = []

        def __new__(cls, value):
            if isinstance(value, cls_a[0]):
                return value
            elif cls.coerce[0]:
                coerced = cls.coerce[0](value)
                if not isinstance(coerced, cls_a[0]):
                    raise exc.SubtypeCoerceError(
                        subtype=cls_a[0],
                        subtype_of=of,
                        passed=value,
                        coerced=coerced,
                    )
                return coerced
            else:
                raise exc.SubtypeNoCoerceFunc(
                    passed=value,
                    subtype=cls_a[0],
                    subtype_of=of,
                )

        cls_dict = dict(
            coerce=(coerce,),
            of=of,
            where_funcs=(where,),
            __new__=__new__,
        )

        cls = super(subtype, typcls).__new__(typcls, name, (of,), cls_dict)
        cls_a.append(cls)
        return cls

    def __init__(self, name, of, where, coerce=None):
        """Creates a new subtype constraint, and optionally associates with a
        coerce method.

        It's also possible to supply a 'coerce' method; this will be used
        as a 'constructor' for the new subtype, and will be passed values
        passed to the constructor which do not already pass the type
        constraint.  The returned value is also checked against the type
        constraint.

        Note that the subtype object does not support the constructor
        syntax of the restricted type.  It only supports a single
        constructor argument.
        """
        super(subtype, self).__init__(name, (of,), type(self).__dict__)
