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


from normalize.coll import DictCollection
from normalize.coll import ListCollection
from normalize.coll import _make_generic
import normalize.exc as exc
from normalize.property import Property
from normalize.property import SafeProperty


class CollectionProperty(Property):
    """Base class for properties which contain collections; responsible for
    creating new collection types (via :py:func:`normalize.coll._make_generic`)
    """
    __trait__ = "coll"
    __safe_unless_ro__ = True

    def __init__(self, of=None, coll=None, isa=None, **kwargs):
        """Create a new Collection property.

        Args:
            ``of=``\ *TYPE*
                Specifies what type each member of the collection must be.

            ``coll=``\ *<Abstract Collection type>*
                Specify the container type for the collection.  Should be
                a :py:mod:`normalize.coll.Collection` sub-class.

            ``isa=``\ *<Concrete Collection type>*
                Specify both ``of=`` and ``isa=`` by passing in a
                'concrete' Collection type (this means it already has
                ``itemtype`` set)
        """
        if isa is None and coll is None:
            raise exc.CollRequiredError()
        if isa:
            if (coll and not issubclass(isa, coll)) or \
                    (of and not issubclass(of, isa.itemtype)):
                raise exc.CollTypeMismatch()
            self.of = isa.itemtype
            self.coll = isa
        else:
            isa = _make_generic(of, coll)

        super(CollectionProperty, self).__init__(isa=isa, **kwargs)


class SafeCollectionProperty(CollectionProperty, SafeProperty):
    def __set__(self, obj, value):
        super(SafeCollectionProperty, self).__set__(
            obj, self.type_safe_value(value),
        )


class ListProperty(CollectionProperty):
    __trait__ = "list"
    coll_type = ListCollection

    def __init__(self, list_of=None, **kwargs):
        if list_of is None:
            list_of = kwargs.pop("of", None)
        if not list_of:
            raise exc.ListOfWhat()
        colltype = kwargs.pop('coll', self.coll_type)
        if not issubclass(colltype, ListCollection):
            raise exc.ListPropertyMustDeriveListCollection(
                got=colltype.__name__,
            )

        super(ListProperty, self).__init__(
            of=list_of, coll=colltype, **kwargs
        )


class DictProperty(CollectionProperty):
    __trait__ = "dict"
    coll_type = DictCollection

    def __init__(self, dict_of=None, **kwargs):
        if dict_of is None:
            dict_of = kwargs.pop("of", None)
        if not dict_of:
            raise exc.DictOfWhat()
        colltype = kwargs.pop('coll', self.coll_type)
        if not issubclass(colltype, DictCollection):
            raise exc.DictPropertyMustDeriveDictCollection(
                got=colltype.__name__,
            )

        super(DictProperty, self).__init__(
            of=dict_of, coll=colltype, **kwargs
        )
