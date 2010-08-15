#!/usr/bin/python

import os, re, time
import hashlib, urlparse, urllib, urllib2

from checksum				import checksumFileObject, checksum
from displayTools			import statusHandler, translateBytes, secondsToReadableTime
from commonExceptions		import FileNotFoundException


class installerPackage:
	"This class represents a .pkg installer, and does much of the work."
		
	#---------------------Class Variables-----------------------------
	
	cacheFolder				= None		# the path to a writeable folder
	sourceFolders			= []		# paths to folders to search when looking for files
	
	verifiedFiles			= {}
	
	fileNameChecksumRegex	= re.compile('^(.+?/)?(?P<fileName>.*)( (?P<checksumType>\S+)-(?P<checksumValue>[^\.]+))(?P<fileExtension>\.[^\.]+)?$')
	
	#--------------------- Class Methods -----------------------------
	
	# ToDo: manage the cache size
	
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
		newCacheFolder = os.path.abspath(os.path.realpath(newCacheFolder))
		
		# set the cache folder
		myClass.cacheFolder = newCacheFolder
		
		# make sure it is in the list of source folders
		myClass.addSourceFolders(newCacheFolder)
	
	@classmethod
	def getCacheFolder(myClass):
		if not isinstance(myClass.cacheFolder, str):
			raise RuntimeWarning("The %s class's cacheFolder value was not useable: %s" % (myClass.__name__, str(myClass.cacheFolder)))
		
		return myClass.cacheFolder
	
	@classmethod
	def removeCacheFolder(myClass):
		'''Remove the current class cache folder, usefull mostly in testing'''
		
		myClass.removeSourceFolders(myClass.cacheFolder)
		myClass.cacheFolder = None
	
	@classmethod
	def addSourceFolders(myClass, newSourceFolders):
		
		# check to make sure that the class is in a useable state
		if not isinstance(myClass.sourceFolders, list):
			raise RuntimeWarning("The %s class's sourceFolders value was not useable, something has gone wrong prior to this: %s" % (myClass.__name__, str(myClass.cacheFolder)))
		
		foldersToAdd = []
		
		# process everything into a neet list
		if isinstance(newSourceFolders, str):
			foldersToAdd.append(newSourceFolders)
		
		elif hasattr(newSourceFolders, '__iter__'):
			for thisFolder in newSourceFolders:
				if not isinstance(thisFolder, str):
					raise ValueError("One of the items given to %s class's addSourceFolders method was not a string: %s" % (myClass.__name__, str(thisFolder)))
					
				foldersToAdd.append(thisFolder)
		
		else:
			raise ValueError("The value given to %s class's addSourceFolders method was not useable: %s" % (myClass.__name__, str(newSourceFolders)))
		
		# process the items in the list
		for thisFolder in foldersToAdd:
			if not os.path.isdir(thisFolder):
				raise ValueError("The value given to %s class's addSourceFolders was not useable: %s" % (myClass.__name__, str(newSourceFolders)))
			
			# normalize the path
			thisFolder = os.path.abspath(os.path.realpath(thisFolder))
				
			if not thisFolder in myClass.sourceFolders:
				myClass.sourceFolders.append(thisFolder)
	
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
			
			if thisFolder == myClass.cacheFolder:
				myClass.cacheFolder = None
	
	@classmethod
	def findItem(myClass, nameOrLocation, checksumType, checksumValue, displayName=None, additionalSourceFolders=None, progressReporter=True):
		'''Look through the caches for this file'''
		
		startTime = time.time()
		
		if not isinstance(checksumType, str) or not isinstance(checksumValue, str):
			raise ValueError('Recieved a value for the checksumType or checksumValue that was not useable: %s:%s' % (checksumType, checksumValue))
		
		if displayName is None:
			displayName = os.path.basename(nameOrLocation)
		
		# setup the reporter if needed
		if progressReporter is True:
			progressReporter = statusHandler(taskMessage="\t" + displayName + " ")
		
		# check the already verified items for this checksum
		if '%s:%s' % (checksumType, checksumValue) in myClass.verifiedFiles:
			itemPath = myClass.verifiedFiles['%s:%s' % (checksumType, checksumValue)]
			
			if progressReporter is not None:
				#progressReporter.update(statusMessage='found previously at: %s' % itemPath)
				progressReporter.update(statusMessage='found previously')
				progressReporter.finishLine()
			
			return itemPath
		
		# remove file:// if it is the nameOrLocation
		if nameOrLocation.startswith('file://'):
			nameOrLocation = nameOrLocation[len('file://'):]
		
		parsedNameOrLocation = urlparse.urlparse(nameOrLocation)
		
		# fail out if we don't support this method
		if parsedNameOrLocation.scheme not in ['', 'http', 'https']:
			raise ValueError('findItem can not process urls types other than http, https, or file')
		
		# check if this is an absolute path, or one relative to pwd
		if parsedNameOrLocation.scheme is '' and os.path.exists(nameOrLocation):
			if checksumValue == checksum(nameOrLocation, checksumType=checksumType, progressReporter=progressReporter)['checksum']:
				if progressReporter is not None:
					progressReporter.update(statusMessage='found by path and verified in %s: %s' % (secondsToReadableTime(time.time() - startTime), itemPath))
					progressReporter.update(statusMessage='found by path and verified in %s' % (secondsToReadableTime(time.time() - startTime)))
					progressReporter.finishLine()
				
				return os.path.realpath(os.path.abspath(nameOrLocation))
		
		# look for the item in the cache by name
		workingName = None
		if parsedNameOrLocation.scheme in ['http', 'https']:
			workingName = os.path.basename(parsedNameOrLocation.path)
		else:
			workingName = os.path.basename(nameOrLocation)
		if progressReporter is not None:
			progressReporter.update(statusMessage='looking in the source folders by guessed name and checksum')
		itemPath = myClass._findItemInCaches(workingName, checksumType, checksumValue, displayName=displayName, additionalSourceFolders=additionalSourceFolders, progressReporter=progressReporter)
		if itemPath is not None:
			# add the item to the found items
			myClass.verifiedFiles['%s:%s' % (checksumType, checksumValue)] = itemPath
			
			if progressReporter is not None:
				#progressReporter.update(statusMessage='found by name or checksum and verified in %s: %s' % (secondsToReadableTime(time.time() - startTime), itemPath))
				progressReporter.update(statusMessage='found by name or checksum and verified in %s' % (secondsToReadableTime(time.time() - startTime)))
				progressReporter.finishLine()
			return itemPath
		
		if parsedNameOrLocation.scheme in ['http', 'https']:
			
			if progressReporter is not None:
				progressReporter.update(statusMessage='checking for a name from the server')
			
			# open a connection to try and figure out the file name from it
			try:
				readFile = urllib2.urlopen(nameOrLocation)
			except IOError, error:
				if hasattr(error, 'reason'):
					raise Exception('Unable to connect to remote url: %s got error: %s' % (nameOrLocation, error.reason))
				elif hasattr(error, 'code'):
					raise Exception('Got status code: %s while trying to connect to remote url: %s' % (str(error.code), nameOrLocation))
			
			if readFile is None:
				raise Exception("Unable to open file for checksumming: %s" % nameOrLocation)
			
			workingUrlName = workingName
			
			# try reading out the content-disposition header
			httpHeader = readFile.info()
			if httpHeader.has_key("content-disposition"):
				workingUrlName = httpHeader.getheader("content-disposition").strip()
				if workingUrlName is not workingName:
					itemPath = myClass._findItemInCaches(workingUrlName, checksumType, checksumValue, displayName=displayName, additionalSourceFolders=additionalSourceFolders, progressReporter=progressReporter)
					if itemPath is not None:
						# add the item to the found items
						myClass.verifiedFiles['%s:%s' % (checksumType, checksumValue)] = itemPath
						
						if progressReporter is not None:
							#progressReporter.update(statusMessage='found by name in the content-disposition header and verified in %s: %s' % (secondsToReadableTime(time.time() - startTime), itemPath))
							progressReporter.update(statusMessage='found by name in the content-disposition header and verified in %s' % (secondsToReadableTime(time.time() - startTime)))
							progressReporter.finishLine()
						readFile.close()
						return itemPath
			
			# try the name in the final URL
			workingUrlName = os.path.basename( urllib.unquote(urlparse.urlparse(readFile.geturl()).path) )
			if workingUrlName is not workingName:
				itemPath = myClass._findItemInCaches(workingUrlName, checksumType, checksumValue, displayName=displayName, additionalSourceFolders=additionalSourceFolders, progressReporter=progressReporter)
				if itemPath is not None:
					# add the item to the found items
					myClass.verifiedFiles['%s:%s' % (checksumType, checksumValue)] = itemPath
					
					if progressReporter is not None:
						#progressReporter.update(statusMessage='found by name in final URL: %s' % (displayName, itemPath))
						progressReporter.update(statusMessage='found by name in final URL')
						progressReporter.finishLine()
					readFile.close()
					return itemPath
			
			# download the file into the cache
			expectedLength = None
			if httpHeader.has_key("content-length"):
				try:
					expectedLength = int(httpHeader.getheader("content-length"))
				except:
					pass
			
			if progressReporter is not None:
				if expectedLength is None:
					progressReporter.update(statusMessage='downloading ')
				else:
					progressReporter.update(statusMessage='downloading %s ' % translateBytes(expectedLength))
			
			hashGenerator = hashlib.new(checksumType)
			downloadTargetPath = os.path.join(myClass.getCacheFolder(), os.path.splitext(workingUrlName)[0] + " " + checksumType + "-" + checksumValue + os.path.splitext(workingUrlName)[1])
			processedBytes, processSeconds = checksumFileObject(hashGenerator, readFile, workingUrlName, expectedLength, copyToPath=downloadTargetPath, progressReporter=progressReporter)
			
			if hashGenerator.hexdigest() != checksumValue:
				os.unlink(downloadTargetPath)
				readFile.close()
				raise FileNotFoundException("Downloaded file did not match checksum: %s (%s vs. %s" % (nameOrLocation, hashGenerator.hexdigest(), checksumValue))
			
			if progressReporter is not None:
				progressReporter.update(statusMessage='downloaded and verified %s in %s (%s/sec)' % (translateBytes(processedBytes), secondsToReadableTime(time.time() - startTime), translateBytes(processedBytes/processSeconds)))
				progressReporter.finishLine()
			readFile.close()
			return downloadTargetPath
		
		# if we have not found anything, then we are out of luck
		raise FileNotFoundException('Could not locate the item: ' + nameOrLocation)
	
	@classmethod
	def _findItemInCaches(myClass, nameOrLocation, checksumType, checksumValue, displayName=None, additionalSourceFolders=None, progressReporter=True): 
		
		# ToDo: input validation 
		
		if progressReporter is True:
			progressReporter = statusHandler(statusMessage='Searching cache folders for ' + nameOrLocation)
		
		# absolute and relative paths
		if os.path.isabs(nameOrLocation):
			# absolute path
			if os.path.exists(nameOrLocation) and checksumValue == checksum(nameOrLocation, checksumType=checksumType, progressReporter=progressReporter)['checksum']:
				return nameOrLocation
		
		elif nameOrLocation.count(os.sep) > 0:
			# relative path
			if os.path.exists(nameOrLocation):
				if checksumValue == checksum(nameOrLocation, checksumType=checksumType, progressReporter=progressReporter)['checksum']:
					return os.path.realpath(os.path.abspath(nameOrLocation))
		
		sourceFolders = myClass.getSourceFolders()
		
		# add additional source folders
		if additionalSourceFolders is None:
			pass
		
		elif isinstance(additionalSourceFolders, str) and os.path.isdir(additionalSourceFolders):
			sourceFolders.append( os.path.realpath(os.path.abspath(additionalSourceFolders)) )
		
		elif hasattr(additionalSourceFolders, '__iter__'):
			for thisFolder in additionalSourceFolders:
				if not os.path.isdir(thisFolder):
					raise ValueError('The folder given to %s as an additionalSourceFolders either did not exist or was not a folder: %s' % (self.__class__.__name__, thisFolder))
					
				sourceFolders.append( os.path.realpath(os.path.abspath(thisFolder)) )
		else:
			raise ValueError('Unable to understand the additionalSourceFolders given: ' + str(additionalSourceFolders))
		
		for thisCacheFolder in sourceFolders:
			assert os.path.isdir(thisCacheFolder), "The cache folder does not exist or is not a folder: %s" % thisCacheFolder
			
			# try paths relative to the source folders
			if nameOrLocation.count(os.sep) > 0 and os.path.exists(os.path.join(thisCacheFolder, nameOrLocation)):
				if checksumValue == checksum(os.path.join(thisCacheFolder, nameOrLocation), checksumType=checksumType, progressReporter=progressReporter)['checksum']:
					return os.path.realpath(os.path.abspath(os.path.join(thisCacheFolder, nameOrLocation)))
			
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
							if checksumValue == checksum(thisItemPath, checksumType=checksumType, progressReporter=progressReporter)['checksum']:
								return thisItemPath
					
					# file name
					if nameOrLocation in [thisItemName, os.path.splitext(thisItemName)[0]] or os.path.splitext(nameOrLocation)[0] in [thisItemName, os.path.splitext(thisItemName)[0]]:
						if checksumValue == checksum(thisItemPath, checksumType=checksumType, progressReporter=progressReporter)['checksum']:
							return thisItemPath
					
					# don't decend into folders that look like bundles or sparce dmg's
					if os.path.isdir(thisItemPath):
						if os.listdir(thisItemPath) == ["Contents"] or os.listdir(thisItemPath) == ["Info.bckup", "Info.plist", "bands", "token"]:
							dirs.remove(thisItemName)
			
		return None
	
	#--------------------Instance Variables---------------------------
	
	displayName			= None		# arbitrary text string for display	
	
	checksumValue		= None
	checksumType		= None
	
	source				= None
	filePath			= None		# a local location to link to
	
	#-------------------- Instance Methods ---------------------------
	
	def __init__(self, displayName, sourceLocation, checksumString, additionalSourceFolders=None):	
		
		if self.cacheFolder is None or not isinstance(self.sourceFolders, list) or len(self.sourceFolders) == 0:
			raise RuntimeWarning('The %s class\'s cache folders must be setup before getCacheFolder is called' % self.__class__.__name__)
		
		# displayName
		if isinstance(displayName, str):
			self.displayName = displayName
		else:
			raise ValueError("Recieved an empty or invalid displayName: " + str(displayName))
		
		# sourceLocation
		if isinstance(sourceLocation, str):
			self.source = sourceLocation
		else:
			raise ValueError("Recieved an empty or invalid sourceLocation: " + str(sourceLocation))
			
		# checksum and checksumType
		if isinstance(checksumString, str) and checksumString.count(":") > 0:
			self.checksumType, self.checksumValue = checksumString.split(":", 1)
			
			# confirm that hashlib supports the hash type:
			try:
				hashlib.new(self.checksumType)
			except ValueError:
				raise Exception('Hash type: %s is not supported by hashlib' % self.checksumType)
		else:
			raise ValueError('Recieved an empty or invalid checksumString: ' + str(checksumString))
		
		foldersToSearch = []
		
		# additionalSourceFolders
		if additionalSourceFolders is None:
			pass
		
		elif isinstance(additionalSourceFolders, str) and os.path.isdir(additionalSourceFolders):
			foldersToSearch.append( os.path.realpath(os.path.abspath(additionalSourceFolders)) )
		
		elif hasattr(additionalSourceFolders, '__iter__'):
			for thisFolder in additionalSourceFolders:
				if not os.path.isdir(thisFolder):
					raise ValueError('The folder given to %s as an additionalSourceFolders either did not exist or was not a folder: %s' % (self.__class__.__name__, thisFolder))
					
					foldersToSearch.append( os.path.realpath(os.path.abspath(thisFolder)) )
		
		else:
			raise ValueError('Unable to understand the additionalSourceFolders given: ' + str(additionalSourceFolders))
		
		# values we need to find or create
		cacheFilePath = self.findItem(sourceLocation, self.checksumType, self.checksumValue, displayName=displayName, additionalSourceFolders=additionalSourceFolders, progressReporter=True)
		
		if cacheFilePath is None:
			raise Exception("Unknown or unsupported source location type: %s" % sourceLocation)
		
		# at this point we know that we have a file at cacheFilePath
		self.filePath = cacheFilePath
