
from normalize.coll import ListCollection
from normalize.coll import make_generic
import normalize.exc as exc
from normalize.property import Property
from normalize.property import SafeProperty


class CollectionProperty(Property):
    """Base class for properties which contain collections; responsible for
    creating new collection types (via :py:func:`normalize.coll.make_generic`)
    """
    __trait__ = "coll"

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
            isa = make_generic(of, coll)

        super(CollectionProperty, self).__init__(isa=isa, **kwargs)


class SafeCollectionProperty(CollectionProperty, SafeProperty):
    def __set__(self, obj, value):
        super(SafeCollectionProperty, self).__set__(
            obj, self.type_safe_value(value),
        )


class ListProperty(CollectionProperty):
    __trait__ = "list"

    def __init__(self, list_of=None, **kwargs):
        if list_of is None:
            list_of = kwargs.pop("of", None)
        if not list_of:
            raise exc.ListOfWhat()
        colltype = kwargs.pop('coll', ListCollection)
        if not issubclass(colltype, ListCollection):
            raise exc.ListPropertyMustDeriveListCollection(
                got=colltype.__name__,
            )

        super(ListProperty, self).__init__(
            of=list_of, coll=colltype, **kwargs
        )
