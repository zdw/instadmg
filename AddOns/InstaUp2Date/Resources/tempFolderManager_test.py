#!/usr/bin/python

from __future__ import with_statement

import os, tempfile, unittest, shutil
from tempFolderManager import tempFolderManager
from testingHelpers import generateSomeContent

class setupTests(unittest.TestCase):
	
	def test_basicClassSetup(self):
		'''Setup the class, and make sure it is running'''
		
		mainTempFolder = tempFolderManager.setDefaultFolder(None)
		
		# output tests
		self.assertTrue(mainTempFolder is not None, 'Calling setDefaultFolder with no input returned None')
		self.assertTrue(os.path.isdir(mainTempFolder), 'Calling setDefaultFolder with no input did not return a valid folder')
		
		# defaultFolder value tests
		self.assertTrue(tempFolderManager.defaultFolder is not None, 'When calling setDefaultFolder with no input the default folder path in tempFolderManager was not set')
		self.assertEqual(mainTempFolder, tempFolderManager.defaultFolder, 'When calling setDefaultFolder with no input the default folder path that setDefaultFolder returned (%s) was not set internally in tempFolderManager (%s)' % (mainTempFolder, tempFolderManager.defaultFolder))
		self.assertTrue(tempFolderManager.defaultFolder.startswith('/private/tmp'), 'The tempFolderManager class did not auto-generate a folder in the expected place (/private/tmp) but rather: ' + tempFolderManager.defaultFolder)
		
		# check that setDefaultFolder and getDefaultFolder return the same things
		getValue = tempFolderManager.getDefaultFolder()
		setValue = tempFolderManager.setDefaultFolder()
		self.assertEqual(getValue, setValue, 'setDefaultFolder and getDefaultFolder did not return the same vaules: "%s" vs. "%s"' % (getValue, setValue))
	
	def test_targetdDefaultFolder(self):
		'''Test that default folders can be created at specified locations'''
		
		target = tempfile.mkdtemp(dir='/tmp')
		result = tempFolderManager.setDefaultFolder(target)
		self.assertTrue(os.path.samefile(target, result), 'When setDefaultFolder was given a target location of "%s" it returned: %s' % (target, result))
		self.assertTrue(os.path.samefile(target, tempFolderManager.defaultFolder), 'When setDefaultFolder was given a target location of "%s" it set the internal default folder to: %s' % (target, tempFolderManager.defaultFolder))
		self.assertEqual(tempFolderManager.getDefaultFolder(), result, 'getDefaultFolder did not return the same location as setDefaultFolder did: "%s" vs "%s"' % (tempFolderManager.getDefaultFolder(), result))
	
	def test_multipleDefaultFolders(self):
		'''SetupMultiple default folders, and see that they are cleaned up with cleanupForExit'''
		
		# create the first target
		firstTarget = tempfile.mkdtemp(dir='/tmp')
		firstResult = tempFolderManager.setDefaultFolder(firstTarget)
		self.assertTrue(os.path.samefile(firstTarget, firstResult), 'When setDefaultFolder was given a target location of "%s" it returned: %s' % (firstTarget, firstResult))
		generateSomeContent(firstTarget)
		
		# create the second target
		secondTarget = tempfile.mkdtemp(dir='/tmp')
		self.assertNotEqual(firstTarget, secondTarget, 'Error in tempfile module: two calls to mkdtemp returned the same result')
		secondResult = tempFolderManager.setDefaultFolder(secondTarget)
		self.assertTrue(os.path.samefile(secondTarget, secondResult), 'When setDefaultFolder was given a target location of "%s" it returned: %s' % (firstTarget, firstResult))
		generateSomeContent(secondTarget)
		
		# clean up everything
		tempFolderManager.cleanupForExit()
		
		# verify that the targets went away
		self.assertFalse(os.path.exists(firstTarget) or os.path.exists(secondTarget), 'Both folders were not deleted when cleanupForExit was called: %s %s' % (firstTarget, secondTarget))
	
	def test_getManagedPathForPath(self):
		
		enclosingFolder = tempFolderManager.getDefaultFolder()
		testItem = os.path.join(enclosingFolder, "any_string")
		result = tempFolderManager.getManagedPathForPath(testItem)
		
		self.assertEqual(enclosingFolder, result, 'getManagedPathForPath did not return the proper enclosing path (%s) when asked for the enclosing path of: "%s" but rather: %s' % (enclosingFolder, testItem, result))
	
	def test_getManagedPathForPath_negative(self):
		'''Test getManagedPathForPath with bad results'''
		
		# make sure we are setup
		tempFolderManager.getDefaultFolder()
		
		# test bad input
		self.assertRaises(ValueError, tempFolderManager.getManagedPathForPath, [])
		self.assertRaises(ValueError, tempFolderManager.getManagedPathForPath, None)
		
		# test paths that should never be there
		testPath = '/this-should-not-exist'
		result = tempFolderManager.getManagedPathForPath(testPath)
		self.assertEqual(None, result, 'getManagedPathForPath did not return none when asked for the manged path for %s, but rather returned: %s' % (testPath, result))
	
	def test_mountedDMGtest(self):
		
		managedFolder = tempFolderManager.getDefaultFolder()
		
		# create a read/write dmg
		
		# !!!! WORK HERE !!!!
	
	def test_createAndCleanupItem(self):
		'''Test the creation and deletion of a single item'''
		
		# !!!! WORK HERE !!!!
	
	def test_plainFiles(self):
		'''Test that a random file will be deleted'''
		
		(fileHandle, filePath) = tempfile.mkstemp()
		os.close(fileHandle) # we don't need to write anything to this
		filePath = os.path.realpath(os.path.normpath(filePath))
		
		# add it, and confirm that this is managed
		tempFolderManager.addManagedItem(filePath)
		self.assertTrue(filePath in tempFolderManager.managedItems, 'Adding a file using addManagedItem did not result in it being put in managedItems')
		self.assertTrue(tempFolderManager.getManagedPathForPath(filePath) is not None, 'Adding a file using addManagedItem did not make it managed (according to getManagedPathForPath)')
		
		# wipe this out using cleanupItem
		tempFolderManager.cleanupItem(filePath)
		self.assertFalse(os.path.exists(filePath), 'Removing a file added with addManagedItem with cleanupItem did not get rid of the file')
		
		# repeat the exercise for cleanupForExit
		(fileHandle, filePath) = tempfile.mkstemp()
		os.close(fileHandle) # we don't need to write anything to this
		filePath = os.path.realpath(os.path.normpath(filePath))
		
		# add it, and confirm that this is managed
		tempFolderManager.addManagedItem(filePath)
		self.assertTrue(filePath in tempFolderManager.managedItems, 'Adding a file using addManagedItem did not result in it being put in managedItems')
		self.assertTrue(tempFolderManager.getManagedPathForPath(filePath) is not None, 'Adding a file using addManagedItem did not make it managed (according to getManagedPathForPath)')
		
		# wipe this out using cleanupItem
		tempFolderManager.cleanupForExit()
		self.assertFalse(os.path.exists(filePath), 'Removing a file added with addManagedItem with cleanupForExit did not get rid of the file')
	
	def test_withStatementFunction(self):
		'''Test the use of items with the "with" statement'''
		
		location = None
		with tempFolderManager() as thisTempFolder:
			
			self.assertTrue(isinstance(thisTempFolder, tempFolderManager), 'While using a with statement a tempFolderManager item was not created correctly')
			
			location = thisTempFolder.getPath()
			self.assertTrue(location is not None, 'When using a with statement getPath method returned None')
			self.assertTrue(os.path.isdir(location), 'When using a with statement getPath method returned a path that was not an existing directory')
			self.assertTrue(tempFolderManager.getManagedPathForPath(location) is not None, 'When using a with statement getPath returned a path that was not in a managed item')
			
			# create some contents to make it interesting
			generateSomeContent(location)
		
		# outside the with statement the item should have auto-cleaned iteself
		self.assertFalse(os.path.exists(location), 'After exiting a with statement the item was not properly cleaned up')
		
		# repeat the same exercise with a preset location
		location = tempfile.mkdtemp(dir='/tmp')
		with tempFolderManager(location) as thisTempFolder:
			
			self.assertTrue(isinstance(thisTempFolder, tempFolderManager), 'While using a with statement and a preset location a tempFolderManager item was not created correctly')
			
			returnedLocation = thisTempFolder.getPath()
			self.assertTrue(returnedLocation is not None, 'When using a with statement and a preset location getPath method returned None')
			self.assertTrue(os.path.samefile(returnedLocation, location), 'When using a with statement and a preset location getPath did not return the expected location: "%s" vs. "%s"' % (location, returnedLocation))
			self.assertTrue(os.path.isdir(location), 'When using a with statement and a preset location getPath method returned a path that was not an existing directory')
			self.assertTrue(tempFolderManager.getManagedPathForPath(location) is not None, 'When using a with statement and a preset location getPath returned a path that was not in a managed item')
			
			# create some contents to make it interesting
			generateSomeContent(location)
		
		# outside the with statement the item should have auto-cleaned iteself
		self.assertFalse(os.path.exists(location), 'After exiting a with statement the item was not properly cleaned up')
	
	def test_cleanupForExit(self):
		'''Confirm that cleanupForExit works as expected'''
		
		# create a few items, so we know they are there
		mainTempFolder = tempFolderManager.getDefaultFolder()
		generateSomeContent(mainTempFolder)
		self.assertTrue(len(os.listdir(mainTempFolder)) > 0, 'generateSomeContent failed to generate any test content')
		
		# copy the list of managed paths
		cachedItemPaths = list(tempFolderManager.managedItems)
		
		# call cleanupAtExit
		tempFolderManager.cleanupForExit()
		
		# confirm that everything has been deleted, and the variables cleaned up
		for thisItem in cachedItemPaths:
			self.assertFalse(os.path.exists(thisItem), 'cleanupAtExit left an item un-deleted: ' + str(thisItem))
		
		self.assertEquals(tempFolderManager.managedItems, [], 'cleanupAtExit left the managedItems variable with a value: ' + str(tempFolderManager.managedItems))
		self.assertTrue(tempFolderManager.defaultFolder	is None, 'cleanupAtExit left the defaultFolder variable with a value: ' + str(tempFolderManager.defaultFolder))
	
	def test_getNewTempFolder(self):
		'''Test the getNewTempFolder method'''
		
		# test without any input
		firstFolderPath = tempFolderManager.getNewTempFolder()
		self.assertTrue(firstFolderPath is not None, 'Called with no options getNewTempFolder gave back None')
		self.assertTrue(os.path.isdir(firstFolderPath), 'Called with no options getNewTempFolder returned a string that was not a path to an existing folder: ' + str(firstFolderPath))
		self.assertTrue(tempFolderManager.getManagedPathForPath(firstFolderPath) is not None, 'Called with no options getNewTempFolder returned a path that was not in any managed path (according to getManagedPathForPath): ' + firstFolderPath)
		
		# test with the parent folder option
		secondParentFolder = tempfile.mkdtemp(dir='/tmp')
		secondFolderPath = tempFolderManager.getNewTempFolder(parentFolder=secondParentFolder)
		self.assertTrue(secondFolderPath is not None, 'Called with a parent folder getNewTempFolder gave back None')
		self.assertTrue(os.path.isdir(secondFolderPath), 'Called with a parent folder getNewTempFolder returned a string that was not a path to an existing folder: ' + str(secondFolderPath))
		self.assertTrue(secondFolderPath.startswith(os.path.realpath(os.path.normpath(secondParentFolder))), 'Called with a parent folder (%s) getNewTempFolder returned a path not in the parent folder: %s' % (secondParentFolder, secondFolderPath))
		self.assertTrue(tempFolderManager.getManagedPathForPath(secondFolderPath) is not None, 'Called with a parent folder getNewTempFolder returned a path that was not in any managed path (according to getManagedPathForPath): ' + secondFolderPath)
		
		# test with the prefix option
		prefixOption = "thisIsATest"
		thirdFolderPath = tempFolderManager.getNewTempFolder(prefix=prefixOption)
		self.assertTrue(thirdFolderPath is not None, 'Called with the prefix option (%s) getNewTempFolder gave back None' % prefixOption)
		self.assertTrue(os.path.isdir(thirdFolderPath), 'Called with the prefix option (%s) getNewTempFolder returned a string that was not a path to an existing folder: %s' % (prefixOption, str(thirdFolderPath)))
		self.assertTrue(os.path.basename(thirdFolderPath).startswith(prefixOption), 'Called with the prefix option (%s) getNewTempFolder returned a path not in the parent folder: %s' % (prefixOption, thirdFolderPath))
		self.assertTrue(tempFolderManager.getManagedPathForPath(secondFolderPath) is not None, 'Called with the prefix option (%s) getNewTempFolder returned a path that was not in any managed path (according to getManagedPathForPath): %s' % (prefixOption, thirdFolderPath))
		
		# call cleanupAtExit to clear everything
		tempFolderManager.cleanupForExit()
		
		# verify that the folders dissapeared
		self.assertFalse(os.path.exists(firstFolderPath), 'After being created with getNewTempFolder using no options the folder path was not cleaned properly by cleanupForExit: ' + firstFolderPath)
		self.assertFalse(os.path.exists(secondFolderPath), 'After being created with getNewTempFolder using the parent folder the folder optionthe path was not cleaned properly by cleanupForExit: ' + secondFolderPath)
		self.assertFalse(os.path.exists(thirdFolderPath), 'After being created with getNewTempFolder using the prefix option (%s) the folder path was not cleaned properly by cleanupForExit: %s' % (prefixOption, thirdFolderPath))
		
		# remove the tempdir we made for the parent folder test
		shutil.rmtree(secondParentFolder)
		

class setupTests_negative(unittest.TestCase):
	
	def test_badDefaultFolders(self):
		'''These tests should all fail, and are designed to make sure that we can't wrongly delete things'''
		self.assertRaises(ValueError, tempFolderManager.setDefaultFolder, '/tmp/this-should-not-exist/inner') # parent folder does not exist
		
		# create a folder with contents
		existingFolder = tempfile.mkdtemp(dir='/tmp')
		generateSomeContent(existingFolder, maxFilesInFolders=1, maxSubFolders=0)
		self.assertRaises(ValueError, tempFolderManager.setDefaultFolder, existingFolder) # folder already exists
		shutil.rmtree(existingFolder)

if __name__ == "__main__":
	unittest.main()
