#!/usr/bin/python

import os
import hashlib, urlparse, urllib, urllib2

from checksum				import checksumFileObject, checksum
from displayTools			import statusHandler, translateBytes, secondsToReadableTime


class installerPackage:
	"This class represents a .pkg installer, and does much of the work."
		
	#---------------------Class Variables-----------------------------
	
	cacheFolder			= None		# the path to a writeable folder
	sourceFolders		= []		# paths to folders to search when looking for files
	
	verifiedFiles		= []
	
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
	def findItem(myClass, itemName, checksumType, checksumValue, additionalSourceFolders=None):
		'''Look through the caches for this file'''
		
		if not isinstance(checksumType, str) or not isinstance(checksumValue, str):
			raise ValueError('Recieved a value for the checksumType or checksumValue that was not useable: %s:%s' % (checksumType, checksumValue))
		
		# check the already verified items for this checksum
		if '%s:%s' % (checksumType, checksumValue) in myClass.verifiedFiles:
			return self.verifiedFiles['%s:%s' % (checksumType, checksumValue)]
			# ToDo: differentiate these from files that need finding
		
		sourceFolders = myClass.getSourceFolders()
		
		# additionalSourceFolders
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
		
		processReporter = None
		
		for thisCacheFolder in sourceFolders:
			assert os.path.isdir(thisCacheFolder), "The cache folder does not exist or is not a folder: %s" % thisCacheFolder
			
			# ToDo: think through the idea of having nested folders
			for thisItemName in os.listdir(thisCacheFolder):
				
				itemNameCheksum = os.path.splitext(thisItemName)[0].split(" ")[-1]
				
				# check for an item with the same name or if it contains the proper checksum value
				if itemName is not None and (thisItemName == itemName or itemNameCheksum == checksumType + "-" + checksumValue):
				
					if processReporter is None:
						processReporter = statusHandler(linePrefix="\t")
					
					if checksumValue == checksum(os.path.join(thisCacheFolder, thisItemName), checksumType=checksumType, progressReporter=processReporter)['checksum']:
						return os.path.join(thisCacheFolder, thisItemName)
		
		# the item is not in the caches, try to get it otherwise
		
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
		cacheFilePath = None
		
		print("Looking for %s" % displayName)
		
		# check the caches for an item with this checksum
		cacheFilePath = self.findItem(None, self.checksumType, self.checksumValue)
		if cacheFilePath is not None:
			print("	Found in cache folder by the checksum")
		
		else:
			# parse the location information
			parsedSourceLocationURL = urlparse.urlparse(sourceLocation)
			
			if parsedSourceLocationURL.scheme in [None, "file", ""]:
				
				assert parsedSourceLocationURL.params is "", "Unexpected url params in location: %s" % sourceLocation
				assert parsedSourceLocationURL.query is "", "Unexpected url query in location: %s" % sourceLocation
				assert parsedSourceLocationURL.fragment is "", "Unexpected url fragment in location: %s" % sourceLocation
				
				filePath = parsedSourceLocationURL.netloc + parsedSourceLocationURL.path
				
				# if this is a name (ie: not a path), look in the caches for the name
				if filePath.count("/") == 0:
					cacheFilePath = self.findItem(filePath, self.checksumType, self.checksumValue, additionalSourceFolders=foldersToSearch)
					
					if cacheFilePath is not None:
						print("	Found in cache folder by file name")
				
				# an absolute path
				if cacheFilePath is None and os.path.isabs(filePath) and os.path.exists(filePath):
					cacheFilePath = filePath
					
					print("	Found at the absolute path provided")
				
				# try this as a relative path from cwd
				if cacheFilePath is None and not os.path.isabs(filePath) and os.path.exists(filePath):
					cacheFilePath = os.path.abspath(filePath)

					print("	Found at the relative path provided")
				
				# try this path in each of the cache folders
				if cacheFilePath is None and not os.path.isabs(filePath):
					for cacheFolder in self.sourceFolders:
						if os.path.exists( os.path.join(cacheFolder, filePath) ):
							cacheFilePath = os.path.abspath(os.path.join(cacheFolder, filePath))
							print("	Found in the cache folder at the provided path")
							break
				
				# final check to make sure the file exists
				if cacheFilePath is None or not os.path.exists(cacheFilePath):
					raise FileNotFoundException("The referenced file/folder does not exist: %s" % cacheFilePath)
				
			elif parsedSourceLocationURL.scheme in ["http", "https"]:
				# url to download
				
				# guess the name from the URL
				cacheFilePath = self.findItem(os.path.basename(parsedSourceLocationURL.path), self.checksumType, self.checksumValue, additionalSourceFolders=foldersToSearch)
				if cacheFilePath is not None:
					print("	Found in cache folder by the name in the URL")
					
				else:
					# open a connection get a file name
					try:
						readFile = urllib2.urlopen(sourceLocation)
					except IOError, error:
						if hasattr(error, 'reason'):
							raise Exception('Unable to connect to remote url: %s got error: %s' % (sourceLocation, error.reason))
						elif hasattr(error, 'code'):
							raise Exception('Got status code: %s while trying to connect to remote url: %s' % (str(error.code), sourceLocation))
					
					if readFile is None:
						raise Exception("Unable to open file for checksumming: %s" % sourceLocation)
						
					# default the filename to the last bit of path of the url
					fileName = os.path.basename( urllib.unquote(urlparse.urlparse(readFile.geturl()).path) )
					expectedLength = None
					
					# grab the name of the file and its length from the http headers if avalible
					httpHeader = readFile.info()
					if httpHeader.has_key("content-length"):
						try:
							expectedLength = int(httpHeader.getheader("content-length"))
						except:
							pass # 
					
					if httpHeader.has_key("content-disposition"):
						fileName = httpHeader.getheader("content-disposition").strip()
					
					# check to see if we already have a file with this name and checksum
					cacheFilePath = self.findItem(fileName, self.checksumType, self.checksumValue, additionalSourceFolders=foldersToSearch)
					
					if cacheFilePath is not None:
						print("	Found using name in a redirected URL or content disposition header")
					
					else:
						# continue downloading into the main cache folder
						hashGenerator = hashlib.new(self.checksumType)
						
						processReporter = statusHandler(linePrefix="\t")
						if expectedLength is None:
							processReporter.update(statusMessage='Downloading %s: ' % fileName, updateMessage='starting')
						else:
							processReporter.update(statusMessage='Downloading %s (%s): ' % (fileName, translateBytes(expectedLength)), updateMessage='starting')
						
						targetFilePath = os.path.join(self.getCacheFolder(), os.path.splitext(fileName)[0] + " " + self.checksumType + "-" + self.checksumValue + os.path.splitext(fileName)[1])
						
						processedBytes, processSeconds = checksumFileObject(hashGenerator, readFile, fileName, expectedLength, copyToPath=targetFilePath, progressReporter=processReporter)
						
						if hashGenerator.hexdigest() != self.checksumValue:
							os.unlink(targetFilePath)
							raise Exception("Downloaded file did not match checksum: %s" % sourceLocation)
						
						cacheFilePath = targetFilePath
						
						processReporter.update(statusMessage='%s (%s) downloaded and verified in %s (%s/sec)' % (fileName, translateBytes(processedBytes), secondsToReadableTime(processSeconds), translateBytes(processedBytes/processSeconds)), updateMessage='', forceOutput=True)
						processReporter.update(updateMessage='\n', forceOutput=True);
							
					readFile.close()
				
			else:
				raise Exception("Unknown or unsupported source location type: %s" % sourceLocation)
		
		# at this point we know that we have a file at cacheFilePath
		self.filePath = cacheFilePath
