#!/usr/bin/python

import os, unittest, tempfile

from displayTools import statusHandler
from tempFolderManager import tempFolderManager

from checksum import checksumFileObject, checksum

sampleFiles			= []

def setupForTests():
	
	# sample file consisting of the letter 'a' four hundred times
	(fileHandle, filePath) = tempfile.mkstemp(dir='/tmp')
	tempFolderManager.addManagedItem(filePath) # make sure it gets taken care of
	os.write(fileHandle, "a" * 400)
	os.close(fileHandle)
	sampleFiles.append({
		'filePath' : filePath,
		'description' : 'a file containing the letter "a" 400 times',
		'sha1' : 'f475597b627a4d580ec1619a94c7afb9cc75abe4',
		'md5' : 'f4347bb35af679911623327c74b7d732'
	})
	
	# an empty file
	(fileHandle, filePath) = tempfile.mkstemp(dir='/tmp')
	os.close(fileHandle)
	sampleFiles.append({
		'filePath' : filePath,
		'description' : 'an empty file',
		'sha1' : 'da39a3ee5e6b4b0d3255bfef95601890afd80709',
		'md5' : 'd41d8cd98f00b204e9800998ecf8427e'
	})
	
	# file with spaces and symbols in the name
	(fileHandle, filePath) = tempfile.mkstemp(dir='/tmp', prefix="s % # ! '*")
	os.write(fileHandle, "firetruck" * 150)
	os.close(fileHandle)
	sampleFiles.append({
		'filePath' : filePath,
		'description' : 'file with spaces and symbols in the name',
		'sha1' : '02df49b807e866b7e5aa6fa93e8955f1b3bf4412',
		'md5' : '756078a54cb863d9ce834c857b836e8b'
	})
	
setupForTests()

class checksumTests(unittest.TestCase):
	'''Test the checksum system to make sure it gives proper results'''
	
	def test_fileChecksums(self):
		'''Checksum all sample items'''
		
		for thisFile in sampleFiles:
			for thisChecksumType in thisFile:
				if thisChecksumType in ['filePath', 'description']:
					continue
				
				result = checksum(thisFile['filePath'], checksumType=thisChecksumType, progressReporter=None)
				self.assertTrue(result is not None, 'Checksumming %s with %s returned None' % (thisFile['description'], thisChecksumType))
				self.assertEqual(result['checksum'], thisFile[thisChecksumType], 'Checksumming %s using %s did not give the expected result (%s) rather: %s' % (thisFile['description'], thisChecksumType, thisFile[thisChecksumType], result['checksum']))
