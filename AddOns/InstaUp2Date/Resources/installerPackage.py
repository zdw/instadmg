#!/usr/bin/python

import os, re, time
import hashlib, urlparse, urllib, urllib2

from checksum				import checksumFileObject, checksum
from displayTools			import statusHandler, bytesToRedableSize, secondsToReadableTime
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
	def addItemToVerifiedFiles(myClass, checksumString, itemPath):
		
		if checksumString.count(':') != 1:
			raise ValueError('Checksum string does not look valid: ' + checksumString)
		
		if not os.path.exists(itemPath):
			raise ValueError('Item does not exist: ' + itemPath)
		
		myClass.verifiedFiles[checksumString] = itemPath
	
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
	
	def __init__(self, sourceLocation, checksumString, displayName=None):	
		
		if self.cacheFolder is None or not isinstance(self.sourceFolders, list) or len(self.sourceFolders) == 0:
			raise RuntimeWarning('The %s class\'s cache folders must be setup before getCacheFolder is called' % self.__class__.__name__)
		
		# sourceLocation
		if isinstance(sourceLocation, str):
			# remove file:// if it is the sourceLocation
			if sourceLocation.startswith('file://'):
				sourceLocation = nameOrLocation[len('file://'):]
		
			self.source = sourceLocation
		else:
			raise ValueError("Recieved an empty or invalid sourceLocation: " + str(sourceLocation))
		
		parsedSourceLocationURL = urlparse.urlparse(sourceLocation)
		
		# fail out if we don't support this method
		if parsedSourceLocationURL.scheme not in ['', 'http', 'https']:
			raise ValueError('findItem can not process urls types other than http, https, or file')
					
		# displayName
		if isinstance(displayName, str):
			self.displayName = displayName
		elif displayName is None and sourceLocation is not None:
			# default to the part that looks like a name in the path
			displayName = os.path.basename(parsedSourceLocationURL.path)
		else:
			raise ValueError("Recieved an empty or invalid displayName: " + str(displayName))
			
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
	
	def findItem(self, additionalSourceFolders=None, progressReporter=True):
		'''Look through the caches to find and verify this item, and download it if necessary'''
		
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
		
		# setup the reporter if needed
		if progressReporter is True:
			progressReporter = statusHandler(taskMessage="\t" + self.displayName + " ")
		
		# start the timer
		startTime = time.time()
		parsedPath = urlparse.urlparse(self.source)
		
		# try it as an absolute path
		if parsedPath.scheme is '' and os.path.isabs(self.source):
			if os.path.exists(self.source):
				result = checksum(self.source, checksumType=self.checksumType, progressReporter=progressReporter)
				if self.checksumValue == result['checksum']:
					self.filePath = os.path.realpath(os.path.abspath(self.source))
					if progressReporter is not None:
						progressReporter.update(statusMessage='found by absolute path and verified in %s' % (secondsToReadableTime(time.time() - startTime)))
						progressReporter.finishLine()
					return
				else:
					raise FileNotFoundException('The item at the path given does not match the checksum given: ' + self.filePath)
					
			else:
				# the file does not exist, so we could not find it where it was supposed to be, fail rather than search further
				raise FileNotFoundException('No file/folder existed at the absolute path: ' + self.filePath)
				
		# try looking for it as a relative path from the search folders and cwd
		elif parsedPath.scheme is '' and self.source.count(os.sep):
			for thisSourceFolder in foldersToSearch:
				thisPath = os.path.join(thisSourceFolder, self.source)
				if os.path.exists(thisPath) and self.checksumValue == checksum(thisPath, checksumType=self.checksumType, progressReporter=progressReporter):
					self.filePath = os.path.realpath(os.path.abspath(self.source))
					if progressReporter is not None:
						progressReporter.update(statusMessage='found by relative path in the source folders and verified in %s' % (secondsToReadableTime(time.time() - startTime)))
						progressReporter.finishLine()
					return
			
			# from the current working directory
			if os.path.exists(self.filePath) and self.checksumValue == checksum(self.filePath, checksumType=self.checksumType, progressReporter=progressReporter):
				self.filePath = os.path.realpath(os.path.abspath(self.source))
				if progressReporter is not None:
					progressReporter.update(statusMessage='found by relative path and verified in %s' % (secondsToReadableTime(time.time() - startTime)))
					progressReporter.finishLine()
				return
			
			# if we are here, then it does not work as a relative file path, so bail out
			raise FileNotFoundException('No file/folder existed at the relative path: ' + self.filePath)
		
		# check the already verified items for this checksum
		if '%s:%s' % (self.checksumType, self.checksumValue) in self.verifiedFiles:
			self.filePath = self.verifiedFiles['%s:%s' % (self.checksumType, self.checksumValue)]
			if progressReporter is not None:
				progressReporter.update(statusMessage='found previously')
				progressReporter.finishLine()
			return
		
		# try in the cache by displayName and checksum
		foundPath = self._findItemInCaches(self.displayName, self.checksumType, self.checksumValue, displayName=self.displayName, additionalSourceFolders=additionalSourceFolders, progressReporter=progressReporter)
		if foundPath is not None:
			# add the item to the found items
			self.addItemToVerifiedFiles('%s:%s' % (self.checksumType, self.checksumValue), foundPath)
			if progressReporter is not None:
				progressReporter.update(statusMessage='found by display name or checksum and verified in %s' % (secondsToReadableTime(time.time() - startTime)))
				progressReporter.finishLine()
			self.filePath = foundPath
			return
		
		# get an idea of what the name is
		workingName = None
		if parsedPath.scheme in ['http', 'https']:
			workingName = os.path.basename(parsedPath.path)
		else:
			workingName = self.source
		
		# look for the item in the caches
		if progressReporter is not None:
			progressReporter.update(statusMessage='looking in the source folders by guessed name and checksum')
		
		# look by guessed name
		foundPath = self._findItemInCaches(workingName, self.checksumType, self.checksumValue, displayName=self.displayName, additionalSourceFolders=additionalSourceFolders, progressReporter=progressReporter)
		if foundPath is not None:
			# add the item to the found items
			self.addItemToVerifiedFiles('%s:%s' % (self.checksumType, self.checksumValue), foundPath)
			if progressReporter is not None:
				progressReporter.update(statusMessage='found by guessed name and verified in %s' % (secondsToReadableTime(time.time() - startTime)))
				progressReporter.finishLine()
			self.filePath = foundPath
			return
		
		# work on urls
		if parsedPath.scheme in ['http', 'https']:
			if progressReporter is not None:
				progressReporter.update(statusMessage='checking for a name from the server')
			
			# open a connection to try and figure out the file name from it
			try:
				readFile = urllib2.urlopen(self.source)
			except IOError, error:
				if hasattr(error, 'reason'):
					raise Exception('Unable to connect to remote url: %s got error: %s' % (self.source, error.reason))
				elif hasattr(error, 'code'):
					raise Exception('Got status code: %s while trying to connect to remote url: %s' % (str(error.code), self.source))
			
			if readFile is None:
				raise Exception("Unable to open file for checksumming: %s" % self.source)
			
			workingUrlName = workingName
			
			# try reading out the content-disposition header
			httpHeader = readFile.info()
			if httpHeader.has_key("content-disposition"):
				workingUrlName = httpHeader.getheader("content-disposition").strip()
				if workingName is not workingName:
					itemPath = myClass._findItemInCaches(workingUrlName, self.checksumType, self.checksumValue, displayName=self.displayName, additionalSourceFolders=additionalSourceFolders, progressReporter=progressReporter)
					if itemPath is not None:
						# add the item to the found items
						self.addItemToVerifiedFiles('%s:%s' % (self.checksumType, self.checksumValue), itemPath)
						
						# set the value, and close up shop
						self.filePath = itemPath
						if progressReporter is not None:
							progressReporter.update(statusMessage='found by name in the content-disposition header and verified in %s' % (secondsToReadableTime(time.time() - startTime)))
							progressReporter.finishLine()
						readFile.close()
						return
			
			# try the name in the final URL
			workingUrlName = os.path.basename( urllib.unquote(urlparse.urlparse(readFile.geturl()).path) )
			if workingUrlName is not workingName:
				itemPath = self._findItemInCaches(workingUrlName, self.checksumType, self.checksumValue, displayName=self.displayName, additionalSourceFolders=additionalSourceFolders, progressReporter=progressReporter)
				if itemPath is not None:
					# add the item to the found items
					self.addItemToVerifiedFiles('%s:%s' % (self.checksumType, self.checksumValue), itemPath)
						
						# set the value, and close up shop
					self.filePath = itemPath
					if progressReporter is not None:
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
					progressReporter.update(statusMessage='downloading %s ' % bytesToRedableSize(expectedLength))
			
			hashGenerator = hashlib.new(self.checksumType)
			downloadTargetPath = os.path.join(self.getCacheFolder(), os.path.splitext(workingUrlName)[0] + " " + self.checksumType + "-" + self.checksumValue + os.path.splitext(workingUrlName)[1])
			processedBytes, processSeconds = checksumFileObject(hashGenerator, readFile, workingUrlName, expectedLength, copyToPath=downloadTargetPath, progressReporter=progressReporter)
			
			if hashGenerator.hexdigest() != self.checksumValue:
				os.unlink(downloadTargetPath)
				readFile.close()
				raise FileNotFoundException("Downloaded file did not match checksum: %s (%s vs. %s)" % (self.source, hashGenerator.hexdigest(), self.checksumValue))
		
			if progressReporter is not None:
				progressReporter.update(statusMessage='downloaded and verified %s in %s (%s/sec)' % (bytesToRedableSize(processedBytes), secondsToReadableTime(time.time() - startTime), bytesToRedableSize(processedBytes/processSeconds)))
				progressReporter.finishLine()
			readFile.close()
			self.filePath = downloadTargetPath
			return
		
		# if we have not found anything, then we are out of luck
		raise FileNotFoundException('Could not locate the item: ' + self.source)
		
		
		cacheFilePath = self.findItem(sourceLocation, self.checksumType, self.checksumValue, displayName=displayName, additionalSourceFolders=additionalSourceFolders, progressReporter=True)
		
		if cacheFilePath is None:
			raise Exception("Unknown or unsupported source location type: %s" % sourceLocation)
		
		# at this point we know that we have a file at cacheFilePath
		self.filePath = cacheFilePath
	
	def getItemLocalPath(self):
		return self.filePath
