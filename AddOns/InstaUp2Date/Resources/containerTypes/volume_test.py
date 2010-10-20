#!/usr/bin/python

import os, unittest

import volume
from .containerController	import containerController

class volume_test(unittest.TestCase):
	
	def test_rootVolume(self):
		'''Test that the / is processed as a volume'''
		
		thisItem = containerController.newItemForPath('/')
		self.assertEqual(thisItem.getContainerType(), 'volume', 'Expected containerType for / to be "volume", but got: ' + thisItem.getContainerType())
		
		# bsdPath
		self.assertTrue(thisItem.bsdPath is not None)
		
		# test that bsd paths are treated the same
		duplicateItem = containerController.newItemForPath(thisItem.bsdPath)
		self.assertEqual(duplicateItem, thisItem, 'Expected item from "/" and the bsdPath to that (%s) to result in the same item, they did not' % thisItem.bsdPath)


if __name__ == '__main__':
	unittest.main()
