#!/usr/bin/python

import unittest

import macOSXVersionParser

class test_macOSXVersionParser(unittest.TestCase):
	
	def comparisonTest(self, left, right, operation, expectedResult):
		actualResult = None
		if operation == "<":
			actualResult = left < right
		elif operation == ">":
			actualResult = left > right
		elif operation == "=":
			actualResult = left == right
		elif operation == "!=":
			actualResult = left != right
		else:
			raise Exception('Did not understand operation: ' + operation)
			
		self.assertEqual(expectedResult, actualResult, 'Testing if "%s" %s "%s", should have gotten "%s" but got "%s"' % (left, actualResult, right, expectedResult, actualResult))
	
	def test_lessThanComparisons(self):
		
		# -- direct object comparisons
		
		# 10.5 to 10.5.8
		self.comparisonTest(macOSXVersionParser.macOSXVersion('9A581'), macOSXVersionParser.macOSXVersion('9L30'), "<", True)
		self.comparisonTest(macOSXVersionParser.macOSXVersion('9A581'), macOSXVersionParser.macOSXVersion('9L30'), ">", False)
		self.comparisonTest(macOSXVersionParser.macOSXVersion('9A581'), macOSXVersionParser.macOSXVersion('9L30'), "=", False)
		self.comparisonTest(macOSXVersionParser.macOSXVersion('9A581'), macOSXVersionParser.macOSXVersion('9L30'), "!=", True)
		
		# 10.5 to 10.6
		self.comparisonTest(macOSXVersionParser.macOSXVersion('9A581'), macOSXVersionParser.macOSXVersion('10A432'), "<", True)
		self.comparisonTest(macOSXVersionParser.macOSXVersion('9A581'), macOSXVersionParser.macOSXVersion('10A432'), ">", False)
		self.comparisonTest(macOSXVersionParser.macOSXVersion('9A581'), macOSXVersionParser.macOSXVersion('10A432'), "=", False)
		self.comparisonTest(macOSXVersionParser.macOSXVersion('9A581'), macOSXVersionParser.macOSXVersion('10A432'), "!=", True)
		
		# 10.6 to 10.6.4
		self.comparisonTest(macOSXVersionParser.macOSXVersion('10A432'), macOSXVersionParser.macOSXVersion('10F569'), "<", True)
		self.comparisonTest(macOSXVersionParser.macOSXVersion('10A432'), macOSXVersionParser.macOSXVersion('10F569'), ">", False)
		self.comparisonTest(macOSXVersionParser.macOSXVersion('10A432'), macOSXVersionParser.macOSXVersion('10F569'), "=", False)
		self.comparisonTest(macOSXVersionParser.macOSXVersion('10A432'), macOSXVersionParser.macOSXVersion('10F569'), "!=", True)
		
		# 10.6.4 to 10.6.4
		self.comparisonTest(macOSXVersionParser.macOSXVersion('10F569'), macOSXVersionParser.macOSXVersion('10F569'), "<", False)
		self.comparisonTest(macOSXVersionParser.macOSXVersion('10F569'), macOSXVersionParser.macOSXVersion('10F569'), ">", False)
		self.comparisonTest(macOSXVersionParser.macOSXVersion('10F569'), macOSXVersionParser.macOSXVersion('10F569'), "=", True)
		self.comparisonTest(macOSXVersionParser.macOSXVersion('10F569'), macOSXVersionParser.macOSXVersion('10F569'), "!=", False)
		
		# 10.6.4 to 10.6.4 with an extra
		self.comparisonTest(macOSXVersionParser.macOSXVersion('10F569'), macOSXVersionParser.macOSXVersion('10F569a'), "<", True)
		self.comparisonTest(macOSXVersionParser.macOSXVersion('10F569'), macOSXVersionParser.macOSXVersion('10F569a'), ">", False)
		self.comparisonTest(macOSXVersionParser.macOSXVersion('10F569'), macOSXVersionParser.macOSXVersion('10F569a'), "=", False)
		self.comparisonTest(macOSXVersionParser.macOSXVersion('10F569'), macOSXVersionParser.macOSXVersion('10F569a'), "!=", True)
		
		# 10.6.4 with an extra to 10.6.4
		self.comparisonTest(macOSXVersionParser.macOSXVersion('10F569a'), macOSXVersionParser.macOSXVersion('10F569'), "<", False)
		self.comparisonTest(macOSXVersionParser.macOSXVersion('10F569a'), macOSXVersionParser.macOSXVersion('10F569'), ">", True)
		self.comparisonTest(macOSXVersionParser.macOSXVersion('10F569a'), macOSXVersionParser.macOSXVersion('10F569'), "=", False)
		self.comparisonTest(macOSXVersionParser.macOSXVersion('10F569a'), macOSXVersionParser.macOSXVersion('10F569'), "!=", True)

		# 10.6.4 with an extra to 10.6.4 with the same extra
		self.comparisonTest(macOSXVersionParser.macOSXVersion('10F569a'), macOSXVersionParser.macOSXVersion('10F569a'), "<", False)
		self.comparisonTest(macOSXVersionParser.macOSXVersion('10F569a'), macOSXVersionParser.macOSXVersion('10F569a'), ">", False)
		self.comparisonTest(macOSXVersionParser.macOSXVersion('10F569a'), macOSXVersionParser.macOSXVersion('10F569a'), "=", True)
		self.comparisonTest(macOSXVersionParser.macOSXVersion('10F569a'), macOSXVersionParser.macOSXVersion('10F569a'), "!=", False)
		
		# 10.6.4 with an extra to 10.6.4 with a different extra
		self.comparisonTest(macOSXVersionParser.macOSXVersion('10F569a'), macOSXVersionParser.macOSXVersion('10F569b'), "<", True)
		self.comparisonTest(macOSXVersionParser.macOSXVersion('10F569a'), macOSXVersionParser.macOSXVersion('10F569b'), ">", False)
		self.comparisonTest(macOSXVersionParser.macOSXVersion('10F569a'), macOSXVersionParser.macOSXVersion('10F569b'), "=", False)
		self.comparisonTest(macOSXVersionParser.macOSXVersion('10F569a'), macOSXVersionParser.macOSXVersion('10F569b'), "!=", True)
				
		# -- object with string comparisons
		
		# 10.5 to 10.5.8
		self.comparisonTest(macOSXVersionParser.macOSXVersion('9A581'), '9L30', "<", True)
		
		# 10.5 to 10.6
		self.comparisonTest(macOSXVersionParser.macOSXVersion('9A581'), '10A432', "<", True)
		
		# 10.6 to 10.6.4
		self.comparisonTest(macOSXVersionParser.macOSXVersion('10A432'), '10F569', "<", True)
		
		# 10.6.4 to 10.6.4
		self.comparisonTest(macOSXVersionParser.macOSXVersion('10F569'), '10F569', "<", False)
		
		# 10.6.4 to 10.6.4 with an extra
		self.comparisonTest(macOSXVersionParser.macOSXVersion('10F569'), '10F569a', "<", True)
		self.comparisonTest(macOSXVersionParser.macOSXVersion('10F569a'), '10F569', "<", False)
		
		# ToDo: volume tests

if __name__ == '__main__':
	unittest.main()