# -*- coding: utf-8 -*-
'''
test_headers.py

Copyright 2012 Andres Riancho

This file is part of w3af, w3af.sourceforge.net .

w3af is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation version 2 of the License.

w3af is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with w3af; if not, write to the Free Software
Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
'''
import unittest

from core.data.dc.headers import Headers


class TestHeaders(unittest.TestCase):

    def test_empty(self):
        self.assertEquals(Headers([]), {})

    def test_simple(self):
        headers = Headers([('a', 'b')])

        self.assertIn('a', headers)
        self.assertEqual(headers['a'], 'b')

    def test_raises(self):
        self.assertRaises(TypeError, Headers, {})
        
    def test_build_with_headers(self):
        headers = Headers([('a', 'b')])
        headers = Headers(headers)
        
        self.assertIn('a', headers)
        self.assertEqual(headers['a'], 'b')

    def test_str(self):
        headers = Headers([('a', 'b')])

        self.assertEqual(str(headers), 'a: b\n')

    def test_str_multi(self):
        headers = Headers([('a', 'b'), ('1', '2')])

        self.assertEqual(str(headers), 'a: b\n1: 2\n')

    def test_unicode(self):
        headers = Headers([('a', 'b')])

        self.assertEqual(unicode(headers), 'a: b\n')

    def test_str_strange(self):
        header_value = ''.join(chr(i) for i in xrange(256))
        headers = Headers([(u'Hola', header_value)])
        
        # I don't assert in a stricter way because the output depends on
        # smart_unicode which might change in the future
        self.assertIn('Hola: \x00\x01\x02', str(headers))
        
    def test_repeated_overwrite(self):
        headers = Headers([('a', 'b'), ('a', '3')])

        self.assertIn('a', headers)
        self.assertEqual(headers['a'], '3')

    def test_special_chars(self):
        headers = Headers([('á', 'ç')])

        self.assertIn('á', headers)
        self.assertEqual(headers['á'], 'ç')

    def test_add_later(self):
        headers = Headers([('a', 'b')])
        headers['c'] = '2'

        self.assertIn('a', headers)
        self.assertEqual(headers['a'], 'b')
        self.assertIn('c', headers)
        self.assertEqual(headers['c'], '2')

    def test_overwrite(self):
        headers = Headers([('a', 'b')])
        headers['a'] = '2'

        self.assertIn('a', headers)
        self.assertEqual(headers['a'], '2')

    def test_headers_case_sensitive(self):
        upper_headers = Headers([('Abc', 'b')])
        lower_headers = Headers([('abc', 'b')])

        self.assertNotEqual(upper_headers, lower_headers)

    def test_clone_with_list_values(self):
        headers = Headers([('a', 'b'), ('c', 'd')])
        cloned = headers.clone_with_list_values()

        self.assertEqual(cloned['a'], ['b'])
        self.assertEqual(cloned['c'], ['d'])