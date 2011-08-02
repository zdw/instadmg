#!/usr/bin/python

import os, unittest

try:
	from .workItem				import workItem
	from .cacheController		import cacheController
	from .tempFolderManager	import tempFolderManager
	from .pathHelpers			import pathInsideFolder
except ImportError:
	from ..workItem				import workItem
	from ..cacheController		import cacheController
	from ..tempFolderManager	import tempFolderManager
	from ..pathHelpers			import pathInsideFolder

class pkgInstaller_test(unittest.TestCase):
	
	def test_remotePKGInstaller(self):
		
		sourceString 	= 'http://support.apple.com/downloads/DL986/en_US/RemoteDesktopClient.dmg'
		sourceName		= 'Remote Desktop Client 3.3.2'
		sourceChecksum	= 'sha1:707812be781a5e3635c552bef24382c1eced93cf'
		
		# -- set the cache controller so we are not using the local sources or cache
		
		foldersToRemove = cacheController.getSourceFolders()
		
		newCacheFolder = tempFolderManager.getNewTempFolder()
		cacheController.addSourceFolders(tempFolderManager.getNewTempFolder())
		cacheController.removeSourceFolders(foldersToRemove)
		cacheController.setCacheFolder(newCacheFolder)
		
		# -- instantiation
		
		remoteDMGPackage = workItem(sourceString, displayName=sourceName, checksum=sourceChecksum)
		
		self.assertTrue(remoteDMGPackage is not None)
		
		self.assertEqual(remoteDMGPackage.sourceLocation, sourceString)
		self.assertEqual(remoteDMGPackage.displayName, sourceName)
		self.assertEqual(remoteDMGPackage.checksumType, sourceChecksum.split(':')[0])
		self.assertEqual(remoteDMGPackage.checksumValue, sourceChecksum.split(':')[1])
		
		# -- download and determination
		
		remoteDMGPackage.locateFiles()
		
		# container
		
		self.assertTrue(remoteDMGPackage.foundContainer())
		self.assertTrue(remoteDMGPackage.getContainer() is not None)
		self.assertTrue(hasattr(remoteDMGPackage.getContainer(), 'isContainerType'))
		self.assertTrue(remoteDMGPackage.getContainer().isContainerType('dmg', includeSubclasses=False))
		self.assertTrue(pathInsideFolder(remoteDMGPackage.getContainer().getStoragePath(), newCacheFolder))
		
		# action
		
		self.assertTrue(remoteDMGPackage.foundAction())
		self.assertTrue(remoteDMGPackage.getAction() is not None)
		self.assertTrue(hasattr(remoteDMGPackage.getAction(), 'isActionType'))
		self.assertTrue(remoteDMGPackage.getAction().isActionType('pkgInstaller', includeSubclasses=False), 'The action type was not pkgInstaller as expected, but rather: %s' % remoteDMGPackage.getAction().getType())
