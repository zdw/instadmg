#!/usr/bin/python

import os, unittest, stat

from installerPackage		import installerPackage
from tempFolderManager 		import tempFolderManager


class installerPackageSetupTests(unittest.TestCase):
	
	def test_cacheSetup(self):
		'''Test setting up cache folder'''
		
		cacheFolderPath = tempFolderManager.getNewTempFolder()
		
		# sanity check that it was not already somehow the cache and source folders already
		self.assertNotEqual(cacheFolderPath, installerPackage.cacheFolder, 'The cache folder to be used for testing was already set: ' + str(cacheFolderPath))
		self.assertFalse(cacheFolderPath in installerPackage.sourceFolders, 'The new cache folder was somehow already in the source folder set: ' + str(cacheFolderPath))
		
		# check that adding a folder adds it to the inside 
		installerPackage.setCacheFolder(cacheFolderPath)
		self.assertEqual(cacheFolderPath, installerPackage.cacheFolder, 'Using setCacheFolder did not result in the cache folder being set in the class')
		self.assertEqual(cacheFolderPath, installerPackage.getCacheFolder(), 'Using setCacheFolder did not result in the item the ouput of getCacheFolder: ' + str(installerPackage.getCacheFolder()))
		
		# check that this got added to the sourceFolders as well
		self.assertTrue(cacheFolderPath in installerPackage.sourceFolders, 'When selecting a cacheFolder it should automatically be added to the sourcefolder list, but was not')
		self.assertTrue(cacheFolderPath in installerPackage.getSourceFolders(), 'When selecting a cacheFolder it should automatically be added to the getSourceFolders output, but was not')
		
		# remove the setting, and test to see that it is removed from everywhere
		installerPackage.removeCacheFolder()
		self.assertEqual(installerPackage.cacheFolder, None, 'After calling removeCacheFolder the cache folder variable was still set')
		self.assertRaises(RuntimeWarning, installerPackage.getCacheFolder)
		
		self.assertFalse(cacheFolderPath in installerPackage.sourceFolders, 'After calling removeCacheFolder the cache folder should not be in the sourceFolders list')
		# don't check the getSourceFolders() return, as it could be an error if nothing else is there
		
	def test_singleSourceSetup(self):
		'''Test setting up a single source folder'''
		
		# setup the cache folder so that we can do tests
		cacheFolderPath = tempFolderManager.getNewTempFolder()
		installerPackage.setCacheFolder(cacheFolderPath)
		
		sourceFolderPath = tempFolderManager.getNewTempFolder()
		
		# sanity check that it was not already somehow the source folders already
		self.assertFalse(sourceFolderPath in installerPackage.sourceFolders, 'The new sourceFolder was found in the sourceFodlers variable too soon')
		self.assertNotEqual(sourceFolderPath, installerPackage.cacheFolder, 'The new sourceFolder should not be the selected cache folder')
		
		# check that adding the source folder results in it being actually added
		installerPackage.addSourceFolders(sourceFolderPath)
		self.assertTrue(sourceFolderPath in installerPackage.sourceFolders, 'After being added with addSourceFolders the test source path was not in the sourceFolders vaiable')
		self.assertTrue(sourceFolderPath in installerPackage.getSourceFolders(), 'After being added with addSourceFolders the test source path was not in the getSourceFolders output')
		
		# check that this has not affected the cache folder setting
		self.assertEqual(cacheFolderPath, installerPackage.getCacheFolder(), 'After adding a source folder the cache folder should not change')
		
		# remove the source folder, and check to make sure it is removed
		installerPackage.removeSourceFolders(sourceFolderPath)
		self.assertFalse(sourceFolderPath in installerPackage.sourceFolders, 'After calling removeSourceFolder the source folder was still in the sourceFolders list')
		
		# cleanup
		installerPackage.removeCacheFolder()
		installerPackage.removeSourceFolders(cacheFolderPath)
		tempFolderManager.cleanupItem(cacheFolderPath)
		tempFolderManager.cleanupItem(sourceFolderPath)
	
	def test_multipleSourceSetup(self):
		'''Test setting up multiple source folders'''
		
		# setup the cache folder so that we can do tests
		cacheFolderPath = tempFolderManager.getNewTempFolder()
		installerPackage.setCacheFolder(cacheFolderPath)
		
		firstSourceFolderPath	= tempFolderManager.getNewTempFolder()
		secondSourceFolderPath	= tempFolderManager.getNewTempFolder()
		thirdSourceFolderPath	= tempFolderManager.getNewTempFolder()
		
		# add the first two items and confirm they are there
		installerPackage.addSourceFolders([firstSourceFolderPath, secondSourceFolderPath])
		
		self.assertTrue(firstSourceFolderPath in installerPackage.sourceFolders, 'After being added with addSourceFolders the first test source path was not in the sourceFolders vaiable')
		self.assertTrue(firstSourceFolderPath in installerPackage.getSourceFolders(), 'After being added with addSourceFolders the first test source path was not in the getSourceFolders output')
		
		self.assertTrue(secondSourceFolderPath in installerPackage.sourceFolders, 'After being added with addSourceFolders the second test source path was not in the sourceFolders vaiable')
		self.assertTrue(secondSourceFolderPath in installerPackage.getSourceFolders(), 'After being added with addSourceFolders the second test source path was not in the getSourceFolders output')
		
		# add the third item, verifying that all three are there
		installerPackage.addSourceFolders(thirdSourceFolderPath)
		
		self.assertTrue(firstSourceFolderPath in installerPackage.sourceFolders, 'After adding the third source item with addSourceFolders the first test source path was not in the sourceFolders vaiable')
		self.assertTrue(firstSourceFolderPath in installerPackage.getSourceFolders(), 'After adding the third source item with addSourceFolders the first test source path was not in the getSourceFolders output')
		
		self.assertTrue(secondSourceFolderPath in installerPackage.sourceFolders, 'After adding the third source item with addSourceFolders the second test source path was not in the sourceFolders vaiable')
		self.assertTrue(secondSourceFolderPath in installerPackage.getSourceFolders(), 'After adding the third source item with addSourceFolders the second test source path was not in the getSourceFolders output')
		
		self.assertTrue(thirdSourceFolderPath in installerPackage.sourceFolders, 'After adding the third source item with addSourceFolders the third test source path was not in the sourceFolders vaiable')
		self.assertTrue(thirdSourceFolderPath in installerPackage.getSourceFolders(), 'After adding the third source item with addSourceFolders the third test source path was not in the getSourceFolders output')
		
		# remove the second item, and verify that it is removed, and the other two still there
		installerPackage.removeSourceFolders(secondSourceFolderPath)
		
		self.assertFalse(secondSourceFolderPath in installerPackage.sourceFolders, 'After removing the second source item with removeSourceFolders the second test source path was still in the sourceFolders vaiable')
		self.assertFalse(secondSourceFolderPath in installerPackage.getSourceFolders(), 'After removing the second source item with removeSourceFolders the second test source path was still in the getSourceFolders output')
				
		self.assertTrue(firstSourceFolderPath in installerPackage.sourceFolders, 'After removing the second source item with removeSourceFolders the first test source path was not in the sourceFolders vaiable')
		self.assertTrue(firstSourceFolderPath in installerPackage.getSourceFolders(), 'After removing the second source item with removeSourceFolders the first test source path was not in the getSourceFolders output')
		
		self.assertTrue(thirdSourceFolderPath in installerPackage.sourceFolders, 'After removing the second source item with removeSourceFolders the third test source path was not in the sourceFolders vaiable')
		self.assertTrue(thirdSourceFolderPath in installerPackage.getSourceFolders(), 'After removing the second source item with removeSourceFolders the third test source path was not in the getSourceFolders output')
		
		# remove the two remaining items and verify that they are gone
		installerPackage.removeSourceFolders([firstSourceFolderPath, thirdSourceFolderPath])
		
		self.assertFalse(firstSourceFolderPath in installerPackage.sourceFolders, 'After removing the first and third source item with removeSourceFolders the first test source path was still in the sourceFolders vaiable')
		self.assertFalse(secondSourceFolderPath in installerPackage.sourceFolders, 'After removing the first and third source item with removeSourceFolders the second test source path was still in the sourceFolders vaiable')
		self.assertFalse(thirdSourceFolderPath in installerPackage.sourceFolders, 'After removing the first and third source item with removeSourceFolders the third test source path was still in the sourceFolders vaiable')
		
		# cleanup
		installerPackage.removeCacheFolder()
		installerPackage.removeSourceFolders(cacheFolderPath)
		tempFolderManager.cleanupItem(cacheFolderPath)
		
		tempFolderManager.cleanupItem(firstSourceFolderPath)
		tempFolderManager.cleanupItem(secondSourceFolderPath)
		tempFolderManager.cleanupItem(thirdSourceFolderPath)

class installerPackageTestsSetup(unittest.TestCase):
	'''Common setup and tearDown routines'''

	cacheFolderPath			= None
	firstSourceFolderPath	= None
	secondSourceFolderPath	= None
	
	def setUp(self):
		'''Create folders for the cache folder and 2 source folders'''
		self.cacheFolderPath		= tempFolderManager.getNewTempFolder()
		installerPackage.setCacheFolder(self.cacheFolderPath)
		
		self.firstSourceFolderPath	= tempFolderManager.getNewTempFolder()
		self.secondSourceFolderPath	= tempFolderManager.getNewTempFolder()
		installerPackage.addSourceFolders([self.firstSourceFolderPath, self.secondSourceFolderPath])
		
		# ToDo: think about making sure we have an absolutely clean setup
	
	def tearDown(self):
		'''Clean up the items we created for tests'''
		
		# cache folder
		if installerPackage.cacheFolder == self.cacheFolderPath:
			installerPackage.removeCacheFolder()
		tempFolderManager.cleanupItem(self.cacheFolderPath)
		
		# source folders
		if self.firstSourceFolderPath in installerPackage.sourceFolders:
			installerPackage.removeSourceFolders(self.firstSourceFolderPath)
		tempFolderManager.cleanupItem(self.firstSourceFolderPath)
		if self.secondSourceFolderPath in installerPackage.sourceFolders:
			installerPackage.removeSourceFolders(self.secondSourceFolderPath)
		tempFolderManager.cleanupItem(self.secondSourceFolderPath)

class installerPackageTests(installerPackageTestsSetup):
	'''Test cases for installerPackage once it has been set up'''
	
	def cacheTestMethod(self, method):
		'''Test findItem finding simple files in the cache'''
		
		# file with a known name and checksum, with the checksum in the path
		checksumFilePath = os.path.join(self.firstSourceFolderPath, 'aFile sha1-f475597b627a4d580ec1619a94c7afb9cc75abe4.txt')
		testFile = open(checksumFilePath, 'w')
		testFile.write("a" * 400) # sha1 checksum: f475597b627a4d580ec1619a94c7afb9cc75abe4
		testFile.close()
		
		# file with a known name and checksum, with the checksum in the path, inside a subfolder
		checksumInSubfolderFilePath = os.path.join(self.firstSourceFolderPath, 'subfolder', 'bFile sha1-8bc1e4c5d467c10555dae3c4ea04471b856b23bc.txt')
		os.mkdir(os.path.join(self.firstSourceFolderPath, 'subfolder'))
		testFile = open(checksumInSubfolderFilePath, 'w')
		testFile.write("b" * 150) # sha1 checksum: 8bc1e4c5d467c10555dae3c4ea04471b856b23bc
		testFile.close()
		
		# file with a known name and checksum, without the checksum in the path
		nameFilePath = os.path.join(self.firstSourceFolderPath, 'cFile.txt')
		testFile = open(nameFilePath, 'w')
		testFile.write("c" * 300) # sha1 checksum: bc5b916598902018a023717425314bee88ff7fe9
		testFile.close()
		
		# file with a known name and checksum in a subfolder, without the checksum in the path
		nameInSubfolderFilePath = os.path.join(self.firstSourceFolderPath, 'subfolder', 'dFile.txt')
		testFile = open(nameInSubfolderFilePath, 'w')
		testFile.write("d" * 180) # sha1 checksum: b07eaa471ef7af455e1079a59135b1ebac44a72e
		testFile.close()
		
		# file with a known name in the second folder
		nameInSecondSourceFolderFilePath = os.path.join(self.secondSourceFolderPath, 'eFile.txt')
		testFile = open(nameInSecondSourceFolderFilePath, 'w')
		testFile.write("E" * 40) # sha1 checksum: 981ee57582ef1b95fb2f87982280a6dd01f46cc8
		testFile.close()
		
		# create two files, with the same name but different checksums, one in a subfolder
		outerDifferentChecksumFilePath = os.path.join(self.secondSourceFolderPath, 'fFile.txt')
		testFile = open(outerDifferentChecksumFilePath, 'w')
		testFile.write("f" * 80) # sha1 checksum: c8280ce5bfab50ffac50bbca5e22540335708ad9
		testFile.close()
		
		os.mkdir(os.path.join(self.secondSourceFolderPath, 'fFileFolder'))
		innerDifferentChecksumFilePath = os.path.join(self.secondSourceFolderPath, 'fFileFolder', 'fFile.txt')
		testFile = open(innerDifferentChecksumFilePath, 'w')
		testFile.write("f" * 40) # sha1 checksum: e0bbc5c28208d8909a27a5890216e24da6eb8cd3
		testFile.close()
		
		# two files with the same contents and name, but one inside a folder, and one at the root
		outerSameChecksumFilePath = os.path.join(self.secondSourceFolderPath, 'gFile.txt')
		testFile = open(outerSameChecksumFilePath, 'w')
		testFile.write("g" * 177) # sha1 checksum: 9315056a35b92557f3180c7c53d33c80dca7095e
		testFile.close()
		
		os.mkdir(os.path.join(self.secondSourceFolderPath, 'gFileFolder'))
		innerSameChecksumFilePath = os.path.join(self.secondSourceFolderPath, 'gFileFolder', 'gFile.txt')
		testFile = open(innerSameChecksumFilePath, 'w')
		testFile.write("g" * 177) # sha1 checksum: 9315056a35b92557f3180c7c53d33c80dca7095e
		testFile.close()
		
		# ToDo: absolute path
		# ToDo: absolute path crossing a symlink
		
		
		
		
		# find file by checksum
		resultPath = method('aFile.txt', 'sha1', 'f475597b627a4d580ec1619a94c7afb9cc75abe4', progressReporter=None)
		self.assertEqual(checksumFilePath, resultPath, 'findItem could not find the aFile by checksum, should have been "%s" but was: %s' % (checksumFilePath, resultPath))
		
		# find a file in a folder by checksum
		resultPath = method('bFile.txt', 'sha1', '8bc1e4c5d467c10555dae3c4ea04471b856b23bc', progressReporter=None)
		self.assertEqual(checksumInSubfolderFilePath, resultPath, 'findItem could not find the bFile inside a subfolder by checksum, should have been "%s" but was: %s' % (checksumInSubfolderFilePath, resultPath))
		
		# find a file by the name, indluding extension
		resultPath = method('cFile.txt', 'sha1', 'bc5b916598902018a023717425314bee88ff7fe9', progressReporter=None)
		self.assertEqual(nameFilePath, resultPath, 'findItem could not find the cFile by the name, indluding extension, should have been "%s" but was: %s' % (nameFilePath, resultPath))
		
		# find a file by the name, minus the extension
		resultPath = method('cFile', 'sha1', 'bc5b916598902018a023717425314bee88ff7fe9', progressReporter=None)
		self.assertEqual(nameFilePath, resultPath, 'findItem could not find the cFile by the name, minus the extension, should have been "%s" but was: %s' % (nameFilePath, resultPath))
		
		# find a file by the name, with a bad extension
		resultPath = method('cFile.bad', 'sha1', 'bc5b916598902018a023717425314bee88ff7fe9', progressReporter=None)
		self.assertEqual(nameFilePath, resultPath, 'findItem could not find the cFile by the name, with a bad extension, should have been "%s" but was: %s' % (nameFilePath, resultPath))
		
		# find a file in a subfolder by the name, indluding extension
		resultPath = method('dFile.txt', 'sha1', 'b07eaa471ef7af455e1079a59135b1ebac44a72e', progressReporter=None)
		self.assertEqual(nameInSubfolderFilePath, resultPath, 'findItem could not find the dFile in a subfolder by the name, indluding extension, should have been "%s" but was: %s' % (nameFilePath, resultPath))
		
		# find a file in a subfolder by the name, minus the extension
		resultPath = method('dFile', 'sha1', 'b07eaa471ef7af455e1079a59135b1ebac44a72e', progressReporter=None)
		self.assertEqual(nameInSubfolderFilePath, resultPath, 'findItem could not find the dFile in a subfolder by the name, minus the extension, should have been "%s" but was: %s' % (nameFilePath, resultPath))
		
		# find a file in the second source folder by the name, minus the extension
		resultPath = method('eFile', 'sha1', '981ee57582ef1b95fb2f87982280a6dd01f46cc8', progressReporter=None)
		self.assertEqual(nameInSecondSourceFolderFilePath, resultPath, 'findItem could not find the eFile in the second source folder by name without checksume, should have been "%s" but was: %s' % (nameInSecondSourceFolderFilePath, resultPath))
		
		# find the inner source file when there is one in the root with the same name but a differnt checksum
		resultPath = method('fFile', 'sha1', 'e0bbc5c28208d8909a27a5890216e24da6eb8cd3', progressReporter=None)
		self.assertEqual(innerDifferentChecksumFilePath, resultPath, 'findItem could not find the inner fFile by checksum, should have been "%s" but was: %s' % (innerDifferentChecksumFilePath, resultPath))
		# find the outer source
		resultPath = method('fFile', 'sha1', 'c8280ce5bfab50ffac50bbca5e22540335708ad9', progressReporter=None)
		self.assertEqual(outerDifferentChecksumFilePath, resultPath, 'findItem could not find the outer fFile by checksum, should have been "%s" but was: %s' % (outerDifferentChecksumFilePath, resultPath))
		
		# find the inner source file by looking for it by a relative path
		resultPath = method('gFileFolder/gFile.txt', 'sha1', '9315056a35b92557f3180c7c53d33c80dca7095e', progressReporter=None)
		self.assertEqual(innerSameChecksumFilePath, resultPath, 'findItem could not find the inner gFile by relative path, should have been "%s" but was: %s' % (innerSameChecksumFilePath, resultPath))
		# make sure that the outer file is found when not giving the relative path
		resultPath = method('gFile.txt', 'sha1', '9315056a35b92557f3180c7c53d33c80dca7095e', progressReporter=None)
		self.assertEqual(outerSameChecksumFilePath, resultPath, 'findItem could not find the outer gFile by name/checksum, should have been "%s" but was: %s' % (outerSameChecksumFilePath, resultPath))
		
	def test_findItemInCaches(self):
		'''Test out the _findItemInCaches method'''
		self.cacheTestMethod(installerPackage._findItemInCaches)

	def test_findItem(self):
		'''Test out both local files and downloads with the findItem method'''
		
		self.cacheTestMethod(installerPackage.findItem)
		
		# download a file
		resultPath = installerPackage.findItem('http://images.apple.com/support/iknow/images/downloads_software_update.png', 'sha1', '4d200d3fc229d929ea9ed64a9b5e06c5be733b38', progressReporter=None)
		self.assertEqual(os.path.join(installerPackage.getCacheFolder(), 'downloads_software_update sha1-4d200d3fc229d929ea9ed64a9b5e06c5be733b38.png'), resultPath, "Downloading a file from Apple's site returned: " + str(resultPath))
			
	# ToDo: test downloads
	# ToDo: test optional folders
	
class installerPackageTest_negative(installerPackageTestsSetup):
	
	def test_cacheSetup_negative(self):
		'''Test that the cacheSetup method errors out when it is supposed to'''
		
		# absolutely bad input
		self.assertRaises(ValueError, installerPackage.setCacheFolder, None)
		self.assertRaises(ValueError, installerPackage.setCacheFolder, [])
		self.assertRaises(ValueError, installerPackage.setCacheFolder, '/bin/ls') # Not a folder
		
		# a folder that is not writeable
		unwriteableFolder = tempFolderManager.getNewTempFolder()
		os.chmod(unwriteableFolder, 0)
		self.assertRaises(ValueError, installerPackage.setCacheFolder, unwriteableFolder)
	
	def test_findItem_negaitve(self):
		'''Test findItem with bad values'''
		# ToDo: 
	
	# ToDo: test that 
	

