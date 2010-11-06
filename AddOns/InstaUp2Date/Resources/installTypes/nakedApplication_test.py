#!/usr/bin/python

import os, unittest

from .workItem			import workItem
from .tempFolderManager	import tempFolderManager

class nakedApplication_test(unittest.TestCase):
	
	def test_folderInstantiation(self):
		
		testPath = tempFolderManager.getNewTempFolder()
		
		testAppFolderPath = os.path.join(testPath, 'TestApp.app')
		os.mkdir(testAppFolderPath)
		os.mkdir(os.path.join(testAppFolderPath, "Contents"))
		open(os.path.join(testAppFolderPath, "Contents", "Info.plist"), 'w').close()
		
		# -- test as folder
		
		testItem = workItem(testPath)
		self.assertTrue(testItem is not None, 'When first instantiation work item with "%s", did not get any output' % testPath)
		
		# find the files and figure out what this is
		testItem.locateFiles()
		
		# subtype tests
		self.assertEqual(testItem.getContainerType(), 'folder', 'The test item container should be a "folder", but was a "%s"' % testItem.getContainerType())
		
		self.assertEqual(testItem.getActionType(), "nakedApplication", 'When testing "%s" as a workItem it was expected to be a "nakedApplication", but it was: %s' % (testPath, testItem.getActionType()))
		
		# -- test as bundle
		
		#self.assertEqual(testItem.getContainerType(), 'folder'
		
#		self.assertEqual(testItem.getActionType(), "nakedApplication", 'When testing "%s" as a workItem it was expected to be a "nakedApplication", but it was: %s' % (testPath, testItem.getActionType()))
		
#		self.assertEqual([testPath], testItem.getTopLevelItems(), 'Expected the item "%s" to give "[%s]" for getTopLevelItems, but got: %s' % (testPath, testPath, testItem.getTopLevelItems()))
