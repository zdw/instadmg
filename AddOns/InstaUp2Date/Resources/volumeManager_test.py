#!/usr/bin/python

import unittest, re

from volumeManager import volumeManager, dmgManager

class volumeManagerTests(unittest.TestCase):
	'''Test the diskUtility rotines to make sure they work'''
	
	#def createImage(self):
	#	'''Create a disk image and mount it'''
	
	def test_getVolumeInfo_root(self):
		'''Test getVolumeInfo on the root volume, expecting that it is a HFS+ volume'''
		
		result = volumeManager.getVolumeInfo('/')
		self.assertTrue(result is not None, 'getVolumeInfo returned None for the root volume')
		
		# disk-type
		self.assertTrue('disk-type' in result, 'getVolumeInfo did not get a disk-type for the root volume')
		self.assertEqual(result['disk-type'], 'Hard Drive', 'The boot volume disk-type was not "Hard Drive" as expected, but rather: ' + str(result['disk-type']))
		
		# volume-format
		self.assertTrue('volume-format' in result, 'getVolumeInfo did not get a volume-format for the root volume')
		self.assertEqual(result['volume-format'], 'Mac OS Extended (Journaled)', 'The boot volume volume-format was not "Mac OS Extended (Journaled)" as expected, but rather: ' + str(result['volume-format']))
		
		# mount-path
		self.assertTrue('mount-path' in result, 'getVolumeInfo did not get a mount-path for the root volume')
		self.assertEqual(result['mount-path'], '/', 'The boot volume volume-format was not "/" as expected, but rather: ' + str(result['mount-path']))
		
		# volume-name
		self.assertTrue('volume-name' in result, 'getVolumeInfo did not get a volume-name for the root volume')
		
		# disk-bsd-name
		self.assertTrue('disk-bsd-name' in result, 'getVolumeInfo did not get a disk-bsd-name for the root volume')
		self.assertTrue(result['disk-bsd-name'].startswith('disk'), 'The boot volume disk-bsd-name did not start with "disk" as expected, but rather was: ' + str(result['disk-bsd-name']))
		
		# bsd-path
		self.assertTrue('bsd-path' in result, 'getVolumeInfo did not get a bsd-path for the root volume')
		self.assertTrue(result['bsd-path'].startswith('/dev/disk'), 'The boot volume bsd-path did not start with "/dev/disk" as expected, but rather was: ' + str(result['bsd-path']))
		self.assertTrue(result['bsd-path'].startswith('/dev/' + result['disk-bsd-name'] + 's'), 'The boot volume bsd-path did not start with the disk-bsd-name (%s) as expected, but rather was: %s' % (result['disk-bsd-name'], str(result['bsd-path'])))
	
	def test_getVolumeInfo_Applications(self):
		'''Test that using getVolumeInfo on an item inside of a volume returns the volume's info'''
		
		rootResult = volumeManager.getVolumeInfo('/')
		self.assertTrue(rootResult is not None, 'getVolumeInfo returned None for the root volume')
		
		applicationsResult = volumeManager.getVolumeInfo('/Applications')
		self.assertTrue(applicationsResult is not None, 'getVolumeInfo returned None for the Applications folder')
		
		self.assertEqual(rootResult, applicationsResult, 'getVolumeInfo did not return the same information for the root volume as it did for Applications')
	
	def test_getMacOSVersionAndBuildOfVolume(self):
		'''Test that getMacOSVersionAndBuildOfVolume can get the information from the root volume'''
		
		version, build = volumeManager.getMacOSVersionAndBuildOfVolume('/')
		
		# version
		self.assertTrue(version is not None, 'getMacOSVersionAndBuildOfVolume got None as the version of MacOS on the root volume')
		self.assertTrue(version.startswith('10.'), 'The value that getMacOSVersionAndBuildOfVolume returned for the version of MacOS on the root volume did not start with "10.": ' + version)
		
		# build
		self.assertTrue(build is not None, 'getMacOSVersionAndBuildOfVolume got None as the build of MacOS on the root volume')
		self.assertTrue(re.match('^\d+[A-Z]\d+[a-zA-Z]?$', build), 'The value that getMacOSVersionAndBuildOfVolume returned for the build of MacOS on the root volume did not look correct: ' + build)
	
	def test_getMountedVolumes(self):
		'''Test that getMountedVolumes is returning a list of volumes'''
		
		# make sure that something is being returned
		mountedVolumes = volumeManager.getMountedVolumes(excludeRoot=False)
		self.assertTrue(hasattr(mountedVolumes, '__iter__'), 'The output of getMountedVolumes including root was not an array')
		self.assertTrue('/' in mountedVolumes, 'The output of getMountedVolumes including root did not include "/"')
		
		
		

class volumeManagerTests_negative(unittest.TestCase):
	'''Test the volumeManager routines in ways that should fail'''
	
	def test_getVolumeInfo_negative(self):
		'''Test that bad info into getVolumeInfo does gets exceptions'''
		
		self.assertRaises(ValueError, volumeManager.getVolumeInfo, None)
		self.assertRaises(ValueError, volumeManager.getVolumeInfo, '')
		


if __name__ == "__main__":
	unittest.main()