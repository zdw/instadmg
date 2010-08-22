#!/usr/bin/env python

import os, time, hashlib, urllib, urllib2, urlparse, stat, tempfile, shutil

from displayTools import bytesToRedableSize, secondsToReadableTime, statusHandler
from tempFolderManager import tempFolderManager

def checksumFileObject(hashFileObject, targetFileObject, targetFileName, expectedLength, chunkSize=None, copyToPath=None, progressReporter=None):
	
	# todo: sanity check the input
	assert hasattr(targetFileObject, "read"), "The target file object does not look useable"
	
	if progressReporter in [None, False]:
		progressReporter = None
	elif not isinstance(progressReporter, statusHandler):
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
		if expectedLength is None:
			progressReporter.update(progressTemplate='%(valueInBytes)s (%(recentRateInBytes)s)', value=0)
		else:
			progressReporter.update(progressTemplate='%(progressPercentage)i%% (%(recentRateInBytes)s)', expectedLength=expectedLength, value=0)
	
	while thisChunkSize > 0:
		thisChunk = targetFileObject.read(chunkSize)
		thisChunkSize = len(thisChunk)
		hashFileObject.update(thisChunk)
		
		processedLength += thisChunkSize
		
		if progressReporter is not None:
			progressReporter.update(value=processedLength)
		
		if writeFileObject != None:
			writeFileObject.write(thisChunk)
	
	if writeFileObject != None:
		writeFileObject.close()
	
	return (processedLength, time.time() - startReportTime)


def checksum(location, tempFolderPrefix="InstaDMGtemp", checksumType="sha1", displayName=None, outputFolder=None, checksumInFileName=True, chunkSize=None, progressReporter=True):
	'''Return the checksum of a given file or folder'''
	
	startReportTime = time.time()
	
	# validate input
	if location is None:
		raise Exception('Checksum called with a empty file location')
	if checksumType is None:
		raise Exception('Checksum called with a empty checksum type')
	if outputFolder is not None and not os.path.isdir(outputFolder):
		raise Exception('The output folder given does not exist, or is not a folder: ' + outputFolder)
	
	# make sure that the location is a string
	location = str(location)
	
	# confirm that hashlib supports the hash type:
	try:
		hashlib.new(checksumType)
	except ValueError:
		raise Exception("Hash type: %s is not supported by hashlib" % checksumType)
	
	# if a local copy is made, this will house the location
	localCopyPath = None
	
	if outputFolder is not None:
		# make sure we have an absolute path to it
		outputFolder = os.path.realpath(os.path.normpath(outputFolder))
	
	# warm up the checksummer
	hashGenerator = hashlib.new(checksumType)
	
	# get rid of file:// urls
	if location.startswith('file://'):
		location = location[len('file://'):]
	
	locationURL = urlparse.urlparse(location)
	
	if displayName is None:
		if locationURL.scheme in ['http', 'https']:
			displayName = os.path.basename(locationURL.path)
		else:
			displayName = os.path.basename(location)
	
	# get the progress reporter ready
	if progressReporter is True:
		# create a statusHandler to handle this
		if locationURL.scheme in ['http', 'https']:
			progressReporter = statusHandler(taskMessage="Downloading %s: " % displayName)
		else:
			progressReporter = statusHandler(taskMessage="Checksumming %s: " % displayName)
	elif progressReporter in [False, None]:
		progressReporter = None # need to be consistent
	elif not isinstance(progressReporter, statusHandler):
		raise Exception('Unable to understand what the progressReporter is: ' + str(progressReporter))
	
	if locationURL.scheme is '':
		# a local path, check if it is a folder
		
		# make sure we have the canonical location
		location = os.path.realpath(os.path.normpath(os.path.expanduser(location)))
		
		fileName = os.path.basename(location)
		
		if chunkSize is None:
			chunkSize = 1*1024*1024 # 1 MiB chunks for local files
		
		if not os.path.exists(location):
			raise Exception('Checksum called with a file location that does not exist: %s' % location)
		
		elif os.path.isdir(location):
			
			if outputFolder is not None:
				# validate outputFolder if there is one
				if os.path.samefile(location, outputFolder):
					raise ValueError('The output folder (%s) can not be the source item (%s)' % (outputFolder, location))
				if location.startswith(outputFolder + "/"):
					raise ValueError('The output folder (%s) can not be inside the source item (%s)' % (outputFolder, location))
				if os.path.samefile(os.path.dirname(location), outputFolder):
					raise ValueError('The output folder (%s) can not the the same as the source folder (%s)' % (outputFolder, os.path.dirname(location)))
				
				# create a temporary file until we get the checksum
				localCopyPath = tempfile.mkdtemp(prefix='checksumTempFolder.', dir=outputFolder)
				# register it with the tempFolderManager class so it will get cleaned up if something goes wrong
				tempFolderManager.addManagedItem(localCopyPath)
			
			if progressReporter is not None:
				progressReporter.update(statusMessage="building file list ", progressTemplate="%(value)i items", value=0)
			
			# get a quick count
			itemCount = 0
			for thisFolder, subFolders, subFiles in os.walk(location):
				
				for thisFile in subFiles:
					thisFilePath = os.path.join(thisFolder, thisFile)
					# note: we skip anything that is not a link or a file (ie: /dev)
					if os.path.islink(thisFilePath) or os.path.isfile(thisFilePath):
						itemCount += 1
				
				for thisFolder in subFolders:
					itemCount += 1
				
				if progressReporter is not None:
					progressReporter.update(value=itemCount)
			
			# change the status message
			if progressReporter is not None:
				progressReporter.update(statusMessage="checksumming item ", progressTemplate="%(value)i of %(expectedLength)i (%(progressPercentage)i%%)", expectedLength=itemCount, value=0)
			
			# process the items
			processedCount = 0
			for processFolder, subFolders, subFiles in os.walk(location):
				
				for thisFile in subFiles:
					thisFilePath = os.path.join(processFolder, thisFile)
					relativeFilePath = os.path.join(processFolder.replace(location, '', 1), thisFile)
					if os.path.isabs(relativeFilePath):
						relativeFilePath = relativeFilePath[1:]
					
					if os.path.islink(thisFilePath):
						if localCopyPath is not None:
							os.symlink(os.readlink(thisFilePath), os.path.join(localCopyPath, relativeFilePath))
						
						hashGenerator.update("softlink %s to %s" % (os.readlink(thisFilePath), relativeFilePath))
						
					elif os.path.isfile(thisFilePath):
						
						readFile = open(thisFilePath)
						if readFile == None:
							raise Exception("Unable to open file for checksumming: " + thisFilePath)
						
						targetLength = os.stat(thisFilePath)[stat.ST_SIZE]
						writeTarget = None
						if localCopyPath is not None:
							writeTarget = os.path.join(localCopyPath, relativeFilePath)
						
						# add the path to the checksum
						hashGenerator.update("file " + relativeFilePath)
						
						checksumFileObject(hashGenerator, readFile, thisFile, targetLength, chunkSize, copyToPath=writeTarget)
						readFile.close()
												
					else:
						continue # skip anything that is not a link or a file (ie: /dev)
					
					processedCount += 1
					if progressReporter is not None:
						progressReporter.update(value=processedCount)
				
				for thisFolder in subFolders:
					thisFolderPath = os.path.join(processFolder, thisFolder)
					relativeFolderPath = os.path.join(processFolder.replace(location, '', 1), thisFolder)
					if os.path.isabs(relativeFolderPath):
						relativeFolderPath = relativeFolderPath[1:]
					
					if os.path.islink(thisFolderPath):
						if localCopyPath is not None:
							os.symlink(os.readlink(thisFolderPath), os.path.join(localCopyPath, relativeFolderPath))
						
						hashGenerator.update("softlink %s to %s" % (os.readlink(thisFolderPath), relativeFolderPath))
					
					else:
						if localCopyPath != None:
							os.mkdir( os.path.join(localCopyPath, relativeFolderPath) )
						
						# add this to the hash
						hashGenerator.update("folder %s" % relativeFolderPath)
					
					processedCount += 1
					if progressReporter is not None:
						progressReporter.update(value=processedCount)
			
			if progressReporter is not None:
				progressReporter.update(statusMessage='checksummed %i items in %s' % (processedCount, secondsToReadableTime(time.time() - startReportTime)))
			
			if localCopyPath is not None:
				# check if there is already something there
				targetOutputPath = os.path.join(outputFolder, fileName)
				if os.path.exists(targetOutputPath):
					if os.path.islink(targetOutputPath) or os.path.isfile(targetOutputPath):
						os.unlink(targetOutputPath)
					else:
						shutil.rmtree(targetOutputPath) # ToDo: handle errors
				
				# move the folder into place
				os.rename(localCopyPath, targetOutputPath)
				
				# unregister it from tempFolderManager
				tempFolderManager.removeManagedItem(localCopyPath)
				
				# change the localCopyPath to reflect the new location
				localCopyPath = os.path.basename(targetOutputPath)
			
		elif os.path.isfile(location):
			
			fileName = os.path.basename(location)
			readFile = open(location)
			if readFile == None:
				raise Exception("Unable to open file for checksumming: %s" % location)
			
			targetLength = os.stat(location)[stat.ST_SIZE]
			
			if outputFolder is not None:
				# create a temporary file until we get the checksum
				localCopyFile, localCopyPath = tempfile.mkstemp(prefix='checksumTempFile.', dir=outputFolder)
				os.close(localCopyFile)
				# register it with the tempFolderManager class so it will get cleaned up if something goes wrong
				tempFolderManager.addManagedItem(localCopyPath)
			
			if progressReporter is not None:
				progressReporter.update(statusMessage="checksumming: ", progressTemplate='%(progressPercentage)i%% (%(recentRateInBytes)s)', expectedLength=targetLength, value=0)
			
			processedBytes, processSeconds = checksumFileObject(hashGenerator, readFile, os.path.basename(location), targetLength, chunkSize=chunkSize, copyToPath=localCopyPath, progressReporter=progressReporter)
			
			if progressReporter is not None:
				progressReporter.update(statusMessage='checksummed (%s) in %s (%s/sec)' % (bytesToRedableSize(processedBytes), secondsToReadableTime(processSeconds), bytesToRedableSize(processedBytes/processSeconds)))
			
			readFile.close()
			
			# if we are keeping a local copy, move it into place
			if localCopyPath is not None:
				# change the file name to the real one, including the checksum if not suppressed
				realFilePath = None
				if checksumInFileName is True:
					realFilePath = os.path.join(outputFolder, os.path.splitext(fileName)[0] + " " + checksumType + "-" + hashGenerator.hexdigest() + os.path.splitext(fileName)[1])
				else:
					realFilePath = os.path.join(outputFolder, fileName)
				
				# try to move the item to the proper name
				os.rename(localCopyPath, realFilePath) # ToDo: proper error handling for all of the bad things that can happen here
				
				# unregister it from tempFolderManager
				tempFolderManager.removeManagedItem(localCopyPath)
				
				# change the localCopyPath to reflect the new location, and that it will now be pulled from the cache
				localCopyPath = os.path.basename(realFilePath)
			
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
		if fileName in [None, '']:
			fileName = 'No_filename_provided'
		targetLength = None
		
		# grab the name of the file and its length from the http headers if avalible
		httpHeader = readFile.info()
		if httpHeader.has_key("content-length"):
			try:
				targetLength = int(httpHeader.getheader("content-length"))
			except:
				pass # 
		
		if httpHeader.has_key("content-disposition"):
			fileName = httpHeader.getheader("content-disposition").strip()
		
		if outputFolder is not None:
			# create a temporary file until we get the checksum
			localCopyFile, localCopyPath = tempfile.mkstemp(prefix='checksumTempFile.', dir=outputFolder)
			os.close(localCopyFile)
			# register it with the tempFolderManager class so it will get cleaned up if something goes wrong
			tempFolderManager.addManagedItem(localCopyPath)
		
		if progressReporter is not None:
			if targetLength is not None:
				progressReporter.update(statusMessage="downloading: ", progressTemplate='%(progressPercentage)i%% (%(recentRateInBytes)s)', expectedLength=targetLength, value=0)
			else:
				progressReporter.update(statusMessage="downloading: ", progressTemplate='%(valueInBytes)s (%(recentRateInBytes)s)', value=0)
		
		processedBytes, processSeconds = checksumFileObject(hashGenerator, readFile, fileName, targetLength, copyToPath=localCopyPath, chunkSize=chunkSize, progressReporter=progressReporter)
		
		if progressReporter is not None:
			progressReporter.update(statusMessage=" downloaded %s (%s) in %s (%s/sec)" % (fileName, bytesToRedableSize(processedBytes), secondsToReadableTime(processSeconds), bytesToRedableSize(processedBytes/processSeconds)))
		
		if localCopyPath is not None:
			# change the file name to the real one, including the checksum if not suppressed
			realFilePath = None
			if checksumInFileName is True:
				realFilePath = os.path.join(outputFolder, os.path.splitext(fileName)[0] + " " + checksumType + "-" + hashGenerator.hexdigest() + os.path.splitext(fileName)[1])
			else:
				realFilePath = os.path.join(outputFolder, fileName)
			
			# try to move the item to the proper name
			os.rename(localCopyPath, realFilePath) # ToDo: proper error handling for all of the bad things that can happen here
			
			# unregister it from tempFolderManager
			tempFolderManager.removeManagedItem(localCopyPath)
			
			# change the localCopyPath to reflect the new location
			localCopyPath = realFilePath
		
		readFile.close()
		
	else:
		raise Exception('Checksum called with a location that does not support: %s' % location)
	
	returnValues = {'name':fileName, 'checksum':hashGenerator.hexdigest(), 'checksumType':checksumType}
	
	# Return the location of the local copy if we were asked to
	if outputFolder is not None:
		returnValues['cacheLocation'] = localCopyPath
	
	return returnValues
