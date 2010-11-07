#!/usr/bin/python

import os, unittest

import volume
from .container		import container

class volume_test(unittest.TestCase):
	
	def test_rootVolume(self):
		'''Test that the / is processed as a volume'''
		
		itemPath = '/'
		testItem = container(itemPath)
		
		self.assertEqual(testItem.getType(), 'volume', 'Expected containerType for %s to be "volume", but got: %s' % (itemPath, testItem.getType()))
		
		# bsdPath
		self.assertTrue(testItem.bsdPath is not None)
		
		# test that bsd paths are treated the same
		self.assertEqual(container(testItem.bsdPath), testItem, 'Expected item from "%s" and the bsdPath to that (%s) to result in the same item, they did not' % (itemPath, testItem.bsdPath))
		
		# check that getTopLevelItems returns the correct items
		expectedItems = [os.path.join(itemPath, itemName) for itemName in os.listdir(itemPath)]
		self.assertEqual(expectedItems, testItem.getTopLevelItems(), 'Expected results of getTopLevelItems for "%s" to be "%s", but got: %s' % (itemPath, expectedItems, testItem.getTopLevelItems()))

if __name__ == '__main__':
	unittest.main()
