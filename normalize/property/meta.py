from collections import defaultdict
import inspect


PROPERTY_TYPES = dict()

# Duck typing kwargs... for picking the right Property sub-class to instantiate
# based on the kwargs used in the Property() constructor
DUCKWARGS = defaultdict(set)


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
    extra_traits = set(kwargs.pop('traits', tuple()))
    # detect initializer arguments only supported by a subclass and add
    # them to extra_traits
    for argname in kwargs:
        if argname not in self.all_duckwargs:
            # initializer does not support this arg.  Do any subclasses?
            for trait, proptype in DUCKWARGS[argname]:
                if isinstance(proptype, type(self)):
                    extra_traits.add(trait)

    all_traits = set(self.traits) | extra_traits

    if "unsafe" in all_traits:
        all_traits.remove("unsafe")
    else:
        if "ro" not in all_traits and "lazy" not in all_traits:
            all_traits.add("safe")

    trait_set_key = tuple(sorted(all_traits))

    if trait_set_key not in PROPERTY_TYPES:
        raise Exception(
            "Failed to find a Property type which provides traits %r" %
            list(trait_set_key)
        )
    property_type = PROPERTY_TYPES[trait_set_key]
    if not isinstance(property_type, type(self)):
        raise Exception(
            "Can't create %s property using %s constructor" % (
                type(property_type).__name__, type(self).__name__,
            )
        )

    return super(selfie, self).__new__(property_type)


class MetaProperty(type):
    """MetaClass for the various Property types, which allows for
    composing the various Property mix-ins, depending on options
    selected.
    """
    def __new__(mcs, name, bases, attrs):
        """This __new__ method is called when new property trait combinations
        are created."""
        selfie = []

        def _has(self, *args, **kwargs):
            return has(selfie[0], self, args, kwargs)

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
            raise Exception(
                "Both %s and %s purport to provide the mix of traits: %r" % (
                    PROPERTY_TYPES[traits].__name__, name, traits,
                )
            )
        attrs['traits'] = traits
        attrs['duckwargs'] = duckwargs
        attrs['all_duckwargs'] = all_duckwargs
        self = super(MetaProperty, mcs).__new__(mcs, name, bases, attrs)
        PROPERTY_TYPES[self.traits] = self
        selfie.append(self)
        if trait:
            for kwarg in duckwargs:
                DUCKWARGS[kwarg].add((trait, self))
        return self
