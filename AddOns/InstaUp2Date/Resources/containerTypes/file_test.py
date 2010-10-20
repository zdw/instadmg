#!/usr/bin/python

import os, unittest

import file
from .containerController	import containerController

class file_test(unittest.TestCase):
	
	def test_simpleFile(self):
		'''Test that the /etc/authorization file is processed as a file'''
		
		thisItem = containerController.newItemForPath('/etc/authorization')
		
		self.assertEqual(thisItem.getContainerType(), 'file', 'Expected containerType for /etc/authorization to be "file", but got: ' + thisItem.getContainerType())