#!/usr/bin/python

import sys
import os
import hashlib
import re
import urllib2
import urlparse

for fileLocation in sys.argv[1:]:

	checksumType = "sha1" # TODO: command line switch to allow other checksum types
	
	# now we check that the file exists:
	#if not(os.path.exists(fileLocation)):
	#	raise Exception() # TODO: better errors
	
	hashGenerator = hashlib.new( checksumType )
	
	foundAFile = False
	returnArray = None
	chunksize = 1 * 1024 * 1024
	
	if os.path.isfile(fileLocation):
		HASHFILE = open(fileLocation, 'rb')
		if HASHFILE == None:
			raise Exception("Unable to open file for checksumming: %s" % folderLocation) # TODO: better errors
		
		
		
		foundAFile = True

		thisChunkSize = 1
		while thisChunkSize > 0:
			thisChunk = HASHFILE.read(chunksize)
			thisChunkSize = len(thisChunk)
			hashGenerator.update(thisChunk)
		HASHFILE.close()
		
		returnArray = (os.path.splitext(os.path.basename(fileLocation))[0], os.path.basename(fileLocation), checksumType + ":" + hashGenerator.hexdigest())
		
	elif os.path.isdir(fileLocation):
	
		for thisFolder, subFolders, subFiles in os.walk(fileLocation):
			for thisFile in subFiles:
				thisFilePath = os.path.join(thisFolder, thisFile)
				if os.path.isfile(thisFilePath) and not(os.path.islink(thisFilePath) and thisFile == "InstallThisOneOnly"):
					HASHFILE = open(thisFilePath)
					if HASHFILE == None:
						raise Exception("Unable to open file for checksumming: %s" % thisFilePath) # TODO: better errors
					foundAFile = True
					
					thisChunkSize = 1
					while thisChunkSize > 0:
						thisChunk = HASHFILE.read(chunksize)
						thisChunkSize = len(thisChunk)
						hashGenerator.update(thisChunk)
					HASHFILE.close()
					
		returnArray = (os.path.splitext(os.path.basename( urlparse.urlparse(fileLocation).path ))[0], os.path.basename( urlparse.urlparse(fileLocation).path ), checksumType + ":" + hashGenerator.hexdigest())
	
	elif re.search('^http(s)?://', fileLocation, re.I):
		HASHFILE = urllib2.urlopen(fileLocation)
		if HASHFILE == None:
			raise Exception("Unable to open file for checksumming: %s" % folderLocation) # TODO: better errors
		foundAFile = True
		
		hashGenerator.update(HASHFILE.read())
		
		HASHFILE.close()
		
		returnArray = (os.path.splitext(os.path.basename(fileLocation))[0], fileLocation, checksumType + ":" + hashGenerator.hexdigest())
	
	if foundAFile == False:
		raise Exception() # TODO: better errors
	
	print "\t" + "\t".join(returnArray)