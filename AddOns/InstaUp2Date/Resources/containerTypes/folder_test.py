#!/usr/bin/python

import os, unittest

import folder
from .container		import container

class folder_test(unittest.TestCase):
	
	def test_applicationsFolder(self):
		'''Test that the Applications folder is processed as a folder'''
		
		thisItem = container('/Applications')
		
		self.assertEqual(thisItem.getContainerType(), 'folder', 'Expected containerType for /Applications to be "folder", but got: ' + thisItem.getContainerType())