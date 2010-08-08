#!/usr/bin/python

import os, unittest, stat

from installerPackage		import installerPackage
from tempFolderManager 		import tempFolderManager


class installerPackageTest(unittest.TestCase):
	
	def test_cacheSetup(self):
		'''Test setting up cache folder'''
		
		cacheFolder = tempFolderManager.getNewTempFolder()
		
		# sanity check that it was not already somehow the cache folder
		self.assertNotEqual(cacheFolder, installerPackage.cacheFolder, 'The cache folder to be used for testing was already set: ' + str(cacheFolder))
		
		# check that adding a folder adds it to the inside 
		installerPackage.setCacheFolder(cacheFolder)
		self.assertEqual(cacheFolder, installerPackage.cacheFolder, 'Using setCacheFolder did not result in the cache folder being set in the class')
		self.assertEqual(cacheFolder, installerPackage.getCacheFolder(), 'Using setCacheFolder did not result in the item the ouput of getCacheFolder: ' + str(installerPackage.getCacheFolder()))
		
	def test_sourceSetup(self):
		'''Test setting the source folders'''
	

class installerPackageTest_negative(unittest.TestCase):
	
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
		
