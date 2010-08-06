#!/usr/bin/env python

import os, time, hashlib, urllib, urllib2, urlparse, stat

from displayTools import translateBytes, secondsToReadableTime, statusHandler
from tempFolderManager import tempFolderManager

def checksumFileObject(hashFileObject, targetFileObject, targetFileName, expectedLength, chunkSize=None, copyToPath=None, progressReporter=None):
	
	# todo: sanity check the input
	assert hasattr(targetFileObject, "read"), "The target file object does not look useable"
	
	if progressReporter in [None, False]:
		progressReporter = None
	elif isinstance(progressReporter, statusHandler):
		pass # things are already set
	else:
		raise Exception('Unable to understand what the progressReporter is: ' + str(progressReporter))
		
	writeFileObject = None
	if copyToPath != None:
		writeFileObject = open(copyToPath, 'wb')
		if writeFileObject == None:
			raise Exception("Unable to open file for writing: %s" % writeTarget)
	
	# set the chunk size if it has not already been set
	if chunkSize is None:
		if hasattr(targetFileObject, "geturl"): # a ULR object
			chunkSize = 1024*100 # 100KiB for urls
		else:
			chunkSize = 5*1024*1024 # 5 MiB for local files
	
	thisChunkSize = 1 # to get us into the first loop
	processedLength = 0
	startReportTime = time.time()
	
	if progressReporter is not None:
		# prep for reporting progress
		lastReportTime = startReportTime
	
	while thisChunkSize > 0:
		thisChunk = targetFileObject.read(chunkSize)
		thisChunkSize = len(thisChunk)
		hashFileObject.update(thisChunk)
		
		processedLength += thisChunkSize
		
		if progressReporter is not None:
			processSpeed = int(thisChunkSize/(time.time() - lastReportTime))
			lastReportTime = time.time()
			
			if expectedLength is not None and processedLength >= expectedLength: # in case we go over
				progressReporter.update(updateMessage="100%")
			elif expectedLength is None:
				progressReporter.update(updateMessage='%s (%s/sec)' % (translateBytes(processedLength), translateBytes(processSpeed)))
			else:
				processedPercentage = int(((processedLength)* 100)/expectedLength)
				progressReporter.update(updateMessage='%i%% (%s/sec)' % (processedPercentage, translateBytes(processSpeed)))
		
		if writeFileObject != None:
			writeFileObject.write(thisChunk)
	
	if writeFileObject != None:
		writeFileObject.close()
	
	return (processedLength, time.time() - startReportTime)


def checksum(location, tempFolderPrefix="InstaDMGtemp", checksumType="sha1", outputFolder=None, chunkSize=None, progressReporter=True):
	'''Return the checksum of a given file or folder'''
	
	# validate input
	if location is None:
		raise Exception('Checksum called with a empty file location')
	if checksumType is None:
		raise Exception('Checksum called with a empty checksum type')
	if outputFolder is not None and not os.path.isdir(outputFolder):
		raise Exception('The output folder given does not exist, or is not a folder: ' + outputFolder)
	
	# confirm that hashlib supports the hash type:
	try:
		hashlib.new(checksumType)
	except ValueError:
		raise Exception("Hash type: %s is not supported by hashlib" % checksumType)
	
	# setup a temporary folder to house the downloads if we are bringing this down
	cacheFolder = None
	
	if outputFolder is not None:
		cacheFolder = tempFolderManager.getNewTempFolder()
	
	# warm up the checksummer
	hashGenerator = hashlib.new(checksumType)
	
	# get the progress reporter ready
	if progressReporter is True:
		# default to the statusHandler
		progressReporter = statusHandler()
	
	elif isinstance(progressReporter, statusHandler):
		pass # things are already set
	
	elif progressReporter in [False, None]:
		progressReporter = None # need to be consistent
	
	else:
		raise Exception('Unable to understand what the progressReporter is: ' + str(progressReporter))
	
	
	locationURL = urlparse.urlparse(location)
	if locationURL.scheme in ['', 'file']:
		# we have a local path, and need to check if we have a folder
		# ToDo: figure out what to do with file:// urls
		
		fileName = os.path.basename(os.path.abspath(location))
		
		if chunkSize is None:
			chunkSize = 1*1024*1024 # 1 MiB chunks for local files
		
		if not os.path.exists(location):
			raise Exception('Checksum called with a file location that does not exist: %s' % location)
		
		elif os.path.isdir(location):
			
			startReportTime = time.time()
			
			if progressReporter is not None:
				progressReporter.update(statusMessage="Building file list: ", updateMessage="0 items")
			
			# get a quick count
			itemCount = 0
			targetFolder = os.path.realpath(os.path.expanduser(location))
			for thisFolder, subFolders, subFiles in os.walk(targetFolder):
				
				for thisFile in subFiles:
					thisFilePath = os.path.join(thisFolder, thisFile)
					# note: we skip anything that is not a link or a file (ie: /dev)
					if os.path.islink(thisFilePath) or os.path.isfile(thisFilePath):
						itemCount += 1
				
				for thisFolder in subFolders:
					itemCount += 1
				
				if progressReporter is not None:
					progressReporter.update(updateMessage="%i items" % itemCount)
			
			# change the status message
			if progressReporter is not None:
				progressReporter.update(statusMessage="Checksumming item ", updateMessage="1 of %i" % itemCount)
			
			# process the items
			processedCount = 0
			for processFolder, subFolders, subFiles in os.walk(targetFolder):
				
				for thisFile in subFiles:
					thisFilePath = os.path.join(processFolder, thisFile)
					relativeFilePath = os.path.join(processFolder.replace(targetFolder, '', 1), thisFile)
					if os.path.isabs(relativeFilePath):
						relativeFilePath = relativeFilePath[1:]
					
					if os.path.islink(thisFilePath):
						if cacheFolder is not None:
							os.symlink(os.readlink(thisFilePath), os.path.join(tempFolder, relativeFilePath))
						
						hashGenerator.update("softlink %s to %s" % (os.readlink(thisFilePath), relativeFilePath))
						
					elif os.path.isfile(thisFilePath):
						
						readFile = open(thisFilePath)
						if readFile == None:
							raise Exception("Unable to open file for checksumming: " + thisFilePath)
						
						targetLength = os.stat(thisFilePath)[stat.ST_SIZE]
						writeTarget = None
						if cacheFolder != None:
							writeTarget = os.path.join(cacheFolder, relativeFilePath)
						
						# add the path to the checksum
						hashGenerator.update("file " + relativeFilePath)
						
						checksumFileObject(hashGenerator, readFile, thisFile, targetLength, chunkSize, copyToPath=writeTarget)
						readFile.close()
												
					else:
						continue # skip anything that is not a link or a file (ie: /dev)
					
					processedCount += 1
					if progressReporter is not None:
						progressReporter.update(updateMessage="%i of %i" % (processedCount, itemCount))
				
				for thisFolder in subFolders:
					thisFolderPath = os.path.join(processFolder, thisFolder)
					relativeFolderPath = os.path.join(processFolder.replace(targetFolder, '', 1), thisFolder)
					if os.path.isabs(relativeFolderPath):
						relativeFolderPath = relativeFolderPath[1:]
					
					if os.path.islink(thisFolderPath):
						if cacheFolder is not None:
							os.symlink(os.readlink(thisFilePath), os.path.join(cacheFolder, relativeFilePath))
						
						hashGenerator.update("softlink %s to %s" % (os.readlink(thisFilePath), relativeFilePath))
					
					else:
						if cacheFolder != None:
							os.mkdir( os.path.join(cacheLocation, relativeFolderPath) )
						
						# add this to the hash
						hashGenerator.update("folder %s" % relativeFolderPath)
					
					processedCount += 1
					if progressReporter is not None:
						progressReporter.update(updateMessage="%i of %i" % (processedCount, itemCount))
					
			
			if progressReporter is not None:
				progressReporter.update(statusMessage='Checksummed %s (%i items) in %s' % (fileName, processedCount, secondsToReadableTime(time.time() - startReportTime)), updateMessage='', forceOutput=True)
				
			
		elif os.path.isfile(location):
			
			fileName = os.path.basename(location)
			readFile = open(location)
			if readFile == None:
				raise Exception("Unable to open file for checksumming: %s" % location)
			
			targetLength = os.stat(location)[stat.ST_SIZE]
			
			writeTarget = None
			if cacheFolder != None:
				writeTarget = os.path.join(cacheFolder, os.path.basename(location))
			
			if progressReporter is not None:
				progressReporter.update(statusMessage="Checksumming %s (%s) in chunks of %s: " % (fileName, translateBytes(targetLength), translateBytes(chunkSize)), updateMessage="0%")
			
			processedBytes, processSeconds = checksumFileObject(hashGenerator, readFile, os.path.basename(location), targetLength, chunkSize=chunkSize, copyToPath=writeTarget, progressReporter=progressReporter)
			
			if progressReporter is not None:
				progressReporter.update(statusMessage='Checksummed %s (%s) in %s (%s/sec)' % (fileName, translateBytes(processedBytes), secondsToReadableTime(processSeconds), translateBytes(processedBytes/processSeconds)), updateMessage='', forceOutput=True)
				progressReporter.outputChannel.write('\n')
			
			readFile.close()
			
		else:
			raise Exception('Checksum called on a location that is neither a file or folder: %s' % location)
	
	elif locationURL.scheme in ['http', 'https']:
		
		if chunkSize is None:
			chunkSize = 1024*100 # 100KiB for urls
		
		try:
			readFile = urllib2.urlopen(location)
		except IOError, error:
			if hasattr(error, 'reason'):
				raise Exception('Unable to connect to remote url: %s got error: %s' % (location, error.reason))
			elif hasattr(error, 'code'):
				raise Exception('Got status code: %s while trying to connect to remote url: %s' % (str(error.code), location))
		
		if readFile == None:
			raise Exception("Unable to open file for checksumming: %s" % location)
		
		# default the filename to the last bit of path of the url
				
		fileName = os.path.basename( urllib.unquote(urlparse.urlparse(readFile.geturl()).path) )
				
		# grab the name of the file and its length from the http headers if avalible
		httpHeader = readFile.info()
		if httpHeader.has_key("content-length"):
			try:
				targetLength = int(httpHeader.getheader("content-length"))
			except:
				pass # 
		
		if httpHeader.has_key("content-disposition"):
			fileName = httpHeader.getheader("content-disposition").strip()
		
		writeTarget = None
		if cacheFolder != None:
			writeTarget = os.path.join(cacheFolder, fileName)
			cacheFolder = writeTarget
		
		if progressReporter is not None:
			if targetLength is not None:
				progressReporter.update(statusMessage="Downloading %s (%s) in chunks of %s: " % (fileName, translateBytes(targetLength), translateBytes(chunkSize)), updateMessage="0%")
			else:
				progressReporter.update(statusMessage="Downloading %s (unknown length) in chunks of %s: " % (fileName, translateBytes(chunkSize)), updateMessage=translateBytes(0))
		
		processedBytes, processSeconds = checksumFileObject(hashGenerator, readFile, fileName, targetLength, copyToPath=writeTarget, chunkSize=chunkSize, progressReporter=progressReporter)
		
		if progressReporter is not None:
			progressReporter.update(statusMessage="Downloaded %s (%s) in %s (%s/sec)" % (fileName, translateBytes(processedBytes), secondsToReadableTime(processSeconds), translateBytes(processedBytes/processSeconds)), updateMessage='')
			progressReporter.outputChannel.write('\n')
		
		readFile.close()
		
	else:
		raise Exception('Checksum called with a location that does not support: %s' % location)
	
	returnValues = {'name':fileName, 'checksum':hashGenerator.hexdigest(), 'checksumType':checksumType}
	
	# Return the location of the local copy if we were asked to
	if outputFolder is not None:
		returnValues["cacheLocation"] = cacheFolder
	
	return returnValues
