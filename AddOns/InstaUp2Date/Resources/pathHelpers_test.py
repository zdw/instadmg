#!/usr/bin/python

import os, unittest

import pathHelpers

class volumeManagerTests(unittest.TestCase):
	'''Test the pathHelper functions'''
	
	def normalizePathTestHelper(self, testPath, expectedResult):
		result = pathHelpers.normalizePath(testPath)
		self.assertEqual(expectedResult, result, 'normalizePath did not return "%s" for "%s", but rather: %s' % (expectedResult, testPath, result))
			
	def test_normalizePath(self):
		'''Test that normalizePath gives the right results'''
		
		# make sure it does not expand the last item
		self.normalizePathTestHelper('/tmp', '/tmp')
		
		# make sure it does not expand the last item even when given a traling slash
		self.normalizePathTestHelper('/tmp/', '/tmp')
		
		# see that things are expanded
		self.normalizePathTestHelper('/tmp/probably_does_not_exist', '/private/tmp/probably_does_not_exist')
		
		# relative path
		self.normalizePathTestHelper('probably_does_not_exist', os.path.join(os.getcwd(), 'probably_does_not_exist'))
		
		# relative with trailing slash
		self.normalizePathTestHelper('probably_does_not_exist/', os.path.join(os.getcwd(), 'probably_does_not_exist'))
		
		# tilde test
		self.normalizePathTestHelper('~/probably_does_not_exist/', os.path.expanduser('~/probably_does_not_exist'))
		
		# test root
		self.normalizePathTestHelper('/', '/')
	
	def pathInsideFolderTestHelper(self, testPath, testFolder, expectedResult):
		result = pathHelpers.pathInsideFolder(testPath, testFolder)
		self.assertEqual(result, expectedResult, 'When testing pathInsideFolder on whether "%s" was inside "%s" it incorrectly returned %s' % (testPath, testFolder, result))
	
	def test_pathInsideFolder(self):
		'''Test that pathInsideFolder gives the right results'''
		
		# simple positive test
		self.pathInsideFolderTestHelper('/private/tmp/bob', '/private/tmp', True)
		
		# simple negative test
		self.pathInsideFolderTestHelper('/Applications', '/private/tmp', False)
		
		# same folder test
		self.pathInsideFolderTestHelper('/tmp', '/private/tmp', False)
		
		# directories test
		self.pathInsideFolderTestHelper('/System/Library', '/System/', True)
		
		# reversed directories negative test
		self.pathInsideFolderTestHelper('/System/', '/System/Library', False)
		
		# normalizing test
		self.pathInsideFolderTestHelper('/tmp/bob', '/private/tmp', True)
		
		# symlinked test
		self.pathInsideFolderTestHelper('/sbin/mount_ftp', '/sbin', True)
		
		# items in root
		self.pathInsideFolderTestHelper('/System', '/', True)
		
	def test_pathInsideFolder_negative(self):
		'''Test that pathInsideFolder fails when it should'''
		
		self.assertRaises(ValueError, pathHelpers.pathInsideFolder, "", "/tmp")
		self.assertRaises(ValueError, pathHelpers.pathInsideFolder, "", "/mach_kernel")
		self.assertRaises(ValueError, pathHelpers.pathInsideFolder, "", "/tmp/bob")

if __name__ == "__main__":
	unittest.main()