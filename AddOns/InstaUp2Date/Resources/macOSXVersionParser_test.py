#!/usr/bin/python

import unittest

import findBaseOS

class test_macOSXVersion(unittest.TestCase):
	
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
		self.comparisonTest(findBaseOS.macOSXVersion('9A581'), findBaseOS.macOSXVersion('9L30'), "<", True)
		self.comparisonTest(findBaseOS.macOSXVersion('9A581'), findBaseOS.macOSXVersion('9L30'), ">", False)
		self.comparisonTest(findBaseOS.macOSXVersion('9A581'), findBaseOS.macOSXVersion('9L30'), "=", False)
		self.comparisonTest(findBaseOS.macOSXVersion('9A581'), findBaseOS.macOSXVersion('9L30'), "!=", True)
		
		# 10.5 to 10.6
		self.comparisonTest(findBaseOS.macOSXVersion('9A581'), findBaseOS.macOSXVersion('10A432'), "<", True)
		self.comparisonTest(findBaseOS.macOSXVersion('9A581'), findBaseOS.macOSXVersion('10A432'), ">", False)
		self.comparisonTest(findBaseOS.macOSXVersion('9A581'), findBaseOS.macOSXVersion('10A432'), "=", False)
		self.comparisonTest(findBaseOS.macOSXVersion('9A581'), findBaseOS.macOSXVersion('10A432'), "!=", True)
		
		# 10.6 to 10.6.4
		self.comparisonTest(findBaseOS.macOSXVersion('10A432'), findBaseOS.macOSXVersion('10F569'), "<", True)
		self.comparisonTest(findBaseOS.macOSXVersion('10A432'), findBaseOS.macOSXVersion('10F569'), ">", False)
		self.comparisonTest(findBaseOS.macOSXVersion('10A432'), findBaseOS.macOSXVersion('10F569'), "=", False)
		self.comparisonTest(findBaseOS.macOSXVersion('10A432'), findBaseOS.macOSXVersion('10F569'), "!=", True)
		
		# 10.6.4 to 10.6.4
		self.comparisonTest(findBaseOS.macOSXVersion('10F569'), findBaseOS.macOSXVersion('10F569'), "<", False)
		self.comparisonTest(findBaseOS.macOSXVersion('10F569'), findBaseOS.macOSXVersion('10F569'), ">", False)
		self.comparisonTest(findBaseOS.macOSXVersion('10F569'), findBaseOS.macOSXVersion('10F569'), "=", True)
		self.comparisonTest(findBaseOS.macOSXVersion('10F569'), findBaseOS.macOSXVersion('10F569'), "!=", False)
		
		# 10.6.4 to 10.6.4 with an extra
		self.comparisonTest(findBaseOS.macOSXVersion('10F569'), findBaseOS.macOSXVersion('10F569a'), "<", True)
		self.comparisonTest(findBaseOS.macOSXVersion('10F569'), findBaseOS.macOSXVersion('10F569a'), ">", False)
		self.comparisonTest(findBaseOS.macOSXVersion('10F569'), findBaseOS.macOSXVersion('10F569a'), "=", False)
		self.comparisonTest(findBaseOS.macOSXVersion('10F569'), findBaseOS.macOSXVersion('10F569a'), "!=", True)
		
		# 10.6.4 with an extra to 10.6.4
		self.comparisonTest(findBaseOS.macOSXVersion('10F569a'), findBaseOS.macOSXVersion('10F569'), "<", False)
		self.comparisonTest(findBaseOS.macOSXVersion('10F569a'), findBaseOS.macOSXVersion('10F569'), ">", True)
		self.comparisonTest(findBaseOS.macOSXVersion('10F569a'), findBaseOS.macOSXVersion('10F569'), "=", False)
		self.comparisonTest(findBaseOS.macOSXVersion('10F569a'), findBaseOS.macOSXVersion('10F569'), "!=", True)

		# 10.6.4 with an extra to 10.6.4 with the same extra
		self.comparisonTest(findBaseOS.macOSXVersion('10F569a'), findBaseOS.macOSXVersion('10F569a'), "<", False)
		self.comparisonTest(findBaseOS.macOSXVersion('10F569a'), findBaseOS.macOSXVersion('10F569a'), ">", False)
		self.comparisonTest(findBaseOS.macOSXVersion('10F569a'), findBaseOS.macOSXVersion('10F569a'), "=", True)
		self.comparisonTest(findBaseOS.macOSXVersion('10F569a'), findBaseOS.macOSXVersion('10F569a'), "!=", False)
		
		# 10.6.4 with an extra to 10.6.4 with a different extra
		self.comparisonTest(findBaseOS.macOSXVersion('10F569a'), findBaseOS.macOSXVersion('10F569b'), "<", True)
		self.comparisonTest(findBaseOS.macOSXVersion('10F569a'), findBaseOS.macOSXVersion('10F569b'), ">", False)
		self.comparisonTest(findBaseOS.macOSXVersion('10F569a'), findBaseOS.macOSXVersion('10F569b'), "=", False)
		self.comparisonTest(findBaseOS.macOSXVersion('10F569a'), findBaseOS.macOSXVersion('10F569b'), "!=", True)
				
		# -- object with string comparisons
		
		# 10.5 to 10.5.8
		self.comparisonTest(findBaseOS.macOSXVersion('9A581'), '9L30', "<", True)
		
		# 10.5 to 10.6
		self.comparisonTest(findBaseOS.macOSXVersion('9A581'), '10A432', "<", True)
		
		# 10.6 to 10.6.4
		self.comparisonTest(findBaseOS.macOSXVersion('10A432'), '10F569', "<", True)
		
		# 10.6.4 to 10.6.4
		self.comparisonTest(findBaseOS.macOSXVersion('10F569'), '10F569', "<", False)
		
		# 10.6.4 to 10.6.4 with an extra
		self.comparisonTest(findBaseOS.macOSXVersion('10F569'), '10F569a', "<", True)
		self.comparisonTest(findBaseOS.macOSXVersion('10F569a'), '10F569', "<", False)
		
		# ToDo: volume tests

if __name__ == '__main__':
	unittest.main()