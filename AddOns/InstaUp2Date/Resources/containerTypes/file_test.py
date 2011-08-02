#!/usr/bin/python

import os, unittest

import file
try:
	from .container		import container
except ImportError:
	from ..container		import container

class file_test(unittest.TestCase):
	
	def test_simpleFile(self):
		'''Test that the /etc/authorization file is processed as a file'''
		
		targetPath	= '/etc/authorization'
		thisItem	= container(targetPath)
		
		self.assertEqual(thisItem.getType(), 'file', 'Expected containerType for %s to be "file", but got: %s' % (targetPath, thisItem.getType()))
		
		self.assertEqual(thisItem.getTopLevelItems(), [targetPath], 'Expected the getTopLevelItems results for %s to be [%s], but got: %s' % (targetPath, targetPath, thisItem.getTopLevelItems()))
