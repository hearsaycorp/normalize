"""
Unit tests for bytes handling in JSON record constructors.

Tests the _decode_and_parse_json function and JsonRecord/JsonRecordList/
JsonRecordDict
constructors accepting bytes input without triggering JsonRecordCoerceError.
"""

import unittest

# Import directly from modules to avoid normalize.__init__ -> diff ->
# richenum chain
from normalize.record.json import _decode_and_parse_json
from normalize.record.json import JsonRecord
from normalize.record.json import JsonRecordList
from normalize.record.json import JsonRecordDict
from normalize.record.json import from_json
from normalize.property.json import JsonProperty
from json import JSONDecodeError


class AuthCookie(JsonRecord):
    """Test record for cookie-like data"""
    u = JsonProperty()
    x = JsonProperty()
    e = JsonProperty()
    o = JsonProperty()
    m = JsonProperty()
    c = JsonProperty()


class CookieList(JsonRecordList):
    """Test list of cookies"""
    itemtype = AuthCookie


class CookieDict(JsonRecordDict):
    """Test dict of cookies"""
    itemtype = AuthCookie


class TestBytesHandling(unittest.TestCase):
    """Test cases for bytes input handling"""

    def test_decode_and_parse_json_with_bytes(self):
        """Test _decode_and_parse_json with bytes input"""
        raw_bytes = b'{"u": 2, "x": "sent_2", "e": 1e+20, "o": 271691174}'
        result = _decode_and_parse_json(raw_bytes)

        expected = {"u": 2, "x": "sent_2", "e": 1e+20, "o": 271691174}
        self.assertEqual(result, expected)

    def test_decode_and_parse_json_with_bytearray(self):
        """Test _decode_and_parse_json with bytearray input"""
        raw_data = bytearray(b'{"key": "value", "num": 42}')
        result = _decode_and_parse_json(raw_data)

        expected = {"key": "value", "num": 42}
        self.assertEqual(result, expected)

    def test_decode_and_parse_json_with_string(self):
        """Test _decode_and_parse_json with string input"""
        raw_string = '{"key": "value", "num": 42}'
        result = _decode_and_parse_json(raw_string)

        expected = {"key": "value", "num": 42}
        self.assertEqual(result, expected)

    def test_decode_and_parse_json_with_dict(self):
        """Test _decode_and_parse_json with dict input (passthrough)"""
        input_dict = {"key": "value", "num": 42}
        result = _decode_and_parse_json(input_dict)

        # Should return the same object
        self.assertIs(result, input_dict)

    def test_decode_and_parse_json_with_invalid_utf8(self):
        """Test _decode_and_parse_json with invalid UTF-8 bytes"""
        invalid_bytes = b'\xff{"u":1}'  # Invalid UTF-8
        
        # Should raise UnicodeDecodeError when decode fails
        with self.assertRaises(UnicodeDecodeError):
            _decode_and_parse_json(invalid_bytes)

    def test_decode_and_parse_json_with_invalid_json(self):
        """Invalid JSON should raise JSONDecodeError"""
        invalid_json = '{"u":1'  # Missing closing brace
        with self.assertRaises(JSONDecodeError):
            _decode_and_parse_json(invalid_json)

    def test_jsonrecord_accepts_bytes(self):
        """Test JsonRecord constructor with bytes input"""
        raw = (
            b'{"u": 2, "x": "sent_2", "e": 1e+20, "o": 271691174, '
            b'"m": 1, "c": 0}'
        )

        # This should not raise JsonRecordCoerceError
        cookie = AuthCookie(raw)

        self.assertEqual(cookie.u, 2)
        self.assertEqual(cookie.x, "sent_2")
        self.assertEqual(cookie.e, 1e+20)
        self.assertEqual(cookie.o, 271691174)
        self.assertEqual(cookie.m, 1)
        self.assertEqual(cookie.c, 0)

    def test_from_json_accepts_bytes(self):
        """Test from_json function with bytes input"""
        raw = (
            b'{"u": 3, "x": "sent_3", "e": 1e+21, "o": 271691175, '
            b'"m": 2, "c": 1}'
        )

        # This should not raise JsonRecordCoerceError
        cookie = from_json(AuthCookie, raw)

        self.assertEqual(cookie.u, 3)
        self.assertEqual(cookie.x, "sent_3")
        self.assertEqual(cookie.e, 1e+21)
        self.assertEqual(cookie.o, 271691175)
        self.assertEqual(cookie.m, 2)
        self.assertEqual(cookie.c, 1)

    def test_jsonrecordlist_accepts_bytes(self):
        """Test JsonRecordList constructor with bytes input"""
        raw = (
            b'[{"u": 1, "x": "a", "e": 1, "o": 1, "m": 0, "c": 0}, '
            b'{"u": 2, "x": "b", "e": 2, "o": 2, "m": 1, "c": 0}]'
        )

        # This should not raise JsonRecordCoerceError
        cookie_list = CookieList(raw)

        self.assertEqual(len(cookie_list), 2)
        self.assertEqual(cookie_list[0].x, "a")
        self.assertEqual(cookie_list[1].u, 2)

    def test_jsonrecorddict_accepts_bytes(self):
        """Test JsonRecordDict constructor with bytes input"""
        raw = (
            b'{"first": {"u": 1, "x": "a", "e": 1, "o": 1, "m": 0, "c": 0}, '
            b'"second": {"u": 2, "x": "b", "e": 2, "o": 2, "m": 1, "c": 0}}'
        )

        # This should not raise JsonRecordCoerceError
        cookie_dict = CookieDict(raw)

        self.assertEqual(set(cookie_dict.keys()), {"first", "second"})
        self.assertEqual(cookie_dict["second"].x, "b")
        self.assertEqual(cookie_dict["first"].u, 1)

    def test_bytes_with_unicode_content(self):
        """Test bytes input containing unicode characters"""
        raw = '{"message": "héllo wørld", "value": 42}'.encode('utf-8')

        cookie_data = {"message": "héllo wørld", "value": 42}
        result = _decode_and_parse_json(raw)

        self.assertEqual(result, cookie_data)

    def test_html_content_error(self):
        """HTML content should raise JSONDecodeError when parsed, and same via constructor."""
        html_content = '''
<!-- EF of static content included-->
<html>
<head>
  <title>502: Server Hangup</title>
  <meta http-equiv="content-type" content="text/html; charset=UTF-8">
  <style type="text/css">
'''
        with self.assertRaises(JSONDecodeError):
            _decode_and_parse_json(html_content)
        with self.assertRaises(JSONDecodeError):
            AuthCookie(html_content)

    def test_decode_and_parse_json_json_heuristics(self):
        """Test JSON detection heuristics for various edge cases"""
        # Valid JSON that should be parsed
        test_cases = [
            ('{"key": "value"}', dict, "Simple JSON object"),
            ('[1, 2, 3]', list, "JSON array"),
            ('"hello"', str, "JSON string"),
            ('42', int, "JSON number"),
            ('true', bool, "JSON boolean"),
            ('null', type(None), "JSON null"),
        ]
        
        for test_input, expected_type, description in test_cases:
            with self.subTest(case=description):
                result = _decode_and_parse_json(test_input)
                self.assertIsInstance(result, expected_type,
                                    f"Failed for {description}: "
                                    f"expected {expected_type.__name__}, "
                                    f"got {type(result).__name__}")

    def test_decode_and_parse_json_non_json_content_raises(self):
        """All clearly non-JSON strings should raise JSONDecodeError."""
        test_inputs = [
            '{"key":}',
            'hello world',
            '<html>...</html>',
            '<?xml version="1.0"?>',
            '',
            '   ',
            '{',
            '{}extra',
            'not json at all!',
            '123abc',
        ]
        for s in test_inputs:
            with self.subTest(s=s):
                with self.assertRaises(JSONDecodeError):
                    _decode_and_parse_json(s)

    def test_xml_content_error(self):
        """XML content should raise JSONDecodeError when parsed, and via constructor."""
        xml_content = '<?xml version="1.0"?><root><error>500</error></root>'
        with self.assertRaises(JSONDecodeError):
            _decode_and_parse_json(xml_content)
        with self.assertRaises(JSONDecodeError):
            AuthCookie(xml_content)


if __name__ == '__main__':
    unittest.main()
