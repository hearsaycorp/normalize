PROPERTY_TYPES = dict()


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
    extra_traits = kwargs.pop('traits', None)
    all_traits = (
        self.traits if not extra_traits else
        tuple(sorted(self.traits + tuple(extra_traits)))
    )
    if all_traits not in PROPERTY_TYPES:
        raise Exception(
            "Failed to find a Property type which provides traits %r" % (
                all_traits
            )
        )
    property_type = PROPERTY_TYPES[all_traits]
    if not isinstance(property_type, type(self)):
        raise Exception(
            "Can't create %s property using %s constructor" % (
                type(property_type).__name__, type(self).__name__,
            )
        )

    return super(selfie, self).__new__(property_type, *args, **kwargs)


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
        traits = list()
        trait = attrs.get('__trait__', None)
        if trait:
            traits.append(trait)
        for base in bases:
            if hasattr(base, "traits"):
                traits.extend(base.traits)
        traits = tuple(sorted(traits))
        if traits in PROPERTY_TYPES:
            raise Exception(
                "Both %s and %s purport to provide the mix of traits: %r" % (
                    PROPERTY_TYPES[traits].__name__, name, traits,
                )
            )
        attrs['traits'] = traits
        self = super(MetaProperty, mcs).__new__(mcs, name, bases, attrs)
        PROPERTY_TYPES[self.traits] = self
        selfie.append(self)
        return self
