from __future__ import absolute_import

import json
import pickle
import unittest2

from normalize.record import Record
from normalize.record.json import from_json
from normalize.record.json import JsonRecord
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
    def setUp(self):
        self.primitive = {
            "id": "123",
            "name": "Fridge",
            "best_cheese": dict(variety="Gouda", smelliness="12"),
            "cheeses": [
                dict(variety="Manchego", smelliness="38"),
                dict(variety="Stilton", smelliness="82"),
                dict(variety="Polkobin", smelliness="31"),
            ],
        }

    def assertDataOK(self, ccr):
        self.assertIsInstance(ccr, CheeseCupboardRecord)
        self.assertEqual(ccr.id, 123)
        self.assertEqual(len(ccr.cheeses), 3)
        self.assertEqual(ccr.best_cheese.variety, "Gouda")
        self.assertEqual(ccr.cheeses[1].smelliness, 82)

    def test_native_marshall(self):
        """Test coerce from python dicts & pickling"""
        ccr = CheeseCupboardRecord(self.primitive)
        for protocol in range(0, pickle.HIGHEST_PROTOCOL + 1):
            pickled = pickle.dumps(ccr, protocol)
            ccr_copy = pickle.loads(pickled)
            self.assertDataOK(ccr_copy)

    def test_json_marshall(self):
        """Test coerce from JSON & marshall out"""
        json_struct = json.dumps(self.primitive)
        ccr = from_json(CheeseCupboardRecord, json.loads(json_struct))
        self.assertDataOK(ccr)

        class RealWorldCCR(JsonRecord, CheeseCupboardRecord):
            pass

        ccr = RealWorldCCR.from_json(json_struct)
        self.assertDataOK(ccr)
