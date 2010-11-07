#!/usr/bin/python

import os, unittest

from .workItem			import workItem
from .tempFolderManager	import tempFolderManager

class nakedApplication_test(unittest.TestCase):
	
	def instantionationTestHelper(self, sourceInformation, expectedContainerType, expectedActionType):
		
		testItem = workItem(sourceInformation)
		self.assertTrue(testItem is not None, 'Instantiation work item with "%s", did not get any output' % sourceInformation)
		
		# find the files and figure out what this is
		testItem.locateFiles()
		
		# subtype tests
		self.assertEqual(testItem.getContainerType(), expectedContainerType, 'The test item container for "%s" should be a "%s", but was a "%s"' % (sourceInformation, expectedContainerType, testItem.getContainerType()))
		
		self.assertEqual(testItem.getActionType(), expectedActionType, 'When testing "%s" as a workItem it was expected to be a "%s", but it was: %s' % (sourceInformation, expectedActionType, testItem.getActionType()))
	
	def test_folderInstantiation(self):
		
		containingFolderPath = tempFolderManager.getNewTempFolder(prefix="folderWithApp.")
		
		testAppFolderPath = os.path.join(containingFolderPath, 'TestApp.app')
		os.mkdir(testAppFolderPath)
		os.mkdir(os.path.join(testAppFolderPath, "Contents"))
		open(os.path.join(testAppFolderPath, "Contents", "Info.plist"), 'w').close()
		
		# -- test as folder
		
		self.instantionationTestHelper(containingFolderPath, 'folder', 'nakedApplication')
		
		# -- test as bundle
		
		self.instantionationTestHelper(testAppFolderPath, 'bundle', 'nakedApplication')
