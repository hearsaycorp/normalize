from __future__ import absolute_import

import pickle
import unittest2

from normalize.record import Record
from normalize.property import ListProperty
from normalize.property import ROProperty
from normalize.property import SafeProperty


class CheeseRecord(Record):
    variety = SafeProperty(isa=str)
    smelliness = SafeProperty(isa=float, check=lambda x: 0 < x < 100)


class CheeseCupboardRecord(Record):
    id = ROProperty(required=True, isa=int)
    name = SafeProperty(isa=str)
    best_cheese = SafeProperty(isa=CheeseRecord)
    cheeses = ListProperty(of=CheeseRecord)


class TestRecordMarshaling(unittest2.TestCase):
    def test_native_marshall(self):
        # coerce from 'native' types (ie, dicts)
        ccr = CheeseCupboardRecord(
            {
                "id": "123",
                "name": "Fridge",
                "best_cheese": dict(variety="Gouda", smelliness="12"),
                "cheeses": [
                    dict(variety="Manchego", smelliness="38"),
                    dict(variety="Stilton", smelliness="82"),
                    dict(variety="Polkobin", smelliness="31"),
                ],
            }
        )

        for protocol in range(0, pickle.HIGHEST_PROTOCOL + 1):
            pickled = pickle.dumps(ccr, protocol)
            ccr_copy = pickle.loads(pickled)
            self.assertEqual(ccr_copy.id, 123)
            self.assertEqual(len(ccr_copy.cheeses), 3)
            self.assertEqual(ccr_copy.best_cheese.variety, "Gouda")
            self.assertEqual(ccr_copy.cheeses[1].smelliness, 82)
