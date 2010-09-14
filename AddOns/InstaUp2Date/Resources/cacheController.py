#!/usr/bin/python

import os, re, urlparse, time, urllib, urllib2, hashlib

import pathHelpers, displayTools, checksum
from commonExceptions		import FileNotFoundException

class cacheController:
	
	# ------ class variables
	
	writeableCacheFolder	= None		# writeable folder to put downloads into
	sourceFolders			= []		# paths to folders to search when looking for files
	
	verifiedFiles			= {}		# collection of items that have already been found indexed by checksum
	
	fileNameChecksumRegex	= re.compile('^(.+?/)?(?P<fileName>.*)( (?P<checksumType>\S+)-(?P<checksumValue>[^\.]+))(?P<fileExtension>\.[^\.]+)?$')
	
	# ------ class methods
	
	# ---- cacheFolder methods
	
	@classmethod
	def setCacheFolder(myClass, newCacheFolder):
		# the first cacheFolder is used to store new files, and must be write-able
		
		if newCacheFolder is None:
			raise ValueError('%s\'s setCacheFolder was given None as an input' % myClass.__name__)
		elif not isinstance(newCacheFolder, str):
			raise ValueError('%s\'s setCacheFolder recieved a newCacheFolder value that it did not understand: %s' % (myClass.__name__, newCacheFolder))
		elif not os.path.isdir(newCacheFolder):
			raise ValueError('%s\'s setCacheFolder given a path that was not a valid directory: %s' % (myClass.__name__, newCacheFolder))
		
		# confirm that this path is writeable
		if not os.access(newCacheFolder, os.W_OK):
			raise ValueError('The value given to %s\'s setCacheFolder method must be a write-able folder: %s' % (myClass.__name__, newCacheFolder))
		
		# make sure we have a canonical path
		newCacheFolder = pathHelpers.normalizePath(newCacheFolder, followSymlink=True)
		
		# set the cache folder
		myClass.writeableCacheFolder = newCacheFolder
		
		# make sure it is in the list of source folders
		myClass.addSourceFolders(newCacheFolder)
	
	@classmethod
	def getCacheFolder(myClass):
		if not isinstance(myClass.writeableCacheFolder, str):
			raise RuntimeWarning("The %s class's cacheFolder value was not useable: %s" % (myClass.__name__, str(myClass.writeableCacheFolder)))
		
		return myClass.writeableCacheFolder
	
	@classmethod
	def removeCacheFolder(myClass):
		'''Remove the current class cache folder, usefull mostly in testing'''
		
		myClass.removeSourceFolders(myClass.writeableCacheFolder)
		myClass.writeableCacheFolder = None
	
	# ---- sourceFolder methods
	
	@classmethod
	def addSourceFolders(myClass, newSourceFolders):
		
		# -- sanity check
		if not isinstance(myClass.sourceFolders, list):
			raise RuntimeWarning("The %s class's sourceFolders value was not useable, something has gone wrong prior to this" % myClass.__name__)
		
		foldersToAdd = []
		
		# -- force newSourceFolders to be a list
		if isinstance(newSourceFolders, str):
			foldersToAdd.append(newSourceFolders)
		
		elif hasattr(newSourceFolders, '__iter__'):
			for thisFolder in newSourceFolders:
				if not isinstance(thisFolder, str):
					raise ValueError("One of the items given to %s class's addSourceFolders method was not a string: %s" % (myClass.__name__, str(thisFolder)))
					
				foldersToAdd.append(thisFolder)
		
		else:
			raise ValueError("The value given to %s class's addSourceFolders method was not useable: %s" % (myClass.__name__, str(newSourceFolders)))
		
		# -- process the items
		for thisFolder in foldersToAdd:
			
			# remove file://
			if thisFolder.lower().startswith('file://'):
				thisFolder = thisFolder[len('file://'):]
			
			parsedLocation = urlparse.urlparse(thisFolder)
			
			if parsedLocation.scheme in ['http', 'https']:
				# web caches
				
				# open a connection, and see if we get a responce
				
				try:
					readFile = urllib2.urlopen(thisFolder)
					readFile.close()
				except urllib2.HTTPError, error:
					if error.code in [403]: # these might mean that the directory can't be listed
						myClass.sourceFolders.append(thisFolder)
					else:
						raise Exception('Got status code: %s while trying to connect to remote url: %s' % (str(error.code), thisFolder))
				
				except urllib2.URLError, error:
					# a bad network connection, or url
					raise Exception('Unable to connect to remote url: %s got error: %s' % (thisFolder, error.reason))
				
				# a 200 responce
				myClass.sourceFolders.append(thisFolder)	
			
			elif parsedLocation.scheme == '':
				# local path
				
				if not os.path.isdir(thisFolder):
					raise ValueError("The value given to %s class's addSourceFolders was not a directory as is required: %s" % (myClass.__name__, str(thisFolder)))
				
				# normalize the path
				thisFolder = pathHelpers.normalizePath(thisFolder, followSymlink=True)
				
				if not thisFolder in myClass.sourceFolders:
					myClass.sourceFolders.append(thisFolder)
			
			else:
				raise ValueError("The value given to %s class's addSourceFolders was not useable: %s" % (myClass.__name__, str(thisFolder)))
	
	@classmethod
	def getSourceFolders(myClass):
		if myClass.sourceFolders is None or len(myClass.sourceFolders) == 0:
			raise RuntimeWarning('The %s class\'s cache folders must be setup before getSourceFolders is called' % myClass.__name__)
		
		return myClass.sourceFolders
	
	@classmethod
	def removeSourceFolders(myClass, sourceFoldersToRemove):
		
		# ToDo: think about errors when the items are not in the list
		# ToDo: think about normalizing the paths
		
		foldersToRemove = []
		
		if isinstance(sourceFoldersToRemove, str):
			foldersToRemove.append(sourceFoldersToRemove)
		
		elif hasattr(sourceFoldersToRemove, '__iter__'):
			for thisFolder in sourceFoldersToRemove:
				if isinstance(thisFolder, str):
					foldersToRemove.append(thisFolder)
				else:
					raise ValueError("One of the items given to %s class's removeSourceFolders method was not a string: %s" % (myClass.__name__, str(thisFolder)))
			
		else:
			raise ValueError('removeSourceFolders called with a value it did not understand: ' + sourceFoldersToRemove)
		
		for thisFolder in foldersToRemove:
			if thisFolder in myClass.sourceFolders:
				myClass.sourceFolders.remove(thisFolder)
			
			if thisFolder == myClass.writeableCacheFolder:
				myClass.writeableCacheFolder = None
	
	# ---- item methods
	
	@classmethod
	def findItem(myClass, nameOrLocation, checksumType, checksumValue, displayName=None, additionalSourceFolders=None, progressReporter=True):
		'''Find an item locally, or download it'''
		
		# ---- validate input
		
		# nameOrLocation
		if not isinstance(nameOrLocation, str) and not nameOrLocation is None:
			raise ValueError('findItem requires a string as a nameOrLocation, but got: ' + nameOrLocation)
		if nameOrLocation is not None and nameOrLocation.startswith('file://'):
			nameOrLocation = nameOrLocation[len('file://'):]
		
		# checksumType
		if not isinstance(checksumType, str):
			raise ValueError('findItem requires a string as a checksumType, but got: ' + checksumType)
		
		# checksumValue
		if not isinstance(checksumValue, str):
			raise ValueError('findItem requires a string as a checksumValue, but got: ' + checksumValue)
		
		# displayName
		if not isinstance(displayName, str) and not displayName is None:
			raise ValueError('findItem requires a string or None as a displayName, but got: ' + displayName)
		
		# additionalSourceFolders
		if additionalSourceFolders is None:
			pass # nothing to do
		elif isinstance(additionalSourceFolders, str) and os.path.isdir(additionalSourceFolders):
			pass # nothing to do
		elif hasattr(additionalSourceFolders, '__iter__'):
			# validate that these are all folders
			for thisFolder in additionalSourceFolders:
				if not os.path.isdir(thisFolder):
					raise ValueError('The folder given to findItem as an additionalSourceFolders either did not exist or was not a folder: ' + thisFolder)
		else:
			raise ValueError('Unable to understand the additionalSourceFolders given: ' + str(additionalSourceFolders))
		
		# progressReporter
		if progressReporter is True:
			progressReporter = displayTools.statusHandler(taskMessage='Searching for ' + nameOrLocation)
		elif progressReporter is False:
			progressReporter = None
		
		# ---- start the timer for reporting
		startTime = time.time()
		
		# ---- look localy
		
		# -- absolute path, note: if an absolute path is not found we will error out
		if os.path.isabs(nameOrLocation):
			if progressReporter is not None:
				progressReporter.update(statusMessage=' looking at an absolute location')
			resultPath, reportCompleted = myClass.findItemInCaches(None, checksumType, checksumValue, displayName, additionalSourceFolders, progressReporter)
			if resultPath is not None:
				# note: if there is nothing at this path, we will get an error before this
				if progressReporter is not None and reportCompleted is False:
					progressReporter.update(statusMessage=' found at an absolute location and verified in %s' % (displayTools.secondsToReadableTime(time.time() - startTime)))
					progressReporter.finishLine()
				return resultPath
		
		# -- try relative path, include remote caches
		parsedNameOrLocation = urlparse.urlparse(nameOrLocation)
		if parsedNameOrLocation.scheme == '' and nameOrLocation.count(os.sep) > 0:
			if progressReporter is not None:
				progressReporter.update(statusMessage=' looking at relative locations')
			resultPath, reportCompleted = myClass.findItemInCaches(nameOrLocation, checksumType, checksumValue, displayName, additionalSourceFolders, progressReporter, includeRemoteCaches=True)
			if resultPath is not None:
				
				# note: if there is nothing at this path, we will get an error before this
				if progressReporter is not None and reportCompleted is False:
					progressReporter.update(statusMessage=' found at a relative location and verified in %s' % (displayTools.secondsToReadableTime(time.time() - startTime)))
					progressReporter.finishLine()
				return resultPath
		
		# -- based on checksum
		
		# first see if we already found this item
		# check the already verified items for this checksum
		checksumString = '%s-%s' % (checksumType, checksumValue)
		if checksumString in myClass.verifiedFiles:
			if progressReporter is not None:
				progressReporter.update(statusMessage=' found previously')
				progressReporter.finishLine()
			return myClass.verifiedFiles[checksumString]
		
		# look through the caches
		if progressReporter is not None:
			progressReporter.update(statusMessage=' looking based on checksum')
		resultPath, reportCompleted = myClass.findItemInCaches(None, checksumType, checksumValue, displayName, additionalSourceFolders, progressReporter)
		if resultPath is not None:
			myClass.addItemToVerifiedFiles(checksumString, resultPath)
			if progressReporter is not None and reportCompleted is False:
				progressReporter.update(statusMessage=' found based on checksum and verified in %s' % (displayTools.secondsToReadableTime(time.time() - startTime)))
				progressReporter.finishLine()
			return resultPath
		
		# -- based on name guessed from nameOrLocation, include remote caches
		locallyGuessedName = None
		if progressReporter is not None:
			progressReporter.update(statusMessage=' looking based on guessed name and verified in %s' % (displayTools.secondsToReadableTime(time.time() - startTime)))
		if parsedNameOrLocation.scheme in ['http', 'https']:
			locallyGuessedName = os.path.basename(parsedNameOrLocation.path)
		else:
			locallyGuessedName = os.path.basename(nameOrLocation)
		resultPath, reportCompleted = myClass.findItemInCaches(locallyGuessedName, checksumType, checksumValue, displayName, additionalSourceFolders, progressReporter, includeRemoteCaches=True)
		if resultPath is not None:
			myClass.addItemToVerifiedFiles(checksumString, resultPath)
			if progressReporter is not None and reportCompleted is False:
				progressReporter.update(statusMessage=' found based on guessed name and verified in %s' % (displayTools.secondsToReadableTime(time.time() - startTime)))
				progressReporter.finishLine()
			return resultPath
		
		# -- based on display name
		if displayName is not None:
			if progressReporter is not None:
				progressReporter.update(statusMessage=' looking based on display name')
			resultPath, reportCompleted = myClass.findItemInCaches(displayName, checksumType, checksumValue, displayName, additionalSourceFolders, progressReporter)
			if resultPath is not None:
				myClass.addItemToVerifiedFiles(checksumString, resultPath)
				if progressReporter is not None and reportCompleted is False:
					progressReporter.update(statusMessage=' found based on display name and verified in %s' % (displayTools.secondsToReadableTime(time.time() - startTime)))
					progressReporter.finishLine()
				return resultPath
		
		# ---- look remotely over http/https
		if parsedNameOrLocation.scheme in ['http', 'https']:
			
			remoteGuessedName = locallyGuessedName
			
			# -- open a connection and get information to guess the name
			
			# open the connection
			readFile = None
			try:
				readFile = urllib2.urlopen(nameOrLocation)
			except IOError, error:
				if hasattr(error, 'reason'):
					raise Exception('Unable to connect to remote url: %s got error: %s' % (nameOrLocation, error.reason))
				elif hasattr(error, 'code'):
					raise Exception('Got status code: %s while trying to connect to remote url: %s' % (str(error.code), nameOrLocation))
			
			# try reading out the content-disposition header
			httpHeader = readFile.info()
			if httpHeader.has_key("content-disposition"):
				remoteGuessedName = httpHeader.getheader("content-disposition").strip()
				
				if remoteGuessedName is not locallyGuessedName:
					if progressReporter is not None:
						progressReporter.update(statusMessage=' looking based on name from content-disposition')
					resultPath, reportCompleted = myClass.findItemInCaches(remoteGuessedName, checksumType, checksumValue, displayName, additionalSourceFolders, progressReporter, includeRemoteCaches=True)
					if resultPath is not None:
						if progressReporter is not None and reportCompleted is False:
							progressReporter.update(statusMessage=' found based on name from content-disposition and verified in %s' % (displayTools.secondsToReadableTime(time.time() - startTime)))
							progressReporter.finishLine()
						readFile.close()
						return resultPath
			
			# try the name in the final URL
			secondRemoteGuessedName = os.path.basename( urllib.unquote(urlparse.urlparse(readFile.geturl()).path) )
			if secondRemoteGuessedName not in [locallyGuessedName, remoteGuessedName]:
				if progressReporter is not None:
					progressReporter.update(statusMessage=' looking based on name in final URL')
				resultPath, reportCompleted = myClass.findItemInCaches(secondRemoteGuessedName, checksumType, checksumValue, displayName, additionalSourceFolders, progressReporter, includeRemoteCaches=True)
				if resultPath is not None:
					if progressReporter is not None and reportCompleted is False:
						progressReporter.update(statusMessage=' found based on name in final URL and verified in %s' % (displayTools.secondsToReadableTime(time.time() - startTime)))
						progressReporter.finishLine()
					readFile.close()
					return resultPath
			
			# -- download file
			
			# try to get the expected file length
			expectedLength = None
			if httpHeader.has_key("content-length"):
				try:
					expectedLength = int(httpHeader.getheader("content-length"))
				except:
					pass
			
			if progressReporter is not None:
				if expectedLength is None:
					progressReporter.update(statusMessage=' downloading ')
				else:
					progressReporter.update(statusMessage=' downloading %s ' % displayTools.bytesToRedableSize(expectedLength))
			
			hashGenerator = hashlib.new(checksumType)
			downloadTargetPath = os.path.join(myClass.getCacheFolder(), os.path.splitext(secondRemoteGuessedName)[0] + " " + checksumString + os.path.splitext(secondRemoteGuessedName)[1])
			processedBytes, processSeconds = checksum.checksumFileObject(hashGenerator, readFile, secondRemoteGuessedName, expectedLength, copyToPath=downloadTargetPath, progressReporter=progressReporter)
			
			if hashGenerator.hexdigest() != checksumValue:
				os.unlink(downloadTargetPath)
				readFile.close()
				raise FileNotFoundException("Downloaded file did not match checksum: %s (%s vs. %s)" % (nameOrLocation, hashGenerator.hexdigest(), checksumValue))
			
			if progressReporter is not None:
				progressReporter.update(statusMessage=' downloaded and verified %s in %s (%s/sec)' % (displayTools.bytesToRedableSize(processedBytes), displayTools.secondsToReadableTime(time.time() - startTime), displayTools.bytesToRedableSize(processedBytes/processSeconds)))
				progressReporter.finishLine()
			
			myClass.addItemToVerifiedFiles(checksumString, downloadTargetPath)
			readFile.close()
			return downloadTargetPath
		
		# if we have not found anything, then we are out of luck
		raise FileNotFoundException('Could not locate the item: ' + nameOrLocation)
	
	@classmethod
	def findItemInCaches(myClass, nameOrLocation, checksumType, checksumValue, displayName=None, additionalSourceFolders=None, progressReporter=True, includeRemoteCaches=False): 
		
		# ---- validate input
		
		# nameOrLocation
		if not isinstance(nameOrLocation, str) and not nameOrLocation is None:
			raise ValueError('findItem requires a string or none as a nameOrLocation, but got: ' + nameOrLocation)
		if nameOrLocation is not None and nameOrLocation.startswith('file://'):
			nameOrLocation = nameOrLocation[len('file://'):]
		
		if nameOrLocation is not None and urlparse.urlparse(nameOrLocation).scheme != '':
			raise ValueError('findItemInCaches only works on file paths or names, got: ' + str(nameOrLocation))
		
		# checksumType
		if not isinstance(checksumType, str):
			raise ValueError('findItem requires a string as a checksumType, but got: ' + checksumType)
		
		# checksumValue
		if not isinstance(checksumValue, str):
			raise ValueError('findItem requires a string as a checksumValue, but got: ' + checksumValue)
		
		# displayName
		if not isinstance(displayName, str) and not displayName is None:
			raise ValueError('findItem requires a string or None as a displayName, but got: ' + displayName)
		
		# additionalSourceFolders
		foldersToSearch = myClass.getSourceFolders()
		if additionalSourceFolders is None:
			pass # nothing to do
		elif isinstance(additionalSourceFolders, str) and os.path.isdir(additionalSourceFolders):
			foldersToSearch.append(pathHelpers.normalizePath(additionalSourceFolders, followSymlink=True))
		elif hasattr(additionalSourceFolders, '__iter__'):
			# validate that these are all folders
			for thisFolder in additionalSourceFolders:
				if not os.path.isdir(thisFolder):
					raise ValueError('The folder given to findItemInCaches as an additionalSourceFolders either did not exist or was not a folder: ' + thisFolder)
				foldersToSearch.append(pathHelpers.normalizePath(thisFolder, followSymlink=True))
		else:
			raise ValueError('Unable to understand the additionalSourceFolders given: ' + str(additionalSourceFolders))
		
		# progressReporter
		if progressReporter is True:
			progressReporter = displayTools.statusHandler(statusMessage='Searching cache folders for ' + nameOrLocation)
		elif progressReporter is False:
			progressReporter = None
		
		# ---- search for the items
		
		# absolute paths
		if nameOrLocation is not None and os.path.isabs(nameOrLocation):
			if os.path.exists(nameOrLocation):
				if checksumValue == checksum.checksum(nameOrLocation, checksumType=checksumType, progressReporter=progressReporter)['checksum']:
					return nameOrLocation, False
				else:
					raise FileNotFoundException('The item at the path given does not match the checksum given: ' + nameOrLocation)
			else:
				raise FileNotFoundException('No file/folder existed at the absolute path: ' + nameOrLocation)
		
		# relative path
		elif nameOrLocation is not None and os.path.exists(nameOrLocation):
			if checksumValue == checksum.checksum(nameOrLocation, checksumType=checksumType, progressReporter=progressReporter)['checksum']:
				return pathHelpers.normalizePath(nameOrLocation, followSymlink=True), False
		
		# cache folders
		for thisCacheFolder in foldersToSearch:
			
			parsedLocation = urlparse.urlparse('')
			if nameOrLocation is not None:
				parsedLocation = urlparse.urlparse(thisCacheFolder)
			
			if parsedLocation.scheme in ['http', 'https'] and includeRemoteCaches is False:
				continue
			
			elif parsedLocation.scheme in ['http', 'https'] and includeRemoteCaches is True:
				
				# -- try different paths on the server
				urlsToTry = {}
				
				(scheme, netloc, path, params, query, fragment) = urlparse.urlparse(thisCacheFolder)
				
				# simple name
				urlsToTry[urlparse.urlunparse((scheme, netloc, os.path.join(path, nameOrLocation), params, query, fragment))] = True
				urlsToTry[urlparse.urlunparse((scheme, netloc, os.path.join(path, urllib.quote(nameOrLocation)), params, query, fragment))] = True
				
				# name including checksum
				nameWithChecksum = os.path.splitext(nameOrLocation)[0] + " " + checksumType + "-" + checksumValue + os.path.splitext(nameOrLocation)[1]
				urlsToTry[urlparse.urlunparse((scheme, netloc, os.path.join(path, nameWithChecksum), params, query, fragment))] = True
				urlsToTry[urlparse.urlunparse((scheme, netloc, os.path.join(path, urllib.quote(nameWithChecksum)), params, query, fragment))] = True
				
				for thisURL in urlsToTry.keys():
					try:
						readFile = urllib2.urlopen(thisURL)
					except IOError, error:
						continue
					
					remoteGuessedName	= os.path.basename(urllib.unquote(urlparse.urlparse(thisURL).path))
					targetFileName		= remoteGuessedName
					if checksumType + "-" + checksumValue not in targetFileName:
						targetFileName = os.path.splitext(remoteGuessedName)[0] + " " + checksumType + "-" + checksumValue + os.path.splitext(remoteGuessedName)[1]
					
					# try to get the expected file length
					httpHeader = readFile.info()
					expectedLength = None
					if httpHeader.has_key("content-length"):
						try:
							expectedLength = int(httpHeader.getheader("content-length"))
						except:
							pass
					
					if progressReporter is not None:
						if expectedLength is None:
							progressReporter.update(statusMessage=' downloading from local web cache ')
						else:
							progressReporter.update(statusMessage=' downloading %s from local web cache ' % displayTools.bytesToRedableSize(expectedLength))
					
					# download file
					hashGenerator = hashlib.new(checksumType)
					startTime = time.time()
					targetFilePath = os.path.join(myClass.getCacheFolder(), targetFileName)
					processedBytes, processSeconds = checksum.checksumFileObject(hashGenerator, readFile, remoteGuessedName, expectedLength, copyToPath=targetFilePath, progressReporter=progressReporter)
					
					if hashGenerator.hexdigest() != checksumValue:
						os.unlink(targetFilePath)
					
					else:
						if progressReporter is not None:
							progressReporter.update(statusMessage=' downloaded from local web cache and verified %s in %s (%s/sec)' % (displayTools.bytesToRedableSize(processedBytes), displayTools.secondsToReadableTime(time.time() - startTime), displayTools.bytesToRedableSize(processedBytes/processSeconds)))
							progressReporter.finishLine()
						
						myClass.addItemToVerifiedFiles('%s-%s' % (checksumType, checksumValue), targetFilePath)
						readFile.close()
						return targetFilePath, True
					
					readFile.close()
			
			elif parsedLocation.scheme == '':
			
				# relative paths from the source folders
				if nameOrLocation is not None and nameOrLocation.count(os.sep) > 0 and os.path.exists(os.path.join(thisCacheFolder, nameOrLocation)):
					if checksumValue == checksum.checksum(os.path.join(thisCacheFolder, nameOrLocation), checksumType=checksumType, progressReporter=progressReporter)['checksum']:
						return pathHelpers.normalizePath(os.path.join(thisCacheFolder, nameOrLocation), followSymlink=True), False
				
				# walk up through the whole set
				for currentFolder, dirs, files in os.walk(thisCacheFolder, topdown=True):
					
					# check each file to see if it is what we are looking for
					for thisItemPath, thisItemName in [[os.path.join(currentFolder, internalName), internalName] for internalName in (files + dirs)]:
						
						# checksum in name
						fileNameSearchResults = myClass.fileNameChecksumRegex.search(thisItemName)
						
						nameChecksumType = None
						nameChecksumValue = None
						if fileNameSearchResults is not None:
							nameChecksumType = fileNameSearchResults.group('checksumType')
							nameChecksumValue = fileNameSearchResults.group('checksumValue')
						
							if nameChecksumType is not None and nameChecksumType.lower() == checksumType.lower() and nameChecksumValue is not None and nameChecksumValue == checksumValue:
								if checksumValue == checksum.checksum(thisItemPath, checksumType=checksumType, progressReporter=progressReporter)['checksum']:
									return thisItemPath, False
						
						# file name
						if nameOrLocation is not None:
							if nameOrLocation in [thisItemName, os.path.splitext(thisItemName)[0]] or os.path.splitext(nameOrLocation)[0] in [thisItemName, os.path.splitext(thisItemName)[0]]:
								if checksumValue == checksum.checksum(thisItemPath, checksumType=checksumType, progressReporter=progressReporter)['checksum']:
									return thisItemPath, False
						
						# don't decend into folders that look like bundles or sparce dmg's
						if os.path.isdir(thisItemPath):
							if os.listdir(thisItemPath) == ["Contents"] or os.listdir(thisItemPath) == ["Info.bckup", "Info.plist", "bands", "token"]:
								dirs.remove(thisItemName)
			else:
				raise ValueError('The cache folder "%s" was not a format that findItemInCaches understood' % thisCacheFolder)
			
		return None, False
	
	@classmethod
	def addItemToVerifiedFiles(myClass, checksumString, itemPath):
		
		if checksumString.count('-') != 1:
			raise ValueError('Checksum string does not look valid: ' + checksumString)
		
		if not os.path.exists(itemPath):
			raise ValueError('Item does not exist: ' + itemPath)
		
		myClass.verifiedFiles[checksumString] = itemPath