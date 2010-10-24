#!/usr/bin/python

import os, unittest

import file
from .container		import container

class file_test(unittest.TestCase):
	
	def test_simpleFile(self):
		'''Test that the /etc/authorization file is processed as a file'''
		
		thisItem = container('/etc/authorization')
		
		self.assertEqual(thisItem.getContainerType(), 'file', 'Expected containerType for /etc/authorization to be "file", but got: ' + thisItem.getContainerType())