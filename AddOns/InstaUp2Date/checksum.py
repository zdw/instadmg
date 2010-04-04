#!/usr/bin/env python

import os, sys, re
import hashlib, urllib2, urlparse, tempfile, optparse
import atexit, shutil, stat

def cleanupTempFolder(tempFolder):
	if os.path.exists(tempFolder) and os.path.isdir(tempFolder):
		# ToDo: log this
		shutil.rmtree(tempFolder, ignore_errors=True)

def cheksumFileObject(hashFileObject, targetFileObject, targetFileName, expectedLength, chunkSize, fileType="file", copyToPath=None, reportProgress=False, reportStepPercentage=15):
	
	# todo: sanity check the input
	
	# prep for reporting progress
	processedLength = 0
	lastReport = 0
	
	writeFileObject = None
	if copyToPath != None:
		writeFileObject = open(copyToPath, 'wb')
		if writeFileObject == None:
			raise Exception("Unable to open file for writing: %s" % writeTarget)
	
	thisChunkSize = 1 # to get us into the first loop
	
	# ToDo: log this better
	if reportProgress == True:
		
		verb = "Checksumming"
		if fileType == "download":
			verb = "Downloading"
		
		if expectedLength == None:
			sys.stderr.write("%s %s (unknown length) in chunks of %i bytes\n" % (verb, targetFileName, chunkSize))
			reportProgress = False
		else:
			sys.stderr.write("%s %s (%i bytes) in chunks of %i bytes: 0%%" % (verb, targetFileName, expectedLength, chunkSize))
		sys.stderr.flush()
	
	while thisChunkSize > 0:
		thisChunk = targetFileObject.read(chunkSize)
		thisChunkSize = len(thisChunk)
		hashFileObject.update(thisChunk)
		
		processedLength += thisChunkSize
		
		if reportProgress == True:
			if processedLength >= expectedLength:
				sys.stderr.write("  100%\n")
				reportProgress = False
			
			elif ((processedLength - lastReport)* 100)/expectedLength >= reportStepPercentage:
				lastReport = processedLength
				sys.stderr.write("  %i%%" % int(((processedLength)* 100)/expectedLength))
		sys.stderr.flush()
		
		if writeFileObject != None:
			writeFileObject.write(thisChunk)
	
	if writeFileObject != None:
		writeFileObject.close()


def checksum(location, tempFolderPrefix="InstaDMGtemp", checksumType="sha1", outputFolder=None, returnCopy=False, chunkSize=5*1024*1024, reportProgress=True, reportStepPercentage=15):
	'''Return the checksum of a given file or folder'''
	
	# validate input
	if location == None:
		raise Exception('Checksum called with a empty file location')
	if checksumType == None:
		raise Exception('Checksum called with a empty checksum type')
	
	
	# queue up the targets
	targets = []
	locationURL = urlparse.urlparse(location)
	
	overallType = None
	
	if locationURL.scheme == '' or locationURL.scheme == 'file':
		# we have a local path, and need to check if we have a folder
	
		if not os.path.exists(location):
			raise Exception('Checksum called with a file location that does not exist: %s' % location)
		
		if os.path.isfile(location):
			targets.append({'type':'file', 'sourceUrl':urlparse.urlparse("file://" + location), 'relativePath':os.path.basename(location)})
			overallType = "file"
		
		elif os.path.isdir(location):
			overallType = "folder"
			
			if reportProgress == True:
				sys.stderr.write("Building file list...\n")
				sys.stderr.flush()
			
			# walk the directory adding everything
			startFolder = os.path.realpath(os.path.expanduser(location))
			for thisFolder, subFolders, subFiles in os.walk(startFolder):
				translatedFolder = thisFolder.replace(os.path.commonprefix([thisFolder, startFolder]), '', 1)
								
				while os.path.isabs(translatedFolder) and len(translatedFolder) > 0:
					translatedFolder = translatedFolder[1:] # we need relative paths
				
				for thisFile in subFiles:
					thisFilePath = os.path.join(thisFolder, thisFile)
					if os.path.islink(thisFilePath):
						targets.append({'type':'symlink', 'sourceUrl':urlparse.urlparse("file://" + thisFilePath), 'relativePath':os.path.join(translatedFolder, thisFile), 'target':os.readlink(thisFilePath)})
					elif os.path.isfile(thisFilePath): # just in case we get handed something like /dev
						targets.append({'type':'file', 'sourceUrl':urlparse.urlparse("file://" + thisFilePath), 'relativePath':os.path.join(translatedFolder, thisFile)})
					
				
				# note: this only works if we keep these in order before their contents
				for thisSubFolder in subFolders:
					targets.append({'type':'folder', 'relativePath':os.path.join(translatedFolder, thisSubFolder)})
					
					
		else:
			raise Exception('Checksum called on a location that is neither a file or folder: %s' % location)
	
	elif locationURL.scheme == 'http' or locationURL.scheme == 'https':
		targets.append({'type':'url', 'sourceUrl':locationURL, 'relativePath':os.path.basename(locationURL.path)})
		overallType = "url"
		
	else:
		raise Exception('Checksum called with a location that does not support: %s' % location)
	
	
	# setup a temporary folder to house the downloads if we are bringing this down
	tempFolder = None
	cacheLocation = None
	if returnCopy == True:
		tempFolder = tempfile.mkdtemp(prefix=tempFolderPrefix, dir='/tmp') # note: the default tempdir would not go away in a reboot
		if tempFolder == None:
			raise Exception('Internal error: unable to create tempfolder')
		atexit.register(cleanupTempFolder, tempFolder)
		cacheLocation = tempFolder
	
	
	# warm up the checksummer
	hashGenerator = hashlib.new(checksumType)
	
	if overallType == "folder" and reportProgress == True:
		sys.stderr.write("Processing %i items: 0%%" % len(targets))
		sys.stderr.flush()
	
	itemsProcessed = 0;
	lastReport = 0;
	
	targetLength = None
	
	if overallType == "url":
		thisTarget = targets[0]
		try:
			readFile = urllib2.urlopen(thisTarget['sourceUrl'].geturl())
		except IOError, error:
			if hasattr(error, 'reason'):
				raise Exception('Unable to connect to remote url: %s got error: %s' % (thisTarget['sourceUrl'].geturl(), error.reason))
			elif hasattr(error, 'code'):
				raise Exception('Got status code: %s while trying to connect to remote url: %s' % (str(error.code), thisTarget['sourceUrl'].geturl()))
		
		if readFile == None:
			raise Exception("Unable to open file for checksumming: %s" % thisTarget['sourceUrl'].getURL())
		
		# default the filename to the last bit of path of the url
		thisTarget['relativePath'] = os.path.basename(thisTarget['sourceUrl'].path)
		if thisTarget['relativePath'] == '':
			thisTarget['relativePath'] = thisTarget['sourceUrl'].netloc
		
		# grab the name of the file from the http headers if it is avalible
		httpHeader = readFile.info()
		if httpHeader.has_key("content-length"):
			try:
				targetLength = int(httpHeader.getheader("content-length"))
			except:
				pass # 
		
		if httpHeader.has_key("content-disposition"):
			thisTarget['relativePath'] = httpHeader.getheader("content-disposition")
		
		writeTarget = None
		if tempFolder != None:
			writeTarget = os.path.join(tempFolder, thisTarget['relativePath'])
			cacheLocation = writeTarget
		
		cheksumFileObject(hashGenerator, readFile, thisTarget['relativePath'], targetLength, fileType="download", chunkSize=1024*100, copyToPath=writeTarget, reportProgress=True, reportStepPercentage=reportStepPercentage)
		
		readFile.close()
	
	elif overallType == "file":
		thisTarget = targets[0]
		
		readFile = open(thisTarget['sourceUrl'].path)
		if readFile == None:
			raise Exception("Unable to open file for checksumming: %s" % thisTarget['sourceUrl'].path)
		
		targetLength = os.stat(thisTarget['sourceUrl'].path)[stat.ST_SIZE]
		
		writeTarget = None
		if tempFolder != None:
			writeTarget = os.path.join(tempFolder, thisTarget['relativePath'])
		
		cheksumFileObject(hashGenerator, readFile, os.path.basename(thisTarget['sourceUrl'].path), targetLength, chunkSize, fileType="file", copyToPath=writeTarget, reportProgress=True, reportStepPercentage=reportStepPercentage)			
		readFile.close()
	
	elif overallType == "folder":
		for thisTarget in targets:
			
			if thisTarget['type'] == 'folder':
				# create the folders needed to hold the stuff if we are going to be caching
				if tempFolder != None:
					os.mkdir( os.path.join(tempFolder, thisTarget['relativePath']) )
				
				# add this to the hash
				hashGenerator.update("folder %s" % thisTarget['relativePath'])
			
			elif thisTarget['type'] == 'symlink':
				if tempFolder != None:
					os.symlink(thisTarget['target'], os.path.join(tempFolder, thisTarget['relativePath']))
				
				# because broken links can't be opened we will checksum on path we are linking to
				hashGenerator.update("softlink %s to %s" % (thisTarget['target'], thisTarget['relativePath']))
			
			elif thisTarget['type'] == 'file':
				readFile = open(thisTarget['sourceUrl'].path)
				if readFile == None:
					raise Exception("Unable to open file for checksumming: %s" % thisTarget['sourceUrl'].geturl())

				targetLength = os.stat(thisTarget['sourceUrl'].path)[stat.ST_SIZE]
					
				
				writeTarget = None
				if tempFolder != None:
					writeTarget = os.path.join(tempFolder, thisTarget['relativePath'])
				
				# add the path to the checksum
				hashGenerator.update("file %s" % thisTarget['relativePath'])
				
				cheksumFileObject(hashGenerator, readFile, os.path.basename(thisTarget['sourceUrl'].path), targetLength, chunkSize, copyToPath=writeTarget)			
				
				readFile.close()
				
			itemsProcessed += 1
			
			# report progress if this is a folder
			if overallType == "folder" and reportProgress == True:
				if itemsProcessed >= len(targets):
					sys.stderr.write("  100%\n")
					
				elif ((itemsProcessed - lastReport)* 100)/len(targets) >= reportStepPercentage:
					lastReport = itemsProcessed
					sys.stderr.write("  %i%%" % int(((itemsProcessed)* 100)/len(targets)))
				sys.stderr.flush()
	
	
	returnValues = {'name':os.path.basename(location), 'checksum':hashGenerator.hexdigest(), 'checksumType':checksumType}
	
	# Return the location of the local copy if we were asked to
	if returnCopy == True and cacheLocation != None:
		returnValues["cacheLocation"] = cacheLocation
	
	return returnValues

	
#------------------------------MAIN------------------------------

if __name__ == "__main__":
	
	allowedChecksumAlgorithms = ("sha1", "sha224", "sha256", "sha384", "sha512", "md5")
	
	optionParser = optparse.OptionParser()
	optionParser.add_option("-a", "--checksum-algorithm", default="sha1", action="store", dest="checksumAlgorithm", choices=allowedChecksumAlgorithms, help="Disable progress notifications")
	optionParser.add_option("-d", "--disable-progress", default=True, action="store_false", dest="reportCheckSum", help="Disable progress notifications")
	optionParser.add_option("-r", "--report-progress-step", default=15, action="store", type="int", dest="reportStepPercentage", help="Percent to wait before reporting progress")
	optionParser.add_option("-s", "--chunk-size", default=5*1024*1024, action="store", type="int", dest="chunkSize", help="Folder to copy dat to")
	optionParser.add_option("-t", "--output-folder", default=None, action="store", dest="outputFolder", type="string", help="Folder to copy dat to")
	(options, args) = optionParser.parse_args()
	
	for location in args:
		data = checksum(
			location,
			checksumType=options.checksumAlgorithm,
			reportProgress=options.reportCheckSum,
			reportStepPercentage=options.reportStepPercentage
		)
		print "\t".join(["", os.path.splitext(data['name'])[0], location, data['checksumType'] + ":" + data['checksum']])
