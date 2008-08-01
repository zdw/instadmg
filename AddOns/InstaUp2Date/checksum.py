#!/usr/bin/python

import sys
import os
import hashlib

for arg in sys.argv[1:]:

	fileLocation = arg
	checksumType = "sha1"
	
	# now we check that the file exists:
	if not(os.path.exists(fileLocation)):
		raise Exception() # TODO: better errors
	
	hashGenerator = hashlib.new( checksumType )
	foundAFile = False
	
	if os.path.isfile(fileLocation):
		HASHFILE = open(fileLocation)
		if HASHFILE == None:
			raise Exception("Unable to open file for checksumming: %s" % folderLocation) # TODO: better errors
		foundAFile = True
		hashGenerator.update(HASHFILE.read())
		HASHFILE.close()
	
	for thisFolder, subFolders, subFiles in os.walk(fileLocation):
		for thisFile in subFiles:
			thisFilePath = os.path.join(thisFolder, thisFile)
			if os.path.isfile(thisFilePath) and not(os.path.islink(thisFilePath) and thisFile == "InstallThisOneOnly"):
				HASHFILE = open(thisFilePath)
				if HASHFILE == None:
					raise Exception("Unable to open file for checksumming: %s" % thisFilePath) # TODO: better errors
				foundAFile = True
				hashGenerator.update(HASHFILE.read())
				HASHFILE.close()
	
	if foundAFile == False:
		raise Exception() # TODO: better errors
	
	print "\t%s\t%s\t%s:%s" % (os.path.splitext(os.path.basename(fileLocation))[0], os.path.basename(fileLocation), checksumType, hashGenerator.hexdigest())