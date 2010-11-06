#!/usr/bin/python

import os, unittest

import folder
from .container		import container

class folder_test(unittest.TestCase):
	
	def test_applicationsFolder(self):
		'''Test that the Applications folder is processed as a folder'''
		
		testPath = '/System'
		thisItem = container(testPath)
		
		self.assertEqual(thisItem.getType(), 'folder', 'Expected containerType for %s to be "folder", but got: %s' % (testPath, thisItem.getType()))
		
		self.assertEqual(thisItem.getTopLevelItems(), os.listdir(testPath), 'Expected getType for %s to be %s, but got: %s' % (testPath, os.listdir(testPath), thisItem.getTopLevelItems()))
