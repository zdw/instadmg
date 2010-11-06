#!/usr/bin/python

#from installer import installer
#
#from .commonExceptions	import FileNotFoundException, InstallerChoicesFileException
##from .managedSubprocess	import managedSubprocess
#
#class pkgInstaller(installer):
#	'''This class handles installing .pkg/mpkg files'''
#	
#	@classmethod
#	def scoreItemMatch(myClass, pathToTarget):
#		if not os.path.exists(pathToTarget):
#			raise ValueError('There was no item at the path provided: %s' % pathToTarget)
#		
#		# try this item out with the installer command line tool to see if it is recognized
#	
#	def subclassInit(self, itemPath, installerChoicesFilePath=None, **kwargs):
#		
#		self.validateInstallerChoicesFile(installerChoicesFilePath) # will raise an exception if it is not valid
#	
#	@classmethod
#	def validateInstallerChoicesFile(myClass, installerChoicesFile):
#		
#		if not os.path.isfile(installerChoicesFile):
#			raise ValueError('InstallerChoices file does not exist, or is not a file: %s' % installerChoicesFile)
#		
#		# read in the file
#		plistNSData, errorMessage = Foundation.NSData.dataWithContentsOfFile_options_error_(installerChoicesFile, Foundation.NSUncachedRead, None)
#		if plistNSData is None or errorMessage is not None:
#			raise InstallerChoicesFileException('unable to read the data in from file: %s, recieved error: %s)' % (installerChoicesFile, errorMessage))
#		
#		# convet it to a plist
#		plistContents, plistFormat, errorMessage = Foundation.NSPropertyListSerialization.propertyListFromData_mutabilityOption_format_errorDescription_(plistNSData, Foundation.NSPropertyListMutableContainers, None, None)
#		if plistContents is None or errorMessage is not None:
#			raise InstallerChoicesFileException('unable to convert the data file: %s into a plist, recieved error: %s' % (installerChoicesFile, errorMessage))
#		
#		# check that it fits for either the "click-simulation" or "direct-choices" patterns
#		
#		choicesFileType = None	# should be "click-simulation" or "direct-choices"
#		
#		for thisObject in plistContents:
#				
#			if choicesFileType is None:
#				# this is a first item, so set the expectation
#				
#				if hasattr(thisObject, "has_key"):
#					choicesFileType = "direct-choices"
#				
#				elif hasattr(thisObject, 'capitalize'):
#					choicesFileType = "click-simulation"
#				
#			if choicesFileType == "direct-choices":
#				if hasattr(thisObject, "has_key") and "attributeSetting" in thisObject and "choiceAttribute" in thisObject and "choiceIdentifier" in thisObject:
#					continue
#				
#				raise InstallerChoicesFileException('the plist does not follow the rules for a direct-choices installerChoices file')
#			
#			if choicesFileType == "click-simulation":
#				if hasattr(thisObject, 'capitalize'):
#					continue
#				
#				raise InstallerChoicesFileException('the plist does not follow the rules for a click-simulation installerChoices file')
#			
#			# we should never get here
#			raise InstallerChoicesFileException('the plist does not follow the rules for either type of installerChoices file')
#		
#		# ToDo: think through whether this should throw exceptions after all
#		return True


