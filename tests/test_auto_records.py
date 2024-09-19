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

"""test the new "auto json record" API"""

from __future__ import absolute_import

from datetime import datetime
import os.path
import unittest
import warnings

from normalize import ListProperty
from normalize import Property
from normalize import Record
from normalize import AutoJsonRecord
from normalize import NCAutoJsonRecord
import normalize.exc as exc


class TestAutoRecords(unittest.TestCase):
    """Test that the new data descriptor classes work"""

    def test_auto_json(self):

        class MyRecord(AutoJsonRecord):
            blah_blah = Property(json_name="blahBlah")

        my_record = MyRecord(
            {
                "blahBlah": {"blah": "blah"},
                "kerSploosh": "zlonk",
                "krunch": {
                    "crrAaack": "kapow",
                    "eeeYow": {"whap": "aiee"},
                },
                "ouchEth": ["bap", "bonk"],
                "whamEth": [
                    {
                        "rip": "bloop",
                    },
                ],
            }
        )

        self.assertEqual(my_record.blah_blah['blah'], "blah")
        self.assertEqual(my_record.ker_sploosh, "zlonk")
        self.assertEqual(my_record.krunch.crr_aaack, "kapow")
        self.assertEqual(my_record.krunch.eee_yow.whap, "aiee")
        self.assertEqual(my_record.ouch_eth[0], "bap")
        self.assertEqual(my_record.wham_eth[0].rip, "bloop")

    def test_nc_auto_json(self):

        class MyRecord(NCAutoJsonRecord):
            blah_blah = Property(json_name="blahBlah")

        my_record = MyRecord(
            {
                "blahBlah": {"blah": "blah"},
                "kerSploosh": "zlonk",
                "krunch": {
                    "crrAaack": "kapow",
                    "eeeYow": {"whap": "aiee"},
                },
                "ouchEth": ["bap", "bonk"],
                "whamEth": [
                    {
                        "rip": "bloop",
                    },
                ],
            }
        )

        self.assertEqual(my_record.blah_blah['blah'], "blah")
        self.assertEqual(my_record.kerSploosh, "zlonk")
        self.assertEqual(my_record.krunch.crrAaack, "kapow")
        self.assertEqual(my_record.krunch.eeeYow.whap, "aiee")
        self.assertEqual(my_record.ouchEth[0], "bap")
        self.assertEqual(my_record.whamEth[0].rip, "bloop")
