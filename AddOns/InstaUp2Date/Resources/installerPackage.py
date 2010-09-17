#!/usr/bin/python

import os, re, time
import hashlib, urlparse, urllib, urllib2

import pathHelpers
from checksum				import checksumFileObject, checksum
from commonExceptions		import FileNotFoundException
from managedSubprocess		import managedSubprocess
from cacheController		import cacheController


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
	def isValidInstaller(myClass, pkgPath, chrootPath=None, installerChoicesFilePath=None):
		'''Use installer to check if a target looks like a valid pkg/mpkg'''
		
		pathToInstaller = '/usr/sbin/installer'
		
		# ---- validate and normalize input
		
		if pkgPath is None:
			raise ValueError('The pkgPath given to isValidInstaller can not be none')
		elif not os.path.isdir(pkgPath) and not os.path.isfile(pkgPath):
			raise ValueError('The pkgPath given to isValidInstaller does not look correct: ' + str(pkgPath))
		pkgPath = pathHelpers.normalizePath(pkgPath, followSymlink=True)
		
		if chrootPath is not None and not os.path.ismount(chrootPath):
			raise ValueError('The chrootPath given to isValidInstaller must be a mount point, this was not: ' + str(chrootPath))
		
		if chrootPath is not None:
			chrootPath = pathHelpers.normalizePath(chrootPath, followSymlink=True)
		
		if installerChoicesFilePath is not None and not os.path.isfile(installerChoicesFilePath):
			raise ValueError('The installerChoicesFilePath given to isValidInstaller must be a file, this was not: ' + str(installerChoicesFilePath))
		installerChoicesFilePath = pathHelpers.normalizePath(installerChoicesFilePath, followSymlink=True)
		
		# validate that the installer command is avalible
		if chrootPath is None and not os.access(pathToInstaller, os.F_OK | os.X_OK):
			raise RuntimeError('The installer command was not avalible where it was expected to be, or was not useable: ' + pathToInstaller)
		elif chrootPath is not None and not os.access(os.path.join(chrootPath, pathToInstaller[1:]), os.F_OK | os.X_OK):
			raise RuntimeError('The installer command was not avalible where it was expected to be, or was not useable: ' + os.path.join(chrootPath, pathToInstaller[1:]))
		
		# ---- build the command
		
		command = []
		
		if chrootPath is not None:
			command += ['/usr/sbin/chroot', chrootPath]
		
		command += [pathToInstaller, '-pkginfo']
		
		if installerChoicesFilePath is not None:
			command += ['-applyChoiceChangesXML', installerChoicesFilePath]
		
		command += ['-pkg', pkgPath, '-target', '.']
		
		# ---- run the command
		
		process = None
		try:
			if chrootPath is None:
				process = managedSubprocess(command)
			else:
				process = managedSubprocess(command, cwd=chrootPath)
		except:
			return False
		
		# if installer did not have a problem, then it is very probably good
		return True
	
	#--------------------Instance Variables---------------------------
	
	displayName				= None		# arbitrary text string for display	
	
	checksumValue			= None
	checksumType			= None
	
	source					= None
	filePath				= None		# a local location to link to
	installerChoicesPath	= None
	
	#-------------------- Instance Methods ---------------------------
	
	def __init__(self, sourceLocation, checksumString, displayName=None, installerChoices=None):	
		
		# ---- validate input and set instance variables
		
		# sourceLocation
		if hasattr(sourceLocation, 'capitalize'):
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
		if hasattr(displayName, 'capitalize'):
			self.displayName = displayName
		elif displayName is None and sourceLocation is not None:
			if parsedSourceLocationURL.scheme in ['http', 'https']:
				# default to the part that looks like a name in the path
				self.displayName = os.path.basename(parsedSourceLocationURL.path)
			else:
				self.displayName = os.path.basename(sourceLocation)
		else:
			raise ValueError("Recieved an empty or invalid displayName: " + str(displayName))
			
		# checksum and checksumType
		if hasattr(checksumString, 'capitalize') and checksumString.count(":") > 0:
			self.checksumType, self.checksumValue = checksumString.split(":", 1)
			
			# confirm that hashlib supports the hash type:
			try:
				hashlib.new(self.checksumType)
			except ValueError:
				raise Exception('Hash type: %s is not supported by hashlib' % self.checksumType)
		else:
			raise ValueError('Recieved an empty or invalid checksumString: ' + str(checksumString))
		
		# installerChoices
		if installerChoices is not None and os.path.isfile(installerChoices):
			self.installerChoicesPath = pathHelpers.normalizePath(installerChoices, followSymlink=True)
		elif installerChoices is not None:
			raise ValueError('Recieved an empty or invalid installerChoices: ' + str(installerChoices))
	
	def getItemLocalPath(self):
		return self.filePath
	
	def findItem(self, additionalSourceFolders=None, progressReporter=True):
		
		# progressReporter
		if progressReporter is True:
			progressReporter = displayTools.statusHandler(taskMessage='Searching for ' + nameOrLocation)
		elif progressReporter is False:
			progressReporter = None
		
		self.filePath = cacheController.findItem(self.source, self.checksumType, self.checksumValue, self.displayName, additionalSourceFolders, progressReporter)
