
from normalize.coll import ListCollection
from normalize.coll import make_generic
from normalize.property import Property
from normalize.property import SafeProperty


class CollectionProperty(Property):
    __trait__ = "coll"

    def __init__(self, of=None, coll=None, check_item=None, isa=None,
                 **kwargs):
        if isa is None and coll is None:
            raise Exception(
                "coll is required; specify coll type or use a sub-class "
                "like ListProperty"
            )
        if isa:
            if (coll and not issubclass(isa, coll)) or \
                    (of and not issubclass(of, isa.itemtype)):
                raise Exception(
                    "collection property 'isa' must match collection type"
                )
            self.of = isa.itemtype
            self.coll = isa
        else:
            isa = make_generic(of, coll)

        super(CollectionProperty, self).__init__(isa=isa, **kwargs)


class SafeCollectionProperty(CollectionProperty, SafeProperty):
    def __set__(self, obj, value):
        super(SafeCollectionProperty, self).__set__(obj, self._coerce(value))


class ListProperty(CollectionProperty):
    __trait__ = "list"

    def __init__(self, list_of=None, **kwargs):
        if list_of is None:
            list_of = kwargs.pop("of", None)
        if not list_of:
            raise Exception(
                "List Properties must have a defined item type; pass of= "
                "or list_of= to the declaration"
            )
        colltype = kwargs.pop('coll', ListCollection)
        if not issubclass(colltype, ListCollection):
            raise Exception(
                "List Property collections must derive ListCollection"
            )
        super(ListProperty, self).__init__(
            of=list_of, coll=colltype, **kwargs
        )


class SafeListCollectionProperty(ListProperty, SafeCollectionProperty):
    pass
