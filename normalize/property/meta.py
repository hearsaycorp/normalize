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

from collections import defaultdict
import inspect

import normalize.exc as exc


PROPERTY_TYPES = dict()

# Duck typing kwargs... for picking the right Property sub-class to instantiate
# based on the kwargs used in the Property() constructor
DUCKWARGS = defaultdict(set)


# a test for whether a value passed to 'default' is sufficient to qualify the
# attribute for v1 upgrade
def looks_like_v1_none(value):
    return not value and value.__hash__ and not callable(value)


def has(selfie, self, args, kwargs):
    """This is called 'has' but is called indirectly.  Each Property sub-class
    is installed with this function which replaces their __new__.

    It is called 'has', because it runs during property declaration, processes
    the arguments and is responsible for returning an appropriate Property
    subclass.  As such it is identical to the 'has' function in Perl's Moose.
    The API does not use the word, but the semantics are the same.

    It is responsible for picking which sub-class of 'self' to invoke.
    Unlike Moose, it will not dynamically create property types; if a type
    does not exist it will be a hard error.

    This function should *only* be concerned with picking the appropriate
    object type, because unlike in Perl, python cannot re-bless objects from
    one class to another.
    """
    if args:
        raise exc.PositionalArgumentsProhibited()
    extra_traits = set(kwargs.pop('traits', tuple()))

    safe_unless_ro = self.__safe_unless_ro__ or any(
        x in kwargs for x in ("required", "isa", "check")
    )
    # detect initializer arguments only supported by a subclass and add
    # them to extra_traits
    for argname in kwargs:
        if argname not in self.all_duckwargs:
            # initializer does not support this arg.  Do any subclasses?
            implies_traits = set()
            for traits, proptype in DUCKWARGS[argname]:
                if isinstance(proptype, type(self)):
                    implies_traits.add(traits)
                    if proptype.__safe_unless_ro__:
                        safe_unless_ro = True
            if len(implies_traits) > 1:
                raise exc.AmbiguousPropertyTraitArg(
                    trait_arg=argname,
                    could_be=" ".join(
                        sorted(x.__name__ for x in implies_traits)
                    ),
                    matched_traits=implies_traits,
                )
            elif not implies_traits:
                raise exc.PropertyArgumentNotKnown(
                    badkwarg=argname,
                    badkwarg_value=kwargs[argname],
                    proptypename=self.__name__,
                    proptype=self,
                )
            else:
                extra_traits.update(list(implies_traits)[0])

    all_traits = set(self.traits) | extra_traits

    if "unsafe" in all_traits and "safe" not in all_traits:
        all_traits.remove("unsafe")
    elif "ro" not in all_traits and safe_unless_ro:
        all_traits.add("safe")

    if "v1" not in all_traits:
        if 'default' in kwargs and looks_like_v1_none(kwargs['default']):
            all_traits.add("v1")
            if 'safe' not in all_traits:
                all_traits.add("safe")

    trait_set_key = tuple(sorted(all_traits))

    if trait_set_key not in PROPERTY_TYPES:
        create_property_type_from_traits(trait_set_key)
    property_type = PROPERTY_TYPES[trait_set_key]
    if not isinstance(property_type, type(self)):
        raise exc.PropertyTypeMismatch(
            selected=type(property_type).__name__,
            base=type(self).__name__,
        )

    return super(selfie, self).__new__(property_type)


def _merge_camel_case_names(base_name, new_name):
    import re
    name_parts = re.sub(
        r'([a-z\d])([A-Z])', lambda m: "%s,%s" % m.groups(), base_name,
    ).split(",")

    other_parts = list(
        x for x in re.sub(
            r'([a-z\d])([A-Z])', lambda m: "%s,%s" % m.groups(), new_name,
        ).split(",") if x not in name_parts
    )

    return "".join(other_parts + name_parts)


def create_property_type_from_traits(trait_set):
    """Takes an iterable of trait names, and tries to compose a property type
    from that.  Raises an exception if this is not possible.  Extra traits not
    requested are not acceptable.

    If this automatic generation doesn't work for you for some reason, then
    compose your property types manually.

    The details of this composition should not be relied upon; it may change in
    future releases.  However, a given normalize version should behave
    consistently for multiple runs, given the same starting sets of properties,
    the composition order will be the same every time.
    """
    wanted_traits = set(trait_set)
    stock_types = dict(
        (k, v) for k, v in list(PROPERTY_TYPES.items()) if
        set(k).issubset(wanted_traits)
    )

    traits_available = set()
    for key in list(stock_types.keys()):
        traits_available.update(key)

    missing_traits = wanted_traits - traits_available
    if missing_traits:
        raise exc.PropertyTypeMixinNotPossible(
            traitlist=repr(trait_set),
            missing=repr(tuple(sorted(missing_traits))),
        )

    made_types = []
    # mix together property types, until we have made the right type.
    while trait_set not in PROPERTY_TYPES:

        # be somewhat deterministic: always start with types which provide the
        # 'first' trait on the list
        start_with = set(
            k for k in list(stock_types.keys()) if k and k[0] == trait_set[0]
        )

        # prefer extending already composed trait sets, by only adding to the
        # longest ones
        longest = max(len(x) for x in start_with)
        made_type = False

        for base in sorted(start_with):
            if len(base) != longest:
                continue

            # pick a type to join on which reduces the short-fall as much as
            # possible.
            shortfall = len(wanted_traits) - len(base)
            mix_in = None
            for other in sorted(stock_types.keys()):
                # skip mixes that will fail; this means that the type on the
                # list is a trait subset of 'base'
                mixed_traits = tuple(sorted(set(base) | set(other)))
                if mixed_traits in PROPERTY_TYPES:
                    continue

                this_shortfall = len(wanted_traits - (set(base) | set(other)))
                if this_shortfall < shortfall:
                    mix_in = other
                    mixed_in_product = mixed_traits
                    shortfall = this_shortfall
                    if shortfall == 0:
                        break

            if mix_in:
                base_type = PROPERTY_TYPES[base]
                other_type = PROPERTY_TYPES[other]
                new_name = _merge_camel_case_names(
                    base_type.__name__, other_type.__name__,
                )
                new_type = type(new_name, (base_type, other_type), {})
                stock_types[mixed_in_product] = new_type
                made_types.append(new_type)
                made_type = True

        if not made_type:
            raise exc.PropertyTypeMixinFailure(
                traitlist=repr(trait_set),
                newtypelist=", ".join(
                    "%r (%s)" % (x.traits, x.__name__) for x in made_types
                )
            )


class MetaProperty(type):
    """MetaClass for the various Property types, which allows for
    composing the various Property mix-ins, depending on options
    selected.
    """
    def __new__(mcs, name, bases, attrs):
        """This __new__ method is called when new property trait combinations
        are created."""
        selfie = [None, attrs.get('default_kwargs', {})]

        def _has(self, *args, **kwargs):
            mixed_kwargs = dict(selfie[1])
            mixed_kwargs.update(kwargs)
            return has(selfie[0], self, args, mixed_kwargs)

        attrs['__new__'] = _has
        duckwargs = set()
        if '__init__' in attrs:
            new_kwargs = inspect.getargspec(attrs['__init__']).args
            if new_kwargs:
                duckwargs.update(new_kwargs)
        traits = set()
        trait = attrs.get('__trait__', None)
        if trait:
            traits.add(trait)
        all_duckwargs = set(duckwargs)
        for base in bases:
            if hasattr(base, "traits"):
                traits.update(base.traits)
            if hasattr(base, "all_duckwargs"):
                all_duckwargs.update(base.all_duckwargs)
        traits = tuple(sorted(traits))
        if traits in PROPERTY_TYPES:
            raise exc.PropertyTypeClash(
                newtype=name,
                oldtype=PROPERTY_TYPES[traits].__name__,
                traitlist=repr(traits),
            )
        attrs['traits'] = traits
        attrs['duckwargs'] = duckwargs
        attrs['all_duckwargs'] = all_duckwargs
        self = super(MetaProperty, mcs).__new__(mcs, name, bases, attrs)
        PROPERTY_TYPES[self.traits] = self
        selfie[0] = self
        if trait:
            for kwarg in duckwargs:
                DUCKWARGS[kwarg].add((traits, self))
        return self
