#!/usr/bin/python

import os, re, unittest

from volumeManager import volumeManager, dmgManager

class volumeManagerTests(unittest.TestCase):
	'''Test the diskUtility routines'''
	
	#def createImage(self):
	#	'''Create a disk image and mount it'''
	
	def test_getVolumeInfo_root(self):
		'''Test getVolumeInfo on the root volume, expecting that it is a HFS+ volume'''
		
		result = volumeManager.getVolumeInfo('/')
		self.assertTrue(result is not None, 'getVolumeInfo returned None for the root volume')
		
		# diskType
		self.assertTrue('diskType' in result, 'getVolumeInfo did not get a diskType for the root volume')
		self.assertEqual(result['diskType'], 'Hard Drive', 'The boot volume diskType was not "Hard Drive" as expected, but rather: ' + str(result['diskType']))
		
		# volumeFormat
		self.assertTrue('volumeFormat' in result, 'getVolumeInfo did not get a volumeFormat for the root volume')
		self.assertEqual(result['volumeFormat'], 'Journaled HFS+', 'The boot volume volumeFormat was not "Journaled HFS+" as expected, but rather: ' + str(result['volumeFormat']))
		
		# mountPath
		self.assertTrue('mountPath' in result, 'getVolumeInfo did not get a mountPath for the root volume')
		self.assertEqual(result['mountPath'], '/', 'The boot volume volumeFormat was not "/" as expected, but rather: ' + str(result['mountPath']))
		
		# volumeName
		self.assertTrue('volumeName' in result, 'getVolumeInfo did not get a volumeName for the root volume')
		
		# diskBsdName
		self.assertTrue('diskBsdName' in result, 'getVolumeInfo did not get a diskBsdName for the root volume')
		self.assertTrue(result['diskBsdName'].startswith('disk'), 'The boot volume diskBsdName did not start with "disk" as expected, but rather was: ' + str(result['diskBsdName']))
		
		# bsdPath
		self.assertTrue('bsdPath' in result, 'getVolumeInfo did not get a bsdPath for the root volume')
		self.assertTrue(result['bsdPath'].startswith('/dev/disk'), 'The boot volume bsdPath did not start with "/dev/disk" as expected, but rather was: ' + str(result['bsdPath']))
		self.assertTrue(result['bsdPath'].startswith('/dev/' + result['diskBsdName'] + 's'), 'The boot volume bsdPath did not start with the diskBsdName (%s) as expected, but rather was: %s' % (result['diskBsdName'], str(result['bsdPath'])))
	
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
		
		# test to make sure that everythign listed is a mount point
		for thisMountPoint in mountedVolumes:
			self.assertTrue(os.path.ismount(thisMountPoint), 'An item returned from getMountedVolumes was not a volume: ' + str(thisMountPoint))
		
		# confirm that root is excluded when it is not wanted
		mountedVolumes = volumeManager.getMountedVolumes()
		self.assertFalse('/' in mountedVolumes, 'The output of getMountedVolumes not including root still included "/"')
	
	def test_volumeManager_onRoot(self):
		'''Test volumeManager by creating a new instance with root's path'''
		
		root = volumeManager('/')
		
		# diskType
		self.assertTrue(root.diskType is not None, 'After being created with the root path, the volumeManager object did not have a diskType value')
		self.assertEqual(root.diskType, 'Hard Drive', "After being created with the root path, the volumeManager object's diskType was not 'Hard Drive' as expectd, but rather: " + root.diskType)
		
		# mountPath
		self.assertTrue(root.mountPath is not None, 'After being created with the root path, the volumeManager object did not have a mountPath value')
		self.assertEqual(root.mountPath, '/', "After being created with the root path, the volumeManager object's mountPath was not '/' as expectd, but rather: " + root.mountPath)
		
		# volumeFormat
		self.assertTrue(root.volumeFormat is not None, 'After being created with the root path, the volumeManager object did not have a volumeFormat value')
		self.assertEqual(root.volumeFormat, 'Journaled HFS+', "After being created with the root path, the volumeManager object's volumeFormat was not 'Mac OS Extended (Journaled)' as expectd, but rather: " + root.volumeFormat)
		
		# isMounted
		self.assertTrue(root.isMounted(), 'The root object is not reporting being mounted')
		

class volumeManagerTests_negative(unittest.TestCase):
	'''Test the volumeManager routines in ways that should fail'''
	
	def test_getVolumeInfo_negative(self):
		'''Test that bad info into getVolumeInfo does gets exceptions'''
		
		self.assertRaises(ValueError, volumeManager.getVolumeInfo, None)
		self.assertRaises(ValueError, volumeManager.getVolumeInfo, '')
		


if __name__ == "__main__":
	unittest.main()