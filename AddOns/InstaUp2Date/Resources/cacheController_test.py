#!/usr/bin/python

import os, unittest

from tempFolderManager 		import tempFolderManager
from commonExceptions		import FileNotFoundException

from cacheController		import cacheController

class cacheControllerTest(unittest.TestCase):
	'''Common setup and tearDown routines'''

	cacheFolderPath			= None
	firstSourceFolderPath	= None
	secondSourceFolderPath	= None
	
	testMaterials			= None
	
	def setUp(self):
		'''Create folders for the cache folder and 2 source folders'''
		self.cacheFolderPath		= tempFolderManager.getNewTempFolder()
		
		cacheController.setCacheFolder(self.cacheFolderPath)
		
		self.firstSourceFolderPath	= tempFolderManager.getNewTempFolder()
		self.secondSourceFolderPath	= tempFolderManager.getNewTempFolder()
		cacheController.addSourceFolders([self.firstSourceFolderPath, self.secondSourceFolderPath])
		
		# ToDo: think about making sure we have an absolutely clean setup
		
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
		
		self.testMaterials = [
			# this should be in the format:
			# filename	- 	checksumType	-	checksumValue	-	desiredOutput	-	errorMessage
			
			# find file by checksum
			{'fileName':'aFile.txt', 'checksumType':'sha1', 'checksumValue':'f475597b627a4d580ec1619a94c7afb9cc75abe4', 'filePath':checksumFilePath, 'errorMessage':'findItem could not find the aFile by checksum'},
			
			# find a file in a folder by checksum
			{'fileName':'bFile.txt', 'checksumType':'sha1', 'checksumValue':'8bc1e4c5d467c10555dae3c4ea04471b856b23bc', 'filePath':checksumInSubfolderFilePath, 'errorMessage':'findItem could not find the bFile inside a subfolder by checksum'},
			
			# find a file by the name, indluding extension
			{'fileName':'cFile.txt', 'checksumType':'sha1', 'checksumValue':'bc5b916598902018a023717425314bee88ff7fe9', 'filePath':nameFilePath, 'errorMessage':'findItem could not find the cFile by the name, indluding extension'},
			
			# find a file by the name, minus the extension
			{'fileName':'cFile', 'checksumType':'sha1', 'checksumValue':'bc5b916598902018a023717425314bee88ff7fe9', 'filePath':nameFilePath, 'errorMessage':'findItem could not find the cFile by the name, minus the extension'},
			
			# find a file by the name, with a bad extension
			{'fileName':'cFile.bad', 'checksumType':'sha1', 'checksumValue':'bc5b916598902018a023717425314bee88ff7fe9', 'filePath':nameFilePath, 'errorMessage':'findItem could not find the cFile by the name, with a bad extension'},
			
			# find a file in a subfolder by the name, indluding extension
			{'fileName':'dFile.txt', 'checksumType':'sha1', 'checksumValue':'b07eaa471ef7af455e1079a59135b1ebac44a72e', 'filePath':nameInSubfolderFilePath, 'errorMessage':'findItem could not find the dFile in a subfolder by the name, indluding extension'},
			
			# find a file in a subfolder by the name, minus the extension
			{'fileName':'dFile', 'checksumType':'sha1', 'checksumValue':'b07eaa471ef7af455e1079a59135b1ebac44a72e', 'filePath':nameInSubfolderFilePath, 'errorMessage':'findItem could not find the dFile in a subfolder by the name, minus the extension'},
			
			# find a file in the second source folder by the name, minus the extension
			{'fileName':'eFile', 'checksumType':'sha1', 'checksumValue':'981ee57582ef1b95fb2f87982280a6dd01f46cc8', 'filePath':nameInSecondSourceFolderFilePath, 'errorMessage':'findItem could not find the eFile in the second source folder by name without checksume'},
			
			# find the inner source file when there is one in the root with the same name but a differnt checksum
			{'fileName':'fFile', 'checksumType':'sha1', 'checksumValue':'e0bbc5c28208d8909a27a5890216e24da6eb8cd3', 'filePath':innerDifferentChecksumFilePath, 'errorMessage':'findItem could not find the inner fFile by checksum'},
			
			# find the outer source
			{'fileName':'fFile', 'checksumType':'sha1', 'checksumValue':'c8280ce5bfab50ffac50bbca5e22540335708ad9', 'filePath':outerDifferentChecksumFilePath, 'errorMessage':'findItem could not find the outer fFile by checksum'},
			
			# find the inner source file by looking for it by a relative path
			{'fileName':'gFileFolder/gFile.txt', 'checksumType':'sha1', 'checksumValue':'9315056a35b92557f3180c7c53d33c80dca7095e', 'filePath':innerSameChecksumFilePath, 'errorMessage':'findItem could not find the inner gFile by relative path'},
			
			# make sure that the outer file is found when not giving the relative path
			{'fileName':'gFile.txt', 'checksumType':'sha1', 'checksumValue':'9315056a35b92557f3180c7c53d33c80dca7095e', 'filePath':outerSameChecksumFilePath, 'errorMessage':'findItem could not find the outer gFile by name/checksum'},
		]

	def tearDown(self):
		'''Clean up the items we created for tests'''
		
		# cache folder
		if cacheController.writeableCacheFolder == self.cacheFolderPath:
			cacheController.removeCacheFolder()
		tempFolderManager.cleanupItem(self.cacheFolderPath)
		
		# source folders
		if self.firstSourceFolderPath in cacheController.sourceFolders:
			cacheController.removeSourceFolders(self.firstSourceFolderPath)
		tempFolderManager.cleanupItem(self.firstSourceFolderPath)
		if self.secondSourceFolderPath in cacheController.sourceFolders:
			cacheController.removeSourceFolders(self.secondSourceFolderPath)
		tempFolderManager.cleanupItem(self.secondSourceFolderPath)
		
		# verified files
		cacheController.verifiedFiles = {}
		
		self.cacheFolderPath = None
		self.firstSourceFolderPath = None
		self.secondSourceFolderPath = None
		
		self.testMaterials = None
		
		tempFolderManager.cleanupForExit()

class cacheControllerTests(cacheControllerTest):
	'''Test cases for cacheController once it has been set up'''
	
	def test_findItemInCaches(self):
		'''Test out the findItemInCaches method'''
		
		for thisTest in self.testMaterials:
			resultPath, waste = cacheController.findItemInCaches(thisTest['fileName'], thisTest['checksumType'], thisTest['checksumValue'], progressReporter=None)
			thisTest['resultPath'] = resultPath
			self.assertEqual(thisTest['filePath'], resultPath, thisTest['errorMessage'] + ', should have been "%(filePath)s" but was: %(resultPath)s' % thisTest)
	
	def test_findItem(self):
		'''Test out both local files and downloads with the findItem method'''
		
		# perform all of the the local file tests
		for thisTest in self.testMaterials:
			
			result = None
			try:
				result = cacheController.findItem(nameOrLocation=thisTest['fileName'], checksumType=thisTest['checksumType'], checksumValue=thisTest['checksumValue'], displayName=None, additionalSourceFolders=None, progressReporter=None)
			except FileNotFoundException, error:
				self.fail(thisTest['errorMessage'] + ', was unable to find a package - ' + str(error))
			
			self.assertEqual(thisTest['filePath'], result, thisTest['errorMessage'] + ', should have been "%s" but was: %s' % (thisTest['filePath'], result))
		
		# download a file
		
		try:
			result = cacheController.findItem(nameOrLocation='http://images.apple.com/support/iknow/images/downloads_software_update.png', checksumType='sha1', checksumValue='4d200d3fc229d929ea9ed64a9b5e06c5be733b38', displayName=None, progressReporter=None)
			expectedResult = os.path.join(cacheController.getCacheFolder(), 'downloads_software_update sha1-4d200d3fc229d929ea9ed64a9b5e06c5be733b38.png')
			self.assertEqual(expectedResult, result, 'Downloading a file from Apple\'s site returned: "%s" rather than "%s"' % (str(result), expectedResult))
		except FileNotFoundException, error:
			self.fail(thisTest['errorMessage'] + ', was unable to find a package - ' + str(error))
		
		#resultPath = cacheController.findItem('http://images.apple.com/support/iknow/images/downloads_software_update.png', 'sha1', '4d200d3fc229d929ea9ed64a9b5e06c5be733b38', progressReporter=None)
		#self.assertEqual(os.path.join(cacheController.getCacheFolder(), 'downloads_software_update sha1:4d200d3fc229d929ea9ed64a9b5e06c5be733b38.png'), resultPath, "Downloading a file from Apple's site returned: " + str(resultPath))
			
	# ToDo: test downloads
	# ToDo: test optional folders
	
class cacheControllerTest_negative(cacheControllerTest):
	
	def test_cacheSetup_negative(self):
		'''Test that the cacheSetup method errors out when it is supposed to'''
		
		# absolutely bad input
		self.assertRaises(ValueError, cacheController.setCacheFolder, None)
		self.assertRaises(ValueError, cacheController.setCacheFolder, [])
		self.assertRaises(ValueError, cacheController.setCacheFolder, '/bin/ls') # Not a folder
		
		if os.getuid() != 0: # this test is meaningless for root
		
			# a folder that is not writeable
			unwriteableFolder = tempFolderManager.getNewTempFolder()
			os.chmod(unwriteableFolder, 0)
			self.assertRaises(ValueError, cacheController.setCacheFolder, unwriteableFolder)
	
	def test_findItem_negaitve(self):
		'''Test findItem with bad values'''
		# ToDo: 

class cacheControllerSetupTests(unittest.TestCase):
	
	def test_cacheSetup(self):
		'''Test setting up cache folder'''
		
		cacheFolderPath = tempFolderManager.getNewTempFolder()
		
		# sanity check that it was not already somehow the cache and source folders already
		self.assertNotEqual(cacheFolderPath, cacheController.writeableCacheFolder, 'The cache folder to be used for testing was already set: ' + str(cacheFolderPath))
		self.assertFalse(cacheFolderPath in cacheController.sourceFolders, 'The new cache folder was somehow already in the source folder set: ' + str(cacheFolderPath))
		
		# check that adding a folder adds it to the inside 
		cacheController.setCacheFolder(cacheFolderPath)
		self.assertEqual(cacheFolderPath, cacheController.writeableCacheFolder, 'Using setCacheFolder did not result in the cache folder being set in the class')
		self.assertEqual(cacheFolderPath, cacheController.getCacheFolder(), 'Using setCacheFolder did not result in the item the ouput of getCacheFolder: ' + str(cacheController.getCacheFolder()))
		
		# check that this got added to the sourceFolders as well
		self.assertTrue(cacheFolderPath in cacheController.sourceFolders, 'When selecting a cacheFolder it should automatically be added to the sourcefolder list, but was not')
		self.assertTrue(cacheFolderPath in cacheController.getSourceFolders(), 'When selecting a cacheFolder it should automatically be added to the getSourceFolders output, but was not')
		
		# remove the setting, and test to see that it is removed from everywhere
		cacheController.removeCacheFolder()
		self.assertEqual(cacheController.writeableCacheFolder, None, 'After calling removeCacheFolder the cache folder variable was still set')
		self.assertRaises(RuntimeWarning, cacheController.getCacheFolder)
		
		self.assertFalse(cacheFolderPath in cacheController.sourceFolders, 'After calling removeCacheFolder the cache folder should not be in the sourceFolders list')
		# don't check the getSourceFolders() return, as it could be an error if nothing else is there
		
	def test_singleSourceSetup(self):
		'''Test setting up a single source folder'''
		
		# setup the cache folder so that we can do tests
		cacheFolderPath = tempFolderManager.getNewTempFolder()
		cacheController.setCacheFolder(cacheFolderPath)
		
		sourceFolderPath = tempFolderManager.getNewTempFolder()
		
		# sanity check that it was not already somehow the source folders already
		self.assertFalse(sourceFolderPath in cacheController.sourceFolders, 'The new sourceFolder was found in the sourceFodlers variable too soon')
		self.assertNotEqual(sourceFolderPath, cacheController.writeableCacheFolder, 'The new sourceFolder should not be the selected cache folder')
		
		# check that adding the source folder results in it being actually added
		cacheController.addSourceFolders(sourceFolderPath)
		self.assertTrue(sourceFolderPath in cacheController.sourceFolders, 'After being added with addSourceFolders the test source path was not in the sourceFolders vaiable')
		self.assertTrue(sourceFolderPath in cacheController.getSourceFolders(), 'After being added with addSourceFolders the test source path was not in the getSourceFolders output')
		
		# check that this has not affected the cache folder setting
		self.assertEqual(cacheFolderPath, cacheController.getCacheFolder(), 'After adding a source folder the cache folder should not change')
		
		# remove the source folder, and check to make sure it is removed
		cacheController.removeSourceFolders(sourceFolderPath)
		self.assertFalse(sourceFolderPath in cacheController.sourceFolders, 'After calling removeSourceFolder the source folder was still in the sourceFolders list')
		
		# cleanup
		cacheController.removeCacheFolder()
		cacheController.removeSourceFolders(cacheFolderPath)
		tempFolderManager.cleanupItem(cacheFolderPath)
		tempFolderManager.cleanupItem(sourceFolderPath)
	
	def test_multipleSourceSetup(self):
		'''Test setting up multiple source folders'''
		
		# setup the cache folder so that we can do tests
		cacheFolderPath = tempFolderManager.getNewTempFolder()
		cacheController.setCacheFolder(cacheFolderPath)
		
		firstSourceFolderPath	= tempFolderManager.getNewTempFolder()
		secondSourceFolderPath	= tempFolderManager.getNewTempFolder()
		thirdSourceFolderPath	= tempFolderManager.getNewTempFolder()
		
		# add the first two items and confirm they are there
		cacheController.addSourceFolders([firstSourceFolderPath, secondSourceFolderPath])
		
		self.assertTrue(firstSourceFolderPath in cacheController.sourceFolders, 'After being added with addSourceFolders the first test source path was not in the sourceFolders vaiable')
		self.assertTrue(firstSourceFolderPath in cacheController.getSourceFolders(), 'After being added with addSourceFolders the first test source path was not in the getSourceFolders output')
		
		self.assertTrue(secondSourceFolderPath in cacheController.sourceFolders, 'After being added with addSourceFolders the second test source path was not in the sourceFolders vaiable')
		self.assertTrue(secondSourceFolderPath in cacheController.getSourceFolders(), 'After being added with addSourceFolders the second test source path was not in the getSourceFolders output')
		
		# add the third item, verifying that all three are there
		cacheController.addSourceFolders(thirdSourceFolderPath)
		
		self.assertTrue(firstSourceFolderPath in cacheController.sourceFolders, 'After adding the third source item with addSourceFolders the first test source path was not in the sourceFolders vaiable')
		self.assertTrue(firstSourceFolderPath in cacheController.getSourceFolders(), 'After adding the third source item with addSourceFolders the first test source path was not in the getSourceFolders output')
		
		self.assertTrue(secondSourceFolderPath in cacheController.sourceFolders, 'After adding the third source item with addSourceFolders the second test source path was not in the sourceFolders vaiable')
		self.assertTrue(secondSourceFolderPath in cacheController.getSourceFolders(), 'After adding the third source item with addSourceFolders the second test source path was not in the getSourceFolders output')
		
		self.assertTrue(thirdSourceFolderPath in cacheController.sourceFolders, 'After adding the third source item with addSourceFolders the third test source path was not in the sourceFolders vaiable')
		self.assertTrue(thirdSourceFolderPath in cacheController.getSourceFolders(), 'After adding the third source item with addSourceFolders the third test source path was not in the getSourceFolders output')
		
		# remove the second item, and verify that it is removed, and the other two still there
		cacheController.removeSourceFolders(secondSourceFolderPath)
		
		self.assertFalse(secondSourceFolderPath in cacheController.sourceFolders, 'After removing the second source item with removeSourceFolders the second test source path was still in the sourceFolders vaiable')
		self.assertFalse(secondSourceFolderPath in cacheController.getSourceFolders(), 'After removing the second source item with removeSourceFolders the second test source path was still in the getSourceFolders output')
				
		self.assertTrue(firstSourceFolderPath in cacheController.sourceFolders, 'After removing the second source item with removeSourceFolders the first test source path was not in the sourceFolders vaiable')
		self.assertTrue(firstSourceFolderPath in cacheController.getSourceFolders(), 'After removing the second source item with removeSourceFolders the first test source path was not in the getSourceFolders output')
		
		self.assertTrue(thirdSourceFolderPath in cacheController.sourceFolders, 'After removing the second source item with removeSourceFolders the third test source path was not in the sourceFolders vaiable')
		self.assertTrue(thirdSourceFolderPath in cacheController.getSourceFolders(), 'After removing the second source item with removeSourceFolders the third test source path was not in the getSourceFolders output')
		
		# remove the two remaining items and verify that they are gone
		cacheController.removeSourceFolders([firstSourceFolderPath, thirdSourceFolderPath])
		
		self.assertFalse(firstSourceFolderPath in cacheController.sourceFolders, 'After removing the first and third source item with removeSourceFolders the first test source path was still in the sourceFolders vaiable')
		self.assertFalse(secondSourceFolderPath in cacheController.sourceFolders, 'After removing the first and third source item with removeSourceFolders the second test source path was still in the sourceFolders vaiable')
		self.assertFalse(thirdSourceFolderPath in cacheController.sourceFolders, 'After removing the first and third source item with removeSourceFolders the third test source path was still in the sourceFolders vaiable')
		
		# cleanup
		cacheController.removeCacheFolder()
		cacheController.removeSourceFolders(cacheFolderPath)
		tempFolderManager.cleanupItem(cacheFolderPath)
		
		tempFolderManager.cleanupItem(firstSourceFolderPath)
		tempFolderManager.cleanupItem(secondSourceFolderPath)
		tempFolderManager.cleanupItem(thirdSourceFolderPath)

	

