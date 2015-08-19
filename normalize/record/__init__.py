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

from __future__ import absolute_import

import normalize.exc as exc
from normalize.identity import record_id
from normalize.record.meta import RecordMeta


class _Unset(object):
    pass


class Record(object):
    """Base class for normalize instances and collections.
    """
    __metaclass__ = RecordMeta

    def __init__(self, init_dict=None, **kwargs):
        """Instantiates a new ``Record`` type.

        You may specify a ``dict`` to initialize from, *or* use keyword
        argument form.  The default interpretation of the first positional
        argument is to treat it as if its contents were passed in as keyword
        arguments.

        Subclass API: subclasses are permitted to interpret positional
        arguments in non-standard ways, but in general it is expected that if
        keyword arguments are passed, then they are already of the right type
        (or, of a type that the ``coerce`` functions associated with the
        properties can accept).  The only exception to this is if ``init_dict``
        is an ``OhPickle`` instance, you should probably just return (see
        :py:class:`OhPickle`)
        """
        if isinstance(init_dict, OhPickle):
            return
        if init_dict and kwargs:
            raise exc.AmbiguousConstruction()
        if not init_dict:
            init_dict = kwargs
        for prop, val in init_dict.iteritems():
            meta_prop = type(self).properties.get(prop, None)
            if meta_prop is None:
                raise exc.PropertyNotKnown(
                    propname=prop,
                    recordtype=type(self),
                    typename=type(self).__name__,
                )
            meta_prop.init_prop(self, val)
        missing = type(self).eager_properties - set(init_dict.keys())

        for propname in missing:
            meta_prop = type(self).properties[propname]
            meta_prop.init_prop(self)

    def __getnewargs__(self):
        """Stub method which arranges for an ``OhPickle`` instance to be passed
        to the constructor above when pickling out.
        """
        return (OhPickle(),)

    def __getstate__(self):
        """Implement saving, for the pickle out API.  Returns the instance
        dict"""
        return self.__dict__

    def __setstate__(self, instance_dict):
        """Implement loading, for the pickle in API.  Sets the instance dict
        directly."""
        self.__dict__.update(instance_dict)

    def __str__(self):
        """Marshalling to string form.  This is what you see if you cast the
        object to a string or use the ``%s`` format code, and is supposed to be
        an "informal" representation when you don't want a full object dump
        like ``repr()`` would provide.

        If you defined a ``primary_key`` for the object, then the values of the
        attributes you specified will be included in the string representation,
        eg ``<Task 17>``.  Otherwise, the *implicit* primary key (eg, a tuple
        of all of the defined attributes with their values) is included, up to
        the first 30 characters or so.
        """
        pk = self.__pk__
        key = repr(pk[0] if len(pk) == 1 else pk)
        return "<%s %s>" % (
            type(self).__name__, key[:30] + "..." if len(key) > 32 else key
        )

    def __repr__(self):
        """Marshalling to Python source.  This is what you will see when
        printing objects using the ``%r`` format code.  This function is
        recursive and should generally satisfy the requirement that it is valid
        Python source, assuming all class names are in scope and all values
        implement ``__repr__`` as suggested in the python documentation.
        """
        typename = type(self).__name__
        values = list()
        for propname in sorted(type(self).properties):
            if propname not in self.__dict__:
                continue
            else:
                values.append("%s=%r" % (propname, self.__dict__[propname]))
        return "%s(%s)" % (typename, ", ".join(values))

    def __eq__(self, other):
        """Compare two Record classes; recursively compares all attributes for
        equality (except those marked 'extraneous').  See also
        :py:meth:`diff` for a version where the comparison can be
        fine-tuned."""
        if type(self) != type(other):
            return False
        for propname, prop in type(self).properties.iteritems():
            if not prop.extraneous:
                if getattr(self, propname, _Unset) != getattr(
                    other, propname, _Unset
                ):
                    return False
        return True

    def __ne__(self, other):
        """implemented for compatibility"""
        return not self.__eq__(other)

    @property
    def __pk__(self):
        """This property returns the "primary key" for this object.  This is
        similar to what is used when comparing Collections via
        :py:mod:`normalize.diff`, and is used for stringification and for the
        ``id()`` built-in.
        """
        return record_id(self, type(self))

    def __hash__(self):
        """Implements ``id()`` for Record types.
        """
        return self.__pk__.__hash__()

    def diff_iter(self, other, **kwargs):
        """Generator method which returns the differences from the invocant to
        the argument.

        args:

            ``other=``\ *Record*\ \|\ *Anything*
                 The thing to compare against; the types must match, unless
                 ``duck_type=True`` is passed.

            *diff_option*\ =\ *value*
                 Unknown keyword arguments are eventually passed to a
                 :ref:`DiffOptions` constructor.
        """
        from normalize.diff import diff_iter
        return diff_iter(self, other, **kwargs)

    def diff(self, other, **kwargs):
        """Compare an object with another and return a :py:class:`DiffInfo`
        object.  Accepts the same arguments as
        :py:meth:`normalize.record.Record.diff_iter`
        """
        from normalize.diff import diff
        return diff(self, other, **kwargs)


class OhPickle(object):
    """Sentinel type for Un-Pickling.  ``pickle`` does not allow a
    ``__getinitargs__``/``__getnewargs__`` to return keyword constructor
    arguments, so this value is passed to ``__init__`` when unpickling.  It
    indicates to not perform any immediate post-construction checks and instead
    just return and let ``__getstate``__ set this object up.
    """
    def __str__(self):
        return "<OhPickle>"
