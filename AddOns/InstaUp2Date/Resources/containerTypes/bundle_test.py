#!/usr/bin/python

import os, unittest

import bundle
try:
	from .container		import container
except ImportError:
	from ..container		import container

class folder_test(unittest.TestCase):
	
	def test_applicationsFolder(self):
		'''Test that the Mail.app folder is processed as a bundle'''
		
		thisItem = container('/Applications/Mail.app')
		
		self.assertEqual(thisItem.getType(), 'bundle', 'Expected containerType for /Applications/Mail.app to be "bundle", but got: ' + thisItem.getType())
		
		self.assertEqual(thisItem.getTopLevelItems(), [targetPath], 'Expected the getTopLevelItems results for %s to be [%s], but got: %s' % (targetPath, targetPath, thisItem.getTopLevelItems()))
