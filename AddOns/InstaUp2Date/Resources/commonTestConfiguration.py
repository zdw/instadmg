#!/usr/bin/python

import os
import commonConfiguration, tempFolderManager, installerPackage
from cacheController		import cacheController

'''Setting shared between tests'''

firstOSInstallerDiscPath	= None
def getFirstOSInstallerDiscPath():
	
	global firstOSInstallerDiscPath
	
	if firstOSInstallerDiscPath is not None:
		return firstOSInstallerDiscPath
	
	for thisItem in os.listdir(commonConfiguration.legacyOSDiscFolder):
		if os.path.splitext(thisItem)[1].lower() == '.dmg':
			firstOSInstallerDiscPath = os.path.join(commonConfiguration.legacyOSDiscFolder, thisItem)
			break
	
	if firstOSInstallerDiscPath is None:
		for thisItem in os.listdir(commonConfiguration.standardOSDiscFolder):
			if os.path.splitext(thisItem)[1].lower() == '.dmg':
				firstOSInstallerDiscPath = os.path.join(commonConfiguration.standardOSDiscFolder, thisItem)
				break
	
	if firstOSInstallerDiscPath is None:
		raise Exception("\nWarning: There were no dmg's in the installer disc folders, so no dmg testing could be done")
	
	return firstOSInstallerDiscPath

downloadedPkgInDmgPath	= None
def getDownloadedPkgInDmgPath():
	
	global downloadedPkgInDmgPath
	
	if downloadedPkgInDmgPath is not None and os.path.exists(downloadedPkgInDmgPath):
		return downloadedPkgInDmgPath
	
	# download a smaller update from Apple if it is not already cached
	cacheController.setCacheFolder(tempFolderManager.tempFolderManager.getNewTempFolder())
	cacheController.addSourceFolders(commonConfiguration.standardCacheFolder)
	sampleItemDMG = installerPackage.installerPackage('http://support.apple.com/downloads/DL792/en_US/AirPortClientUpdate2009001.dmg', 'sha1:168065c8bf2e6530a3053899ac7a6a210e9397d7')
	sampleItemDMG.findItem(progressReporter=False)
	
	downloadedPkgInDmgPath = sampleItemDMG.getItemLocalPath()
	return downloadedPkgInDmgPath