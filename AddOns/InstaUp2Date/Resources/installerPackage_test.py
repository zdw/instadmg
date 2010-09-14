#!/usr/bin/python

import os, unittest, stat, urllib

from installerPackage		import installerPackage

import commonConfiguration
from tempFolderManager 		import tempFolderManager
from commonExceptions		import FileNotFoundException
from containerController	import newContainerForPath
from cacheController		import cacheController

from cacheController_test	import cacheControllerTest

class packageTesting(unittest.TestCase):
	
	samplePackagePath = None
	
	def getSamplePackage(self):
		'''Find or pull down a known sample .pkg and source it'''
		
		if self.samplePackagePath is not None:
			return self.samplePackagePath
		
		# download a smaller update from Apple if it is not already cached
		cacheController.setCacheFolder(tempFolderManager.getNewTempFolder())
		cacheController.addSourceFolders(commonConfiguration.standardCacheFolder)
		sampleItemDMG = installerPackage('http://support.apple.com/downloads/DL792/en_US/AirPortClientUpdate2009001.dmg', 'sha1:168065c8bf2e6530a3053899ac7a6a210e9397d7')
		sampleItemDMG.findItem(progressReporter=False)
		
		# mount the image
		dmgItem = newContainerForPath(sampleItemDMG.getItemLocalPath())
		dmgItem.mount(mountReadWrite=False)
		
		samplePackagePath = os.path.join(dmgItem.getWorkingPath(), 'AirPortClientUpdate2009001.pkg')
		self.assertTrue(os.path.exists(samplePackagePath), 'Unable to setup the sameple package')
		
		self.samplePackagePath = samplePackagePath
		
		return samplePackagePath
	
	def test_isValidInstaller(self):
		'''A simple test to see if the isValidInstaller works on a valid installer''' 
		
		pathToTestFile = self.getSamplePackage()
		
		self.assertTrue(installerPackage.isValidInstaller(pathToTestFile), '')
	
#	def test_isValidInstaller_chroot(self):
#		
#		if os.getuid() != 0:
#			if hasattr(unittest, 'skip'):
#				self.skip('chroot tests only work when run as root')
#			return # we can't test here if the
#		
#		pathToTestFile = self.getSamplePackage()
#		
#		self.assertTrue(installerPackage.isValidInstaller(pathToTestFile))

class findPackages(cacheControllerTest):
	
	def test_findItem(self):
		'''Test out both local files and downloads with the findItem method'''
		
		# perform all of the the local file tests
		for thisTest in self.testMaterials:
			thisPackage = installerPackage(thisTest['fileName'], thisTest['checksumType'] + ":" + thisTest['checksumValue'], displayName=None)
			
			try:
				thisPackage.findItem(progressReporter=None)
			except FileNotFoundException, error:
				self.fail(thisTest['errorMessage'] + ', was unable to find a package - ' + str(error))
			
			thisTest['resultPath'] = thisPackage.getItemLocalPath()
			self.assertEqual(thisTest['filePath'], thisPackage.getItemLocalPath(), thisTest['errorMessage'] + ', should have been "%(filePath)s" but was: "%(resultPath)s"' % thisTest)
		
		# download a file
		thisPackage = installerPackage('http://images.apple.com/support/iknow/images/downloads_software_update.png', 'sha1:4d200d3fc229d929ea9ed64a9b5e06c5be733b38', displayName=None)
		try:
			thisPackage.findItem(progressReporter=None)
			self.assertEqual(os.path.join(cacheController.getCacheFolder(), 'downloads_software_update sha1-4d200d3fc229d929ea9ed64a9b5e06c5be733b38.png'), thisPackage.getItemLocalPath(), "Downloading a file from Apple's site returned: " + str(thisPackage.getItemLocalPath()))
		except FileNotFoundException, error:
			self.fail(thisTest['errorMessage'] + ', was unable to find a package - ' + str(error))
		
		#resultPath = cacheController.findItem('http://images.apple.com/support/iknow/images/downloads_software_update.png', 'sha1', '4d200d3fc229d929ea9ed64a9b5e06c5be733b38', progressReporter=None)
		#self.assertEqual(os.path.join(cacheController.getCacheFolder(), 'downloads_software_update sha1-4d200d3fc229d929ea9ed64a9b5e06c5be733b38.png'), resultPath, "Downloading a file from Apple's site returned: " + str(resultPath))

class packageTesting_negative(unittest.TestCase):
	
	def test_isValidInstaller_negaitve(self):
		pass
	
	def test_isValidInstaller_chroot(self):
		
		pass
