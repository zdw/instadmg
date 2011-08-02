#!/usr/bin/python

import os, unittest

import folder
try:
	from .container		import container
except ImportError:
	from ..container		import container

class folder_test(unittest.TestCase):
	
	def test_applicationsFolder(self):
		'''Test that the Applications folder is processed as a folder'''
		
		testPath = '/System'
		thisItem = container(testPath)
		
		self.assertEqual(thisItem.getType(), 'folder', 'Expected containerType for %s to be "folder", but got: %s' % (testPath, thisItem.getType()))
		
		expectedItems = [os.path.join(testPath, itemName) for itemName in os.listdir(testPath)]
		self.assertEqual(thisItem.getTopLevelItems(), expectedItems, 'Expected getType for %s to be %s, but got: %s' % (testPath, expectedItems, thisItem.getTopLevelItems()))
