#!/usr/bin/python

import os, unittest

import folder
from .containerController	import containerController

class folder_test(unittest.TestCase):
	
	def test_applicationsFolder(self):
		'''Test that the Applications folder is processed as a folder'''
		
		thisItem = containerController.newItemForPath('/Applications')
		
		self.assertEqual(thisItem.getContainerType(), 'folder', 'Expected containerType for /Applications to be "folder", but got: ' + thisItem.getContainerType())