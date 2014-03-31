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
class FieldSelectorException(StringFormatException):
    pass


class StringFormatExceptionError(StringFormatException):
    pass


class SubclassError(StringFormatException):
    pass


class UsageException(StringFormatException):
    pass


# concrete exception types
class DiffOptionsException(UsageException):
    message = "pass options= or DiffOptions constructor arguments; not both"


class FieldSelectorAttributeError(FieldSelectorException, AttributeError):
    message = "Could not find property specified by name: {name}"


class FieldSelectorKeyError(FieldSelectorException, KeyError):
    message = "Could not find Record specified by index: {key}"


class KeywordExceptionFormatError(StringFormatExceptionError):
    message = (
        "{typename} raised without passing {missing}; saw only: {passed}"
    )


class PositionalExceptionFormatError(StringFormatExceptionError):
    message = (
        "{typename} expects a positional format string; passed: "
        "{received}"
    )
