#!/usr/bin/python

import os, unittest

from findInstallerDisc		import findInstallerDisc

import commonConfiguration
import tempFolderManager
import managedSubprocess

class findInstallerDiscTest(unittest.TestCase):
	'''Test the class, assuming that there are images in the appropriate places'''
	
	def getAllowedBuildsFromVanilla(self, version):
		
		# get the allowedBuilds from the chosen vanilla file
		
		vanillaFile	= open(os.path.join(commonConfiguration.standardCatalogFolder, version + '_vanilla.catalog'))
		buildsInfo	= None
		for thisLine in vanillaFile:
			if thisLine.startswith('Installer Disc Builds:'):
				buildsInfo = thisLine[len('Installer Disc Builds:'):].strip().split(', ')
				break
		if buildsInfo is None:
			raise Exception('Unable to parse the "Installer Disc Builds" from the 10.6_vanilla file')
		
		return buildsInfo
	
	def test_codePath(self):
		
		# -- allowedBuilds from 10.6_vanilla
		
		buildsInfo = self.getAllowedBuildsFromVanilla('10.6')
		
		allowedBuildsResults = findInstallerDisc(allowedBuilds=buildsInfo)
		self.assertTrue(allowedBuildsResults is not None, 'When run with allowedBuilds, findInstallerDisc did not return anything')
		self.assertTrue(allowedBuildsResults['InstallerDisc'] is not None, 'When run with allowedBuilds, findInstallerDisc did not return any path to an installerDisc')
		self.assertTrue(hasattr(allowedBuildsResults['InstallerDisc'], 'getStoragePath'), 'When run with allowedBuilds, findInstallerDisc did not return a baseContainer type, but rather: %s (%s)' % (allowedBuildsResults['InstallerDisc'], type(allowedBuildsResults['InstallerDisc'])))
		self.assertTrue(os.path.exists(allowedBuildsResults['InstallerDisc'].getStoragePath()), 'The return value from findInstallerDisc run with allowedBuilds was not a valid path: ' + allowedBuildsResults['InstallerDisc'].getStoragePath())
		
		# -- searchItems
		
		# create a folder, and link in the disc from above with the proper name for a legacy run
		
		containingFolder = tempFolderManager.tempFolderManager.getNewTempFolder()
		os.symlink(allowedBuildsResults['InstallerDisc'].getStoragePath(), os.path.join(containingFolder, 'Mac OS X Install DVD.dmg'))
		
		legacyResults = findInstallerDisc(searchItems=[containingFolder])
		self.assertTrue(legacyResults is not None, 'When run without any options, findInstallerDisc did not return any results')
		self.assertTrue(legacyResults['InstallerDisc'] is not None, 'When run without any options, findInstallerDisc did not return any path to an installerDisc')
		self.assertTrue(hasattr(legacyResults['InstallerDisc'], 'getStoragePath'), 'When run without any options, findInstallerDisc did not return a baseContainer type, but rather: %s (%s)' % (legacyResults['InstallerDisc'], type(legacyResults['InstallerDisc'])))
		self.assertTrue(os.path.exists(legacyResults['InstallerDisc'].getStoragePath()), 'The return value from findInstallerDisc run without options was not a valid path: ' + legacyResults['InstallerDisc'].getStoragePath())
		
	def test_commandLine(self):
		
		pathToCommandLine = os.path.join(os.path.dirname(__file__), 'findInstallerDisc.py')
		buildsInfo = self.getAllowedBuildsFromVanilla('10.6')
		
		process = managedSubprocess.managedSubprocess([pathToCommandLine, '--allowed-builds', ", ".join(buildsInfo), '--supress-return'])
		results = process.stdout.read().split('\n')
		
		self.assertTrue(os.path.exists(results[0]), 'The first line returned by the command-line version is not a path to a valid item: ' + str(results[0]))