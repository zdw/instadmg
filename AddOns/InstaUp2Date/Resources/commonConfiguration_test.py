#!/usr/bin/python

import os, unittest

import commonConfiguration

class commonConfiguration_test(unittest.TestCase):
	
	def test_filesExist(self):
		
		# pathToInstaDMG
		self.assertTrue(os.path.exists(commonConfiguration.pathToInstaDMG), 'Nothing exists at the path to InstaDMG: ' + commonConfiguration.pathToInstaDMG)
		self.assertTrue(os.path.isfile(commonConfiguration.pathToInstaDMG), 'InstaDMG is not a file: ' + commonConfiguration.pathToInstaDMG)
		self.assertTrue(os.access(commonConfiguration.pathToInstaDMG, os.X_OK), 'InstaDMG is not executable: ' + commonConfiguration.pathToInstaDMG)
		
		# pathToInstaDMGFolder
		self.assertTrue(os.path.exists(commonConfiguration.pathToInstaDMGFolder), 'Nothing exists at the path to InstaDMGFolder: ' + commonConfiguration.pathToInstaDMGFolder)
		self.assertTrue(os.path.isdir(commonConfiguration.pathToInstaDMGFolder), 'InstaDMGFolder is not a folder: ' + commonConfiguration.pathToInstaDMGFolder)
		
		# standardCatalogFolder
		self.assertTrue(os.path.exists(commonConfiguration.standardCatalogFolder), 'Nothing exists at the path to the standard catalog folder: ' + commonConfiguration.standardCatalogFolder)
		self.assertTrue(os.path.isdir(commonConfiguration.standardCatalogFolder), 'Standard catalog folder is not a folder: ' + commonConfiguration.standardCatalogFolder)
		
		# standardCacheFolder
		self.assertTrue(os.path.exists(commonConfiguration.standardCacheFolder), 'Nothing exists at the path to the standard cache folder: ' + commonConfiguration.standardCacheFolder)
		self.assertTrue(os.path.isdir(commonConfiguration.standardCacheFolder), 'Standard catalog folder is not a folder: ' + commonConfiguration.standardCacheFolder)
		
		# standardUserItemsFolder
		self.assertTrue(os.path.exists(commonConfiguration.standardUserItemsFolder), 'Nothing exists at the path to the standard user items folder: ' + commonConfiguration.standardUserItemsFolder)
		self.assertTrue(os.path.isdir(commonConfiguration.standardUserItemsFolder), 'Standard catalog folder is not a folder: ' + commonConfiguration.standardUserItemsFolder)
		
		# legacyOSDiscFolder
		self.assertTrue(os.path.exists(commonConfiguration.legacyOSDiscFolder), 'Nothing exists at the path to legacy OS disc folder: ' + commonConfiguration.legacyOSDiscFolder)
		self.assertTrue(os.path.isdir(commonConfiguration.legacyOSDiscFolder), 'Legacy OS disc folder is not a folder: ' + commonConfiguration.legacyOSDiscFolder)
		
		# standardOSDiscFolder
		self.assertTrue(os.path.exists(commonConfiguration.standardOSDiscFolder), 'Nothing exists at the path to the standard OS disc folder: ' + commonConfiguration.standardOSDiscFolder)
		self.assertTrue(os.path.isdir(commonConfiguration.standardOSDiscFolder), 'Standard OS disc folder is not a folder: ' + commonConfiguration.standardOSDiscFolder)
		
		# standardOutputFolder
		self.assertTrue(os.path.exists(commonConfiguration.standardOutputFolder), 'Nothing exists at the path to the standard output folder: ' + commonConfiguration.standardOutputFolder)
		self.assertTrue(os.path.isdir(commonConfiguration.standardOutputFolder), 'Standard output folder is not a folder: ' + commonConfiguration.standardOutputFolder)

if __name__ == '__main__':
	print commonConfiguration.pathToInstaDMG
	unittest.main()
