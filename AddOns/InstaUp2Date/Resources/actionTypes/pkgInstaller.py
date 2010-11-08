#!/usr/bin/python

import os

import actionBase

class pkgInstaller(actionBase.actionBase):
	
	installerChoicesFilePath	= None
	
	@classmethod
	def scoreItemMatch(myClass, inputItem, processInformation, **kwargs):
		
		# -- validate input
		
		if not hasattr(inputItem, "isContainerType"):
			raise ValueError('inputItem must be a subclass of containerBase, got: %s (%s)' % (str(inputItem), type(inputItem)))
		
		if not hasattr(processInformation, '__iter__'):
			raise ValueError('processInformation must be a dict, got: %s (%s)' % (str(processInformation), type(processInformation)))
		
		# -- score item
		
		# note: we are depending on 'prepareForUse' already having been called on intputItem
		
		foundApps = False
		for thisItem in inputItem.getTopLevelItems():
			if os.path.splitext(thisItem)[1].lower() in ['.pkg', '.mpkg']:
				return myClass.getMatchScore()
		
		return 0
	
	@classmethod
	def validatePKGInstaller(myClass, itemPath, targetVolume=None, installerChoicesFile=None):
		'''Use the command-line installer to validate a target file'''
		
		# -- validate and normalize input
		
		# -- simple validation of file
		
		# -- use 'installer' to validate file
	
	def subclassInit(self, itemPath, **kwargs):
		
		if 'installerChoicesFile' in kwargs:
			if self.validateInstallerChoicesFile(installerChoicesFilePath) is True:
				self.installerChoicesFilePath = kwargs['installerChoicesFile']
				
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


