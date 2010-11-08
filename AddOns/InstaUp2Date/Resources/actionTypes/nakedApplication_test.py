#!/usr/bin/python

import os, unittest

from .workItem			import workItem
from .tempFolderManager	import tempFolderManager

class nakedApplication_test(unittest.TestCase):
	
	def instantionationTestHelper(self, sourceItem, sourceChecksum, expectedContainerType, expectedActionType):
		
		testItem = workItem(sourceItem, checksum=sourceChecksum)
		self.assertTrue(testItem is not None, 'Instantiation work item with "%s", did not get any output' % sourceItem)
		
		# find the files and figure out what this is
		testItem.locateFiles()
		
		# subtype tests
		self.assertEqual(testItem.getContainerType(), expectedContainerType, 'The test item container for "%s" should be a "%s", but was a "%s"' % (sourceItem, expectedContainerType, testItem.getContainerType()))
		
		self.assertEqual(testItem.getActionType(), expectedActionType, 'When testing "%s" as a workItem it was expected to be a "%s", but it was: %s' % (sourceItem, expectedActionType, testItem.getActionType()))
	
	def test_folderSetup(self):
		
		containingFolderPath = tempFolderManager.getNewTempFolder(prefix="folderWithApp.")
		
		testAppFolderPath = os.path.join(containingFolderPath, 'TestApp.app')
		os.mkdir(testAppFolderPath)
		os.mkdir(os.path.join(testAppFolderPath, "Contents"))
		open(os.path.join(testAppFolderPath, "Contents", "Info.plist"), 'w').close()
		
		testAppFolderChecksum = 'sha1:dc5ae495ff0c7588eb1bd30cd7aadba95e43687d'
		testAppBundleChecksum = 'sha1:b9596a9ad213402514bcf150c96971d70e0f6c35'
		
		# -- instantiation as folder
		
		self.instantionationTestHelper(containingFolderPath, testAppFolderChecksum, 'folder', 'nakedApplication')
		
		# -- instantiation as bundle
		
		self.instantionationTestHelper(testAppFolderPath, testAppBundleChecksum, 'bundle', 'nakedApplication')
		
		# -- install from folder
		
		folderInstallTarget = tempFolderManager.getNewTempFolder(prefix="folderInstalTarget.")
		os.mkdir(os.path.join(folderInstallTarget, 'Applications'))
		
		testItem = workItem(containingFolderPath, checksum=testAppFolderChecksum)
		testItem.locateFiles()
		
		self.assertFalse(os.path.exists(os.path.join(folderInstallTarget, 'Applications', 'TestApp.app')), 'The app already existed in the test path before performActionOnVolume')
		testItem.performActionOnVolume(folderInstallTarget)
		self.assertTrue(os.path.exists(os.path.join(folderInstallTarget, 'Applications', 'TestApp.app')), 'The app was not in the target volume after performActionOnVolume')

		# -- install from bundle
		
		folderInstallTarget = tempFolderManager.getNewTempFolder(prefix="folderInstalTarget.")
		os.mkdir(os.path.join(folderInstallTarget, 'Applications'))
		
		testItem = workItem(testAppFolderPath, checksum=testAppBundleChecksum)
		testItem.locateFiles()
		
		self.assertFalse(os.path.exists(os.path.join(folderInstallTarget, 'Applications', 'TestApp.app')), 'The app already existed in the test path before performActionOnVolume')
		testItem.performActionOnVolume(folderInstallTarget)
		self.assertTrue(os.path.exists(os.path.join(folderInstallTarget, 'Applications', 'TestApp.app')), 'The app was not in the target volume after performActionOnVolume')