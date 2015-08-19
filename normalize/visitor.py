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

import collections
import types

from normalize.coll import Collection
import normalize.exc as exc
from normalize.record import Record
from normalize.selector import FieldSelector
from normalize.selector import MultiFieldSelector


class Visitor(object):
    """The Visitor object represents a single recursive visit in progress.  You
    hopefully shouldn't have to sub-class this class for most use cases; just
    VisitorPattern.
    """
    def __init__(self, unpack_func, apply_func, collect_func, reduce_func,
                 apply_empty_slots=False, extraneous=False,
                 ignore_empty_string=False, ignore_none=True,
                 visit_filter=None, filter=None):
        """Create a new Visitor object.  Generally called by a front-end class
        method of :py:class:`VisitorPattern`

        There are four positional arguments, which specify the particular
        functions to be used during the visit.  The important options from a
        user of a visitor are the keyword arguments:

            ``apply_empty_slots=``\ *bool*
                If set, then your ``apply`` method (or ``reverse``, etc) will
                be called even if there is no corresponding value in the input.
                Your method will receive the Exception as if it were the value.

            ``extraneous=``\ *bool*
                Also call the apply method on properties marked *extraneous*.
                False by default.

            ``ignore_empty_string=``\ *bool*
                If the 'apply' function returns the empty string, treat it as
                if the slot or object did not exist.  ``False`` by default.

            ``ignore_none=``\ *bool*
                If the 'apply' function returns ``None``, treat it as if the
                slot or object did not exist.  ``True`` by default.

            ``visit_filter=``\ *MultiFieldSelector*
                This supplies an instance of
                :py:class:`normalize.selector.MultiFieldSelector`, and
                restricts the operation to the matched object fields.  Can also
                be specified as just ``filter=``
        """
        self.unpack = unpack_func
        self.apply = apply_func
        self.collect = collect_func
        self.reduce = reduce_func

        self.apply_empty_slots = apply_empty_slots
        self.extraneous = extraneous
        self.ignore_empty_string = ignore_empty_string
        self.ignore_none = ignore_none

        if visit_filter is None:
            visit_filter = filter
        if isinstance(visit_filter, (MultiFieldSelector, types.NoneType)):
            self.visit_filter = visit_filter
        else:
            self.visit_filter = MultiFieldSelector(*visit_filter)

        self.seen = set()  # TODO
        self.cue = list()

    def is_filtered(self, prop):
        return (not self.extraneous and prop.extraneous) or (
            self.visit_filter and not self.visit_filter[self.cue + [prop.name]]
        )

    @property
    def field_selector(self):
        return FieldSelector(self.cue)

    def push(self, what):
        self.cue.append(what)

    def pop(self, what=None):
        if what is not None:
            assert(self.cue[-1] == what)
        return self.cue.pop()

    def copy(self):
        """Be sure to implement this method when sub-classing, otherwise you
        will lose any specialization context."""
        doppel = type(self)(
            self.unpack, self.apply, self.collect, self.reduce,
            apply_empty_slots=self.apply_empty_slots,
            extraneous=self.extraneous,
            ignore_empty_string=self.ignore_empty_string,
            ignore_none=self.ignore_none,
            visit_filter=self.visit_filter,
        )
        for x in self.cue:
            doppel.push(x)
        doppel.seen = self.seen
        return doppel


class VisitorPattern(object):
    """Base Class for writing Record visitor pattern classes.  These classes
    are not instantiated, and consist purely of class methods.

    There are three visitors supplied by default, which correspond to typical
    use for IO (:py:meth:`normalize.visitor.VisitorPattern.visit` for output,
    and :py:meth:`normalize.visitor.VisitorPattern.cast` for input), and for
    providing a centralized type catalogue
    (:py:meth:`normalize.visitor.VisitorPattern.reflect`).

    ============= =========== ============= ===================================
    ``visit``     ``cast``    ``reflect``   Description
    ============= =========== ============= ===================================
    ``unpack``    ``grok``    ``scantypes`` Defines how to get a property value
                                            from the thing being walked, and a
                                            generator for the collection.
    ``apply``     ``reverse`` ``propinfo``  Conversion for individual values
    ``aggregate`` ``collect`` ``itemtypes`` Combine collection results
    ``reduce``    ``produce`` ``typeinfo``  Combine apply results
    ============= =========== ============= ===================================

    To customize what is emitted, sub-class ``VisitorPattern`` and override the
    class methods of the conversion you are interested in.  For many simple IO
    use cases, you might need only to override are ``apply`` and ``reverse``,
    if that.

    The versions for ``visit`` are documented the most thoroughly, as these are
    the easiest to understand and the ones most users will be customizing.  The
    documentation for the other methods describes the differences between them
    and their ``visit`` counterpart.
    """
    Visitor = Visitor

    @classmethod
    def visit(cls, value, value_type=None, **kwargs):
        """A value visitor, which visits instances (typically), applies
        :py:meth:`normalize.visitor.VisitorPattern.apply` to every attribute
        slot, and returns the reduced result.

        Like :py:func:`normalize.diff.diff`, this function accepts a series of
        keyword arguments, which are passed through to
        :py:class:`normalize.visitor.Visitor`.

        This function also takes positional arguments:

            ``value=``\ *object*
                The value to visit.  Normally (but not always) a
                :py:class:`normalize.record.Record` instance.

            ``value_type=``\ *RecordType*
                This is the ``Record`` subclass to interpret ``value`` as.  The
                default is ``type(value)``.  If you specify this, then the type
                information on ``value`` is essentially ignored (with the
                caveat mentioned below on :py:meth:`Visitor.map_prop`), and may
                be a ``dict``, ``list``, etc.

            ``**kwargs``
                Visitor options accepted by
                :py:meth:`normalize.visitor.Visitor.__init__`.
        """
        visitor = cls.Visitor(
            cls.unpack, cls.apply, cls.aggregate, cls.reduce,
            **kwargs)

        if not value_type:
            value_type = type(value)
            if not issubclass(value_type, Record):
                raise TypeError(
                    "Cannot visit %s instance" % value_type.__name__
                )

        return cls.map(visitor, value, value_type)

    @classmethod
    def unpack(cls, value, value_type, visitor):
        """Unpack a value during a 'visit'

        args:

            ``value=``\ *object*
                The instance being visited

            ``value_type=``\ *RecordType*
                The expected type of the instance

            ``visitor=``\ *Visitor*
                The context/options

        returns a tuple with two items:

            ``get_prop=``\ *function*
                This function should take a
                :py:class:`normalize.property.Property` instance, and return
                the slot from the value, or raise ``AttributeError`` or
                ``KeyError`` if the slot is empty.  Returning nothing means
                that the item has no properties to unpack; ie, it's an opaque
                type.

            ``get_item=``\ *generator*
                This generator should return the tuple protocol used by
                :py:class:`normalize.coll.Collection`: (K, V) where K can be an
                ascending integer (for sequences), V (for sets), or something
                hashable like a string (for dictionaries/maps)
        """
        if issubclass(value_type, Collection):
            try:
                generator = value.itertuples()
            except AttributeError:
                if isinstance(value, value_type.colltype):
                    generator = value_type.coll_to_tuples(value)
                else:
                    raise exc.VisitorUnpackError(
                        passed=value,
                        colltype=value_type.colltype.__name__,
                        context=visitor,
                    )
        else:
            generator = None

        if issubclass(value_type, Record):
            def propget(prop):
                return prop.__get__(value)
        else:
            propget = None

        return propget, generator

    @classmethod
    def apply(cls, value, prop, visitor):
        """'apply' is a general place to put a function which is called on
        every extant record slot.  This is usually the most important function
        to implement when sub-classing.

        The default implementation passes through the slot value as-is, but
        expected exceptions are converted to ``None``.

        args:

            ``value=``\ *value*\ \|\ *AttributeError*\ \|\ *KeyError*
                This is the value currently in the slot, or the Record itself
                with the ``apply_records`` visitor option.  *AttributeError*
                will only be received if you passed ``apply_empty_slots``, and
                *KeyError* will be passed if ``parent_obj`` is a ``dict`` (see
                :py:meth:`Visitor.map_prop` for details about when this might
                happen)

            ``prop=``\ *Property*\ \|\ ``None``
                This is the :py:class:`normalize.Property` instance which
                represents the field being traversed.

                This can be ``None`` when being applied over Collection
                instances, where the type of the contents is not a Record.

            ``visitor=``\ *Visitor*
                This object can be used to inspect parameters of the current
                run, such as options which control which kinds of values are
                visited, which fields are being visited and where the function
                is in relation to the starting point.
        """
        return (
            None if isinstance(value, (AttributeError, KeyError)) else
            value
        )

    @classmethod
    def aggregate(self, mapped_coll_generator, coll_type, visitor):
        """Hook called for each normalize.coll.Collection, after mapping over
        each of the items in the collection.

        The default implementation calls
        :py:meth:`normalize.coll.Collection.tuples_to_coll` with
        ``coerce=False``, which just re-assembles the collection into a native
        python collection type of the same type of the input collection.

        args:

            ``result_coll_generator=`` *generator func*
                Generator which returns (key, value) pairs (like
                :py:meth:`normalize.coll.Collection.itertuples`)

            ``coll_type=``\ *CollectionType*
                This is the :py:class:`normalize.coll.Collection`-derived
                *class* which is currently being reduced.

            ``visitor=``\ *Visitor*
                Context/options object
        """
        return coll_type.tuples_to_coll(mapped_coll_generator, coerce=False)

    @classmethod
    def reduce(self, mapped_props, aggregated, value_type, visitor):
        """This reduction is called to combine the mapped slot and collection
        item values into a single value for return.

        The default implementation tries to behave naturally; you'll almost
        always get a dict back when mapping over a record, and list or some
        other collection when mapping over collections.

        If the collection has additional properties which are not ignored (eg,
        not extraneous, not filtered), then the result will be a dictionary
        with the results of mapping the properties, and a 'values' key will be
        added with the result of mapping the items in the collection.

        args:

            ``mapped_props=``\ *generator*
                Iterating over this generator will yield K, V pairs, where K is
                **the Property object** and V is the mapped value.

            ``aggregated=``\ *object*
                This contains whatever ``aggregate`` returned, normally a list.

            ``value_type=``\ *RecordType*
                This is the type which is currently being reduced.
                A :py:class:`normalize.record.Record` subclass

            ``visitor=``\ *Visitor*
                Contenxt/options object.
        """
        reduced = None
        if mapped_props:
            reduced = dict((k.name, v) for k, v in mapped_props)

        if issubclass(value_type, Collection) and aggregated is not None:
            if all(visitor.is_filtered(prop) for prop in
                   value_type.properties.values()):
                reduced = aggregated
            else:
                if reduced.get("values", False):
                    raise exc.VisitorTooSimple(
                        fs=visitor.field_selector,
                        value_type_name=value_type.__name__,
                        visitor=type(self).__name__,
                    )
                else:
                    reduced['values'] = aggregated

        return reduced

    # CAST versions
    @classmethod
    def cast(cls, value_type, value, visitor=None, **kwargs):
        """Cast is for visitors where you are visiting some random data
        structure (perhaps returned by a previous ``VisitorPattern.visit()``
        operation), and you want to convert back to the value type.

        This function also takes positional arguments:

            ``value_type=``\ *RecordType*
                The type to cast to.

            ``value=``\ *object*

            ``visitor=``\ *Visitor.Options*
                Specifies the visitor options, which customizes the descent
                and reduction.
        """
        if visitor is None:
            visitor = cls.Visitor(
                cls.grok, cls.reverse, cls.collect, cls.produce,
                **kwargs)

        return cls.map(visitor, value, value_type)

    # hooks for types which define what is considered acceptable input for
    # given contexts during 'cast'
    #
    # note: Collection.coll_to_tuples will generally allow you to pass
    # collections as a list or a dict with the *values* being the members of
    # the set, so this code allows this.
    grok_mapping_types = collections.Mapping
    grok_coll_types = (collections.Sequence, collections.Mapping)

    @classmethod
    def grok(cls, value, value_type, visitor):
        """Like :py:meth:`normalize.visitor.VisitorPattern.unpack` but called
        for ``cast`` operations.  Expects to work with dictionaries and lists
        instead of Record objects.

        Reverses the transform performed in
        :py:meth:`normalize.visitor.VisitorPattern.reduce` for collections with
        properties.

        If you pass tuples to ``isa`` of your Properties, then you might need
        to override this function and throw ``TypeError`` if the passed
        ``value_type`` is not appropriate for ``value``.
        """
        is_coll = issubclass(value_type, Collection)
        is_record = issubclass(value_type, Record) and any(
            not visitor.is_filtered(prop) for prop in
            value_type.properties.values()
        )

        if is_record and not isinstance(value, cls.grok_mapping_types):
            raise exc.VisitorGrokRecordError(
                val=repr(value),
                record_type=value_type,
                record_type_name=value_type.__name__,
                field_selector=visitor.field_selector,
            )

        values = value
        if is_coll and is_record:
            try:
                if "values" in value:
                    values = value['values']
            except TypeError:
                pass

        generator = None
        if is_coll:
            if not isinstance(values, cls.grok_coll_types):
                raise exc.VisitorGrokCollectionError(
                    val=repr(values),
                    record_type=value_type,
                    record_type_name=value_type.__name__,
                    field_selector=visitor.field_selector,
                )
            generator = value_type.coll_to_tuples(values)

        propget = None
        if is_record:
            def propget(prop):
                return value[prop.name]

        return propget, generator

    @classmethod
    def reverse(cls, value, prop, visitor):
        """Like :py:meth:`normalize.visitor.VisitorPattern.apply` but called
        for ``cast`` operations.  The default implementation passes through but
        squashes exceptions, just like apply.
        """
        return (
            None if isinstance(value, (AttributeError, KeyError)) else
            value
        )

    @classmethod
    def collect(cls, mapped_coll_generator, coll_type, visitor):
        """Like :py:meth:`normalize.visitor.VisitorPattern.aggregate`, but
        coerces the mapped values to the collection item type on the way
        through.
        """
        return coll_type.tuples_to_coll(mapped_coll_generator)

    @classmethod
    def produce(cls, mapped_props, aggregated, value_type, visitor):
        """Like :py:meth:`normalize.visitor.VisitorPattern.reduce`, but
        constructs instances rather than returning plain dicts.
        """
        kwargs = {} if not mapped_props else dict(
            (k.name, v) for k, v in mapped_props
        )
        if issubclass(value_type, Collection):
            kwargs['values'] = aggregated
        return value_type(**kwargs)

    # versions which walk type objects
    @classmethod
    def reflect(cls, X, **kwargs):
        """Reflect is for visitors where you are exposing some information
        about the types reachable from a starting type to an external system.
        For example, a front-end, a REST URL router and documentation
        framework, an avro schema definition, etc.

        X can be a type or an instance.

        This API should be considered **experimental**
        """
        if isinstance(X, type):
            value = None
            value_type = X
        else:
            value = X
            value_type = type(X)
        if not issubclass(value_type, Record):
            raise TypeError("Cannot reflect on %s" % value_type.__name__)

        visitor = cls.Visitor(
            cls.scantypes, cls.propinfo, cls.itemtypes,
            cls.typeinfo,
            **kwargs)

        return cls.map(visitor, value, value_type)

    @classmethod
    def scantypes(cls, value, value_type, visitor):
        """Like :py:meth:`normalize.visitor.VisitorPattern.unpack`, but
        returns a getter which just returns the property, and a collection
        getter which returns a set with a single item in it.
        """

        item_type_generator = None
        if issubclass(value_type, Collection):

            def get_item_types():
                if isinstance(value_type.itemtype, tuple):
                    # not actually supported by Collection yet, but whatever
                    for vt in value_type.itemtype:
                        yield (vt, vt)
                else:
                    yield value_type.itemtype, value_type.itemtype

            item_type_generator = get_item_types()

        propget = None
        if issubclass(value_type, Record):
            def propget(prop):
                return prop

        return propget, item_type_generator

    @classmethod
    def propinfo(cls, value, prop, visitor):
        """Like :py:meth:`normalize.visitor.VisitorPattern.apply`, but takes a
        property and returns a dict with some basic info.  The default
        implementation returns just the name of the property and the type in
        here.
        """
        if not prop:
            return {"name": value.__name__}

        rv = {"name": prop.name}
        if prop.valuetype:
            if isinstance(prop.valuetype, tuple):
                rv['type'] = [typ.__name__ for typ in prop.valuetype]
            else:
                rv['type'] = prop.valuetype.__name__
        return rv

    @classmethod
    def itemtypes(cls, mapped_types, coll_type, visitor):
        """Like :py:meth:`normalize.visitor.VisitorPattern.aggregate`, but
        returns .  This will normally only get called with a single type.
        """
        rv = list(v for k, v in mapped_types)
        return rv[0] if len(rv) == 1 else rv

    @classmethod
    def typeinfo(cls, propinfo, type_parameters, value_type, visitor):
        """Like :py:meth:`normalize.visitor.VisitorPattern.reduce`, but returns
        the final dictionary to correspond to a type definition.  The default
        implementation returns just the type name, the list of properties, and
        the item type for collections.
        """
        propspec = dict((prop.name, info) for prop, info in propinfo)
        ts = {'name': value_type.__name__}
        if propspec:
            ts['properties'] = propspec
        if type_parameters:
            ts['itemtype'] = type_parameters
        return ts

    # sentinel iteration stopper
    class StopVisiting(object):
        """This sentinel value may be returned by a custom implementation of
        ``unpack`` (or ``grok``, or ``scantypes``) to indicate that the descent
        should be stopped immediately, instead of proceeding to descend into
        sub-properties.  It can be passed a literal value to use as the mapped
        value as a single constructor argument, or the class itself returned to
        indicate no mapped value."""
        return_value = None

        def __init__(self, return_value):
            self.return_value = return_value

    # methods-in-common
    @classmethod
    def map(cls, visitor, value, value_type):
        """The common visitor API used by all three visitor implementations.

        args:

            ``visitor=``\ *Visitor*
                Visitor options instance: contains the callbacks to use to
                implement the visiting, as well as traversal & filtering
                options.

            ``value=``\ *Object*
                Object being visited

            ``value_type=``\ *RecordType*
                The type object controlling the visiting.
        """
        unpacked = visitor.unpack(value, value_type, visitor)

        if unpacked == cls.StopVisiting or isinstance(
            unpacked, cls.StopVisiting
        ):
            return unpacked.return_value

        if isinstance(unpacked, tuple):
            props, coll = unpacked
        else:
            props, coll = unpacked, None

        # recurse into values for collections
        if coll:
            coll_map_generator = cls.map_collection(
                visitor, coll, value_type,
            )
            mapped_coll = visitor.collect(
                coll_map_generator, value_type, visitor,
            )
        else:
            mapped_coll = None

        # recurse into regular properties
        mapped_props = None
        if props:
            mapped_props = cls.map_record(visitor, props, value_type)
        elif mapped_coll is None:
            return visitor.apply(value, None, visitor)

        return visitor.reduce(
            mapped_props, mapped_coll, value_type, visitor,
        )

    @classmethod
    def map_record(cls, visitor, get_value, record_type):
        rv = visitor.copy()  # expensive?
        for name, prop in record_type.properties.iteritems():
            if rv.is_filtered(prop):
                continue

            rv.push(name)
            try:
                value = get_value(prop)
            except AttributeError as ae:
                value = ae
            except KeyError as ke:
                value = ke
            except Exception as e:
                rv.pop(name)
                raise exc.VisitorPropError(
                    exception=e,
                    prop=prop,
                    prop_name=name,
                    record_type_name=record_type.__name__,
                    fs=rv.field_selector,
                )

            if visitor.apply_empty_slots or not isinstance(
                value, (KeyError, AttributeError),
            ):
                mapped = cls.map_prop(rv, value, prop)
                if mapped is None and rv.ignore_none:
                    pass
                elif mapped == "" and rv.ignore_empty_string:
                    pass
                else:
                    yield prop, mapped
            rv.pop(name)

    @classmethod
    def map_collection(cls, visitor, coll_generator, coll_type):
        rv = visitor.copy()
        for key, value in coll_generator:
            rv.push(key)
            mapped = cls.map(rv, value, coll_type.itemtype)
            rv.pop(key)
            if mapped is None and visitor.ignore_none:
                pass
            elif mapped == "" and visitor.ignore_empty_string:
                pass
            else:
                yield key, mapped

    @classmethod
    def map_prop(cls, visitor, value, prop):
        mapped = None

        # XXX - this fallback here is type-unsafe, and exists only for
        # those who don't declare their isa= for complex object types.
        value_type = prop.valuetype or type(value)

        if isinstance(value_type, tuple):
            mapped = cls.map_type_union(
                visitor, value, value_type, prop,
            )
        elif issubclass(value_type, Record):
            mapped = cls.map(visitor, value, value_type)
        else:
            mapped = visitor.apply(value, prop, visitor)

        return mapped

    @classmethod
    def map_type_union(cls, visitor, value, type_tuple, prop):
        # This corner-case method applies when visiting a value and
        # ncountering a type union in the ``Property.valuetype`` field.
        #
        # this code has the same problem that record_id does; that is, it
        # doesn't know which of the type union the value is.
        #
        # the solution this function uses is to try all of them, until one of
        # them returns something logically true.  Handlers (ie, unpack/grok)
        # can also protest by raising TypeError, and the next one will be
        # tried.
        record_types = []
        matching_record_types = []

        for value_type in type_tuple:
            if issubclass(value_type, Record):
                record_types.append(value_type)
                # XXX - this test here should probably be a per-visitor
                # hook, as it only really applies to 'visit', not 'grok'
                if isinstance(value, value_type):
                    matching_record_types.append(value_type)

        mapped = None
        if matching_record_types:
            for value_type in matching_record_types:
                try:
                    mapped = cls.map(visitor, value, value_type)
                except TypeError:
                    pass
                else:
                    if mapped:
                        break
        else:
            for value_type in record_types:
                try:
                    mapped = cls.map(visitor, value, value_type)
                except TypeError:
                    pass
                else:
                    # this could also be the wrong thing when mapping
                    # over types.
                    if mapped:
                        break

            if not mapped:
                mapped = visitor.apply(value, prop, visitor)

        return mapped
