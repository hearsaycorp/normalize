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


def make_subtype(of, called, where, coerce=None):
    """Creates a new subtype constraint, and optionally associates with a
    coerce method.

    A subtype constraint is a special type object that can be used
    anywhere a regular type object is expected in normalize, but
    refers to a subset of all of the possible values of the type it is
    created from.  This allows the rules in the passed 'where'
    function to be depended upon in calling code without writing
    custom constructor functions.

    It's also possible to supply a 'coerce' method; this will be used
    as a 'constructor' for the new subtype, and will be passed values
    passed to the constructor which do not already pass the type
    constraint.  The returned value is also checked against the type
    constraint.

    Note that the subtype object does not support the constructor
    syntax of the restricted type.  It only supports a single
    constructor argument.
    """
    if not isinstance(of, type):
        raise exc.SubtypeOfWhat(of=of)
    if isinstance(type(of), subtype):
        where_funcs = type(of).where_funcs + (where,)
        if not coerce:
            coerce = type(of).coerce[0]
    else:
        where_funcs = (where,)

    cls_a = []

    def __new__(cls, value):
        if isinstance(value, cls_a[0]):
            return value
        elif cls.coerce[0]:
            coerced = cls.coerce[0](value)
            if not isinstance(coerced, cls_a[0]):
                raise exc.SubtypeCoerceError(
                    subtype_name=called,
                    subtype_of=of.__name__,
                    passed=value,
                    coerced=coerced,
                )
            return coerced
        else:
            raise exc.SubtypeNoCoerceFunc(
                passed=value,
                subtype_name=called,
                subtype_of=of.__name__,
            )

    subtype_f = subtype
    # for classes with a custom metaclass, we'll need to whip up a new
    # metaclass for them as well.
    if not issubclass(subtype, type(of)):
        subtype_f = type(
            type(of).__name__ + "Subtype", (subtype, type(of)), {})

    cls_dict = dict(
        coerce=(coerce,),
        of=of,
        where_funcs=where_funcs,
        __new__=__new__,
    )

    cls = subtype_f(called, (of,), cls_dict)
    cls_a.append(cls)
    return cls
