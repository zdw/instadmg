#!/usr/bin/python

import os, unittest, tempfile

from displayTools import statusHandler
from tempFolderManager import tempFolderManager

from checksum import checksumFileObject, checksum

sampleFiles			= []
nullStatusHandler	= None

def setupForTests():
	# neuter the output
	(fileHandle, filePath) = tempfile.mkstemp(dir="/tmp")
	nullOutputFile = os.fdopen(fileHandle, "w")
	tempFolderManager.addManagedItem(filePath) # make sure it gets taken care of
	nullStatusHandler = statusHandler(outputChannel=nullOutputFile)
	
	# create a sample file consisting of the letter 'a' four hundred times
	(fileHandle, filePath) = tempfile.mkstemp(dir="/tmp")
	tempFolderManager.addManagedItem(filePath) # make sure it gets taken care of
	os.write(fileHandle, "a" * 400)
	os.close(fileHandle)
	sampleFiles.append({
		'filePath' : filePath,
		'description' : 'a file containing the letter "a" 400 times',
		'sha1' : 'f475597b627a4d580ec1619a94c7afb9cc75abe4',
		'md5' : 'f4347bb35af679911623327c74b7d732'
	})
setupForTests()

class checksumTests(unittest.TestCase):
	'''Test the checksum system to make sure it gives proper results'''
	
	def test_fileChecksum(self):
		'''Checksum all sample files'''
		
		for thisFile in sampleFiles:
			for thisChecksumType in thisFile:
				if thisChecksumType in ['filePath', 'description']:
					continue
				
				result = checksum(thisFile['filePath'], checksumType=thisChecksumType, progressReporter=nullStatusHandler)
				self.assertTrue(result is not None, 'Checksumming %s with %s returned None' % (thisFile['description'], thisChecksumType))
				self.assertEqual(result['checksum'], thisFile[thisChecksumType], 'Checksumming %s using %s did not give the expected result (%s) rather: %s' % (thisFile['description'], thisChecksumType, thisFile[thisChecksumType], result['checksum']))
