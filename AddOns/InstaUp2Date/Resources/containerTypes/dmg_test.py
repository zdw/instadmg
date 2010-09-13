#!/usr/bin/python

import os, unittest

import dmg
from .containerController		import newContainerForPath
from .commonConfiguration		import standardOutputFolder
from .tempFolderManager			import tempFolderManager

class dmg_test(unittest.TestCase):
	
	def test_outputFiles(self):
		'''Test the class with a dmg from the outputFiles folder'''
		
		testItem = None
		for thisItem in os.listdir(standardOutputFolder):
			if os.path.splitext(thisItem)[1].lower() == '.dmg':
				testItem = thisItem
				break
		
		if testItem is None:
			print("\nWarning: There were no dmg's in the output folder, so no dmg testing could be done")
			return
		
		# -- simple tests
		
		# confirm that the class picks up on it as a dmg
		testItemPath = os.path.join(standardOutputFolder, testItem)
		testItem = newContainerForPath(testItemPath)
		self.assertEqual(testItem.getContainerType(), 'dmg', 'Expected containerType for "%s" to be "dmg", but got: %s' % (testItemPath, testItem.getContainerType()))
		
		# check to see if the item is mounted
		self.assertEqual(testItem.getMountPoint(), None, 'Did not expect the item (%s) to be mounted, but it was at: %s' % (testItemPath, testItem.getMountPoint()))
		
		# try mounting the item without any options
		testItem.mount()
		self.assertTrue(testItem.getMountPoint() is not None, 'Mounting the item (%s) with no options did not get a mount point' % testItemPath)
		
		# test that the content looks like it is there
		actualMountPoint = testItem.getMountPoint()
		self.assertTrue(os.path.ismount(actualMountPoint), 'After mounting the item (%s) with no options, the reported mount point (%s) was not a mount' % (testItemPath, actualMountPoint))
		self.assertTrue(os.path.isdir(os.path.join(actualMountPoint, 'System')), 'After mounting the item (%s) with no options, the System folder was not in the mount point')
		
		# unmount the volume
		testItem.unmount()
		actualMountPoint = testItem.getMountPoint()
		self.assertTrue(actualMountPoint is None, 'After unmounting the item (%s) there was still a mount point: %s' % (testItemPath, actualMountPoint))
		
		# -- mountpoint tests
		
		targetMountPoint = tempFolderManager.getNewMountPoint()
		actualMountPoint = testItem.mount(mountPoint=targetMountPoint)
		self.assertEqual(targetMountPoint, actualMountPoint, 'Mounting the item (%s) at a specified mount point (%s) returned %s' % (testItemPath, targetMountPoint, actualMountPoint))
		self.assertEqual(targetMountPoint, testItem.getMountPoint(), 'Mounting the item (%s) at a specified mount point (%s) resulted in a mount point of %s' % (testItemPath, targetMountPoint, testItem.getMountPoint()))
		
		# -- singleton test - make sure the same item is only created once
		
		duplicateItem = newContainerForPath(testItemPath)
		self.assertEqual(duplicateItem, testItem, 'When feeding the same dmg (%s) into newContainerForPath twice, got seperate items')
