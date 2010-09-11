#!/usr/bin/python

import os, unittest, tempfile

from displayTools import statusHandler
from tempFolderManager import tempFolderManager

from checksum import checksumFileObject, checksum

class checksumTests(unittest.TestCase):
	'''Test the checksum system to make sure it gives proper results'''
	
	sampleFolder		= None
	sampleFiles			= []
	
	def setUp(self):
		# setup a folder to hold our temporary items
		self.sampleFolder = tempFolderManager.getNewTempFolder()
		
		# sample file consisting of the letter 'a' four hundred times
		myFile = open(os.path.join(self.sampleFolder, 'aFile'), 'w')
		myFile.write("a" * 400)
		myFile.close()
		self.sampleFiles.append({
			'filePath' : os.path.join(self.sampleFolder, 'aFile'),
			'description' : 'a file containing the letter "a" 400 times',
			'sha1' : 'f475597b627a4d580ec1619a94c7afb9cc75abe4',
			'md5' : 'f4347bb35af679911623327c74b7d732'
		})
		
		# an empty file
		open(os.path.join(self.sampleFolder, 'emptyFile'), 'w').close()
		self.sampleFiles.append({
			'filePath' : os.path.join(self.sampleFolder, 'emptyFile'),
			'description' : 'an empty file',
			'sha1' : 'da39a3ee5e6b4b0d3255bfef95601890afd80709',
			'md5' : 'd41d8cd98f00b204e9800998ecf8427e'
		})
		
		# a subfolder
		os.mkdir(os.path.join(self.sampleFolder, 'simpleSubfolder'))
		self.sampleFiles.append({
			'filePath' : os.path.join(self.sampleFolder, 'simpleSubfolder'),
			'description' : 'a folder containing a single file',
			'sha1' : '004073ec84557678eb540cbefdacbbd932a7dd98',
			'md5' : '353c93582c0b3443f37fad4d498a58f1'
		})
		
		# file with spaces and symbols in the name, and the word "firetruck" 15 times
		myFile = open(os.path.join(self.sampleFolder, 'simpleSubfolder', 's % # ! \'*'), 'w')
		myFile.write("firetruck" * 150)
		myFile.close()
		self.sampleFiles.append({
			'filePath' : os.path.join(self.sampleFolder, 'simpleSubfolder', 's % # ! \'*'),
			'description' : 'file with spaces and symbols in the name',
			'sha1' : '02df49b807e866b7e5aa6fa93e8955f1b3bf4412',
			'md5' : '756078a54cb863d9ce834c857b836e8b'
		})
		
		# folder with a symlink in it
		os.mkdir(os.path.join(self.sampleFolder, 'folderContainingSymlink'))
		os.symlink('badSymlinkTarget', os.path.join(self.sampleFolder, 'folderContainingSymlink', 'badSymlink'))
		self.sampleFiles.append({
			'filePath' : os.path.join(self.sampleFolder, 'folderContainingSymlink'),
			'description' : 'symlink to the folder simpleSubfolder',
			'sha1' : '0750b25b8e0b817fb886166b6a9246db6e715914',
			'md5' : '63f025923ee362d59c81ecdd9e89a650'
		})
	
	def tearDown(self):
		tempFolderManager.cleanupForExit()
	
	def test_fileChecksums(self):
		'''Checksum all sample items'''
		
		for thisFile in self.sampleFiles:
			for thisChecksumType in thisFile:
				if thisChecksumType in ['filePath', 'description']:
					continue
				
				result = checksum(thisFile['filePath'], checksumType=thisChecksumType, progressReporter=None)
				self.assertTrue(result is not None, 'Checksumming %s with %s returned None' % (thisFile['description'], thisChecksumType))
				self.assertEqual(result['checksum'], thisFile[thisChecksumType], 'Checksumming %s using %s did not give the expected result (%s) rather: %s' % (thisFile['description'], thisChecksumType, thisFile[thisChecksumType], result['checksum']))
