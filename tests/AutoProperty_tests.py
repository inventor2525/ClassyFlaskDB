from typing import List
from ClassyFlaskDB.helpers.Decorators.AutoProperty import AutoProperty
import unittest

import json
from copy import deepcopy
	
class AutoProperty_tests(unittest.TestCase):
	def test_auto_backingfield(self):
		tester = self
		tester.field4_getter_called = False
		tester.field5_getter_called = False
		
		class Thing():
			@AutoProperty()
			def field1(self, value):
				self._field1 = value*2
			
			@AutoProperty(default=1)
			def field2(self, value):
				tester.assertEqual(self._field2, 1)
				self._field2 = value*3
			
			@AutoProperty(default_factory=lambda: 2)
			def field3(self, value):
				tester.assertEqual(self._field3, 2)
				self._field3 = value*4
			
			@AutoProperty(default_factory=lambda: 3, use_getter=True)
			def field4(self):
				if not tester.field4_getter_called:
					tester.assertEqual(self._field4, 3)
					tester.field4_getter_called = True
				return self._field4*5
			
			@AutoProperty(default=4, use_getter=True)
			def field5(self):
				if not tester.field5_getter_called:
					tester.assertEqual(self._field5, 4)
					tester.field5_getter_called = True
				return self._field5*6
			
		t = Thing()
		self.assertEqual(t.field1, None)
		t.field1 = -1
		self.assertEqual(t.field1, -2)
		self.assertEqual(t._field1, -2)
		
		self.assertEqual(t.field2, 1)
		t.field2 = -2
		self.assertEqual(t.field2, -6)
		self.assertEqual(t._field2, -6)
		
		self.assertEqual(t.field3, 2)
		t.field3 = -3
		self.assertEqual(t.field3, -12)
		self.assertEqual(t._field3, -12)
		
		self.assertEqual(t.field4, 15)
		t.field4 = -4
		self.assertEqual(t.field4, -20)
		self.assertEqual(t._field4, -4)
		
		self.assertEqual(t.field5, 24)
		t.field5 = -5
		self.assertEqual(t.field5, -30)
		self.assertEqual(t._field5, -5)
if __name__ == '__main__':
	unittest.main()