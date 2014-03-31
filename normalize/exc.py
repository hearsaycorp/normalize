"""
Structured exception module.

This makes structured exceptions as easy to use as string exceptions.  Simply
define an exception name and a format string; the base class takes care of the
rest.  Should you need any more sophisticated handling of an exception, it is
easy to change without affecting downstream users.
"""


class StringFormatException(Exception):
    message = "(uncustomized exception!)"

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        try:
            self.formatted = self.message.format(*args, **kwargs)
        except IndexError:
            raise PositionalExceptionFormatError(
                typename=type(self).__name__,
                received=repr(args),
            )
        except KeyError, e:
            raise KeywordExceptionFormatError(
                typename=type(self).__name__,
                missing=e[0],
                passed=repr(kwargs.keys()),
            )

    def __str__(self):
        return self.formatted

    def __getattr__(self, attrname):
        try:
            return self.kwargs[attrname]
        except KeyError:
            raise AttributeError(
                "no such attribute %s of %s" % (
                    attrname, type(self).__name__,
                )
            )

    def __getitem__(self, key):
        return self.args[key]

    def __repr__(self):
        return "%s%s(%s)" % (
            "exc." if self.__module__.endswith(".exc") else "",
            type(self).__name__, ", ".join(
                tuple("%r" % x for x in self.args) +
                tuple("%s=%r" % (k, v) for k, v in self.kwargs.iteritems())
            )
        )


# exception base classes
class CoercionError(StringFormatException, ValueError):
    pass


class FieldSelectorException(StringFormatException):
    pass


class PropertyDefinitionError(StringFormatException):
    pass


class PropertyTypeDefinitionError(StringFormatException):
    pass


class StringFormatExceptionError(StringFormatException):
    pass


class SubclassError(StringFormatException):
    pass


class UsageException(StringFormatException):
    pass


# concrete exception types
class CoerceWithoutType(PropertyDefinitionError):
    message = (
        "In order to coerce types, the intended type must be known; "
        "pass isa=TYPE or isa=(TYPE, TYPE, ...) to Property()"
    )


class CollectionCoerceError(CoercionError):
    message = "Cannot interpret {giventype} as a {fortype} constructor"


class CollectionDefinitionError(SubclassError):
    message = "{property} must be defined in a {coll} subclass"


class CollRequiredError(PropertyDefinitionError):
    message = (
        "coll is required; specify coll type or use a sub-class "
        "like ListProperty"
    )


class CollTypeMismatch(PropertyDefinitionError):
    message = (
        "collection property 'isa' must match collection type"
    )


class DefaultSignatureError(PropertyDefinitionError):
    message = (
        "default functions may take 0 or 1 arguments; {module}.{func} "
        "wants {nargs}"
    )


class DiffOptionsException(UsageException):
    message = "pass options= or DiffOptions constructor arguments; not both"


class FieldSelectorAttributeError(FieldSelectorException, AttributeError):
    message = "Could not find property specified by name: {name}"


class FieldSelectorKeyError(FieldSelectorException, KeyError):
    message = "Could not find Record specified by index: {key}"


class KeyHashError(StringFormatException):
    message = (
        "PK for {prop} returned an unhashable value; try setting "
        "a primary key in type {typename}"
    )


class KeywordExceptionFormatError(StringFormatExceptionError):
    message = (
        "{typename} raised without passing {missing}; saw only: {passed}"
    )


class LazyIsFalse(PropertyDefinitionError):
    message = "To make an eager property, do not pass lazy= to Property()"


class ListOfWhat(PropertyDefinitionError):
    message = (
        "List Properties must have a defined item type; pass of= "
        "or list_of= to the declaration"
    )


class ListPropertyMustDeriveListCollection(PropertyDefinitionError):
    message = (
        "List Property collections must derive ListCollection, and "
        "{got} doesn't"
    )


class PositionalExceptionFormatError(StringFormatExceptionError):
    message = (
        "{typename} expects a positional format string; passed: "
        "{received}"
    )


class PropertyNotUnique(PropertyTypeDefinitionError):
    message = (
        "Duplicate ListProperties of the same class name defined in the "
        "same module.  Both end up being called {key} in my global map.  "
        "I'm sorry Dave, I'm afraid I can't let you do that."
    )


class ReadOnlyAttributeError(StringFormatException, AttributeError):
    message = "{attrname} is read-only"
