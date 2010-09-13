#!/usr/bin/python

import os, unittest

import volume
from .containerController		import newContainerForPath

class volume_test(unittest.TestCase):
	
	def test_rootVolume(self):
		'''Test that the / is processed as a volume'''
		
		thisItem = newContainerForPath('/')
		
		self.assertEqual(thisItem.getContainerType(), 'volume', 'Expected containerType for / to be "volume", but got: ' + thisItem.getContainerType())