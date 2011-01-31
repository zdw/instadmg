#!/usr/bin/python

# InstaUpToDate
#
#	This script parses one or more catalog files to setup InstaDMG

__version__		= int('$Revision$'.split(" ")[1])

import os, sys, re
import hashlib, urlparse, subprocess, datetime

import Resources.pathHelpers			as pathHelpers
import Resources.commonConfiguration	as commonConfiguration
import Resources.displayTools			as displayTools
import Resources.findInstallerDisc		as findInstallerDisc
import Resources.commonExceptions		as commonExceptions
from Resources.container				import container
from Resources.managedSubprocess		import managedSubprocess
from Resources.tempFolderManager		import tempFolderManager
from Resources.installerPackage			import installerPackage
from Resources.cacheController			import cacheController

#------------------------------SETTINGS------------------------------

versionString						= "0.5b (svn revision: %i)" % __version__

allowedCatalogFileSettings			= [ 'ISO Language Code', 'Output Volume Name', 'Output File Name', 'Installer Disc Builds' ]
allowedCatalogChecksumFileSettings	= [ 'Installer Choices File', 'Supporting Disc' ]

# these should be in the order they run in
systemSectionTypes					= [ "OS Updates", "System Settings" ]
addedSectionTypes					= [ "Apple Updates", "Third Party Software", "Third Party Settings", "Software Settings" ]	

#------------------------RUNTIME ADJUSTMENTS-------------------------

appleUpdatesFolderPath				= os.path.join(commonConfiguration.pathToInstaDMGFolder, "InstallerFiles", "BaseUpdates")
customPKGFolderPath					= os.path.join(commonConfiguration.pathToInstaDMGFolder, "InstallerFiles", "CustomPKG")

#-------------------------------CLASSES------------------------------

class instaUpToDate:
	"The central class to manage the process"
		
	#---------------------Class Variables-----------------------------
	
	sectionStartParser			= re.compile('^(?P<sectionName>[^\t]+):\s*(#.*)?$')
	packageLineParser			= re.compile('^\t(?P<displayName>[^\t]*)\t(?P<fileLocation>[^\t]+)\t(?P<fileChecksum>(?P<checksumType>\S+):(?P<checksumValue>\S+))(\t(?P<installerChoicesFile>[^\t\n]+))?\s*(#.*)?$')
	emptyLineParser				= re.compile('^\s*(?P<comment>#.*)?$')
	settingLineParser			= re.compile('^(?P<variableName>%s)\s*[=:]\s*(?P<variableValue>.*)' % "|".join(allowedCatalogFileSettings))
	settingLineChecksumParser	= re.compile('^(?P<variableName>%s)\s*[=:]\s*(?P<variableValue>.*)(\t(?P<fileChecksum>(?P<checksumType>\S+):(?P<checksumValue>\S+)))' % "|".join(allowedCatalogChecksumFileSettings))
	includeLineParser			= re.compile('^\s*include-file\s*[=:]\s*(?P<location>.*)(\s*#.*)?$')
	
	fileExtensions				= ['.catalog']
	
	#--------------------Instance Variables---------------------------
	
	catalogFilePath				= None	# the main catalog file
	
	installerDiscPath			= None	# path to the installer disc to use
	
	sectionFolders				= None
	
	packageGroups 				= None	# a Hash
	parsedFiles 				= None	# an Array, for loop checking
	
	outputFilePath				= None	# path to the created dmg
	
	# catalog file settings
	outputVolumeName			= None
	outputFileName				= None
	installerDiscBuilds			= None
	isoLanguageCode				= None
	
	installerChoicesFilePath	= None
	
	supportingDiscPath			= None
	
	# defaults
	outputVolumeNameDefault		= 'Macintosh HD'

	#---------------------Class Functions-----------------------------
	
	@classmethod
	def getCatalogFullPath(myClass, catalogFileInput, catalogFolders):
		'''Classmethod to translate input to a abs-path from one of the accepted formats (checked in this order):
			- ToDo: http or https reference (will be downloaded and temporary filepath returned)
			- absolute path to a file
			- catalog file name within the CatalogFiles folder, with or without the .catalog extension
			- relative path from CatalogFiles folder, with or without the .catalog extension
			- relative path from the pwd, with or without the .catalog extension
		'''
		
		if catalogFolders is None:
			raise Exception('getCatalogFullPath was passed an emtpy catalogFolders')
			
		elif isinstance(catalogFolders, str) and os.path.isdir(str(catalogFolders)):
			catalogFolders = [catalogFolders]
		
		elif hasattr(catalogFolders, '__iter__'):
			for thisFolder in catalogFolders:
				if not os.path.isdir(str(thisFolder)):
					raise Exception('getCatalogFullPath was passed a bad catalog folder: ' + str(thisFolder))
			
		else:
			raise Exception('getCatalogFullPath unable to understand the catalogFolders given: ' + str(catalogFolders))
		
		
		# http/https url
		if urlparse.urlparse(catalogFileInput).scheme in ["http", "https"]:
			raise Exception("URL catalog files are not done yet")
			# ToDo: download the files, then return the path
		
		# try it as an absolute or relative file path
		if os.path.isfile(catalogFileInput):
			return pathHelpers.normalizePath(catalogFileInput, followSymlink=True)
		
		# cycle through the folders we have been given to see if it is there
		if not os.path.isabs(catalogFileInput):
			for thisFolder in catalogFolders:
				
				# try the simple path:
				if os.path.isfile( os.path.join(thisFolder, catalogFileInput) ):
					return pathHelpers.normalizePath(os.path.join(thisFolder, catalogFileInput), followSymlink=True)
				
				# try appending file extension(s)
				for thisExtension in myClass.fileExtensions:
					if os.path.isfile( os.path.join(thisFolder, catalogFileInput + thisExtension) ):
						return pathHelpers.normalizePath(os.path.join(thisFolder, catalogFileInput + thisExtension), followSymlink=True)
		
		raise commonExceptions.CatalogNotFoundException("The file input is not one that getCatalogFullPath understands, or can find: %s" % catalogFileInput)
		
	#------------------------Functions--------------------------------
	
	def __init__(self, catalogFilePath, sectionFolders, catalogFolders):
		
		# set up section folders structure
		self.sectionFolders 		= []
		self.catalogFolders			= []
		self.packageGroups			= {}
		self.parsedFiles			= []
		
		self.supportingDiscPath		= []
				
		# catalogFilePath
		if not os.path.exists(catalogFilePath):
			raise commonExceptions.FileNotFoundException('The catalog file does not exist: ' + str(catalogFilePath))
		self.catalogFilePath = catalogFilePath
		
		# catalogFolders
		if isinstance(catalogFolders, str) and os.path.isdir(catalogFolders):
			catalogFolders = [str(catalogFolders)]
		
		if hasattr(catalogFolders, '__iter__'):
			for thisCatalogFolder in catalogFolders:
				if not os.path.isdir(str(thisCatalogFolder)):
					raise Exception('%s called with a catalogFolder that was not a folder: %s' % (self.__class__, thisCatalogFolder))
				self.catalogFolders.append(str(thisCatalogFolder))
				
		else:
			raise Exception('%s called with a catalogFolder that could not be understood: %s' % (self.__class__, str(sectionFolders)))
		
		# sectionFolders
		if not hasattr(sectionFolders, '__iter__'):
			raise Exception('%s called with a sectionFolders attribute that was not an array: %s' % (self.__class__, sectionFolders))
		
		for thisFolder in sectionFolders:
			if not hasattr(thisFolder, 'has_key') or not thisFolder.has_key('folderPath') or not thisFolder.has_key('sections'):
				raise Exception('%s called with a sectionFolders that had a bad item in it: %s' % (self.__class__, thisFolder))
			
			newSection = {}
			
			if not isinstance(thisFolder['folderPath'], str) or not os.path.isdir(thisFolder['folderPath']):
				raise Exception('%s called with a sectionFolders that had a bad item in it (folderPath was not an existing path): %s' % (self.__class__, thisFolder))
			
			newSection['folderPath'] = str(thisFolder['folderPath'])
			
			if not hasattr(thisFolder['sections'], 'append'):
				raise Exception('%s called with a sectionFolders that had a bad item in it (sections was not an array): %s' % (self.__class__, thisFolder))
			
			newSection['sections'] = []
			
			for thisSectionName in thisFolder['sections']:
				if not str(thisSectionName) in (systemSectionTypes + addedSectionTypes):
					raise Exception('Section type not in allowed section types: ' + str(thisSectionName))
				
				for thisSectionFolder in self.sectionFolders:
					if str(thisSectionName) in thisSectionFolder['sections']:
						raise Exception('Section type was repeated: ' + str(thisSectionName))
					
				newSection['sections'].append(str(thisSectionName))
				self.packageGroups[str(thisSectionName)] = []
			
			self.sectionFolders.append(newSection)
	
	def getMainCatalogName(self):
		return os.path.splitext(os.path.basename(self.catalogFilePath))[0]
	
	def parseCatalogFile(self, fileLocation=None):
		
		if fileLocation is None:
			fileLocation = self.catalogFilePath
		
		# the file passed could be an absolute path, a relative path, or a catalog file name
		#	the first two are handled without a special section, but the name needs some work
		
		fileLocation = self.getCatalogFullPath(fileLocation, self.catalogFolders) # there should not be an error here, since we have already validated it
		# note: this last will have taken care of downloading any remote files
		
		assert os.path.isfile(fileLocation), "There was no file where it was expected to be: %s" % fileLocation
		
		# check to make sure we are not in a loop
		assert fileLocation not in self.parsedFiles, 'Loop detected in catalog files: %s' % fileLocation
		self.parsedFiles.append(fileLocation)
		
		inputfile = open(fileLocation, "r")
		if inputfile == None:
				raise Exception('Unable to open input file: %s' % inputFilePath) # TODO: improve error handling
			
		currentSection = None;
		lineNumber = 0
		
		# parse through the file
		for line in inputfile.readlines():
			lineNumber += 1
			
			if self.emptyLineParser.search(line):
				continue
			
			# ---- settings lines
			settingLineMatch = self.settingLineParser.search(line)
			if settingLineMatch is not None:
				# get the variable name this would be
				variableName = settingLineMatch.group("variableName").split()[0].lower() + "".join(x.capitalize() for x in settingLineMatch.group("variableName").split()[1:])
				
				# sanity check that this variable exists
				if not hasattr(self, variableName):
					raise InstallerChoicesFileException('The %s class does not have a "%s" variable as it should have. This error should never happen.' % (self.__class__.__name__, variableName), choicesFile=fileLocation, lineNumber=lineNumber)
				
				if hasattr(getattr(self, variableName), '__iter__'):
					# if this variable as an array, append to it
					getattr(self, variableName).append(settingLineMatch.group("variableValue")) # amazingly, this works
				
				elif getattr(self, variableName) is None:
					setattr(self, variableName, settingLineMatch.group("variableValue"))
				
				# note: if the variable is already set, ignore this value
				
				continue
			
			# ---- settings lines with checksums
			settingLineMatch = self.settingLineChecksumParser.search(line)
			if settingLineMatch is not None:
				
				# get the variable name this would be
				variableName = settingLineMatch.group("variableName").split()[0].lower() + "".join(x.capitalize() for x in settingLineMatch.group("variableName").split()[1:])
				
				checksumType	= settingLineMatch.group('checksumType')
				checksumValue	= settingLineMatch.group('checksumValue')
				
				# find this item in the caches by name/checksum
				progressReporter = displayTools.statusHandler(taskMessage='\t%s: %s -' % (settingLineMatch.group("variableName"), settingLineMatch.group("variableValue")))
				itemPath = None
				try:
					itemPath = cacheController.findItem(settingLineMatch.group("variableValue"), checksumType, checksumValue, progressReporter=progressReporter)
				except commonExceptions.FileNotFoundException:
					raise commonExceptions.InstallerChoicesFileException('Unable to find %s: %s (checksum: %s)' % (settingLineMatch.group("variableName"), settingLineMatch.group("variableValue"), settingLineMatch.group("fileChecksum")), choicesFile=fileLocation, lineNumber=lineNumber)
				
				# sanity check that this variable exists
				if not hasattr(self, variableName + 'Path'):
					raise Exception('The %s class does not have a "%s" variable as it should have. This error should never happen.' % (self.__class__.__name__, variableName + 'Path'))
				
				if hasattr(getattr(self, variableName + 'Path'), '__iter__'):
					# if this variable as an array, append to it
					getattr(self, variableName + 'Path').append(itemPath) # amazingly, this works
				
				elif getattr(self, variableName + 'Path') is None:
					setattr(self, variableName + 'Path', itemPath)
				
				# note: if the variable is already set, ignore this value
				
				continue
			
			# ---- file includes lines
			includeLineMatch = self.includeLineParser.search(line)
			if includeLineMatch:
				self.parseCatalogFile( self.getCatalogFullPath(includeLineMatch.group("location"), self.catalogFolders) )
				continue
			
			# ---- section lines
			sectionTitleMatch = self.sectionStartParser.search(line)
			if sectionTitleMatch:
				if sectionTitleMatch.group("sectionName") not in self.packageGroups and sectionTitleMatch.group("sectionName") != "Base OS Disk":
					raise Exception('Unknown section title: "%s" on line: %i of file: %s\n%s' % (sectionTitleMatch.group("sectionName"), lineNumber, fileLocation, line) ) # TODO: improve error handling
				
				currentSection = sectionTitleMatch.group("sectionName")
				continue
			
			# ---- item lines
			packageLineMatch = self.packageLineParser.search(line)
			if packageLineMatch:
				if currentSection == None:
					# we have to have a place to put this
					raise Exception('Every item must belong to a section') # TODO: improve error handling
				
				thisPackage = installerPackage(
					displayName				= packageLineMatch.group("displayName"),
					sourceLocation			= packageLineMatch.group("fileLocation"),
					checksumString			= packageLineMatch.group("fileChecksum"),
					installerChoices		= packageLineMatch.group("installerChoicesFile")
				)
				
				print('\t' + packageLineMatch.group("displayName"))
				
				self.packageGroups[currentSection].append(thisPackage)
				
				continue
				
			# if we got here, the line was not good
			raise Exception('Error in config file: %s line number: %i\n%s' % (fileLocation, lineNumber, line)) # TODO: improve error handling
			
		inputfile.close()
	
	def findItems(self):
		'''Find all the items verify their checksums, and download anything that is missing'''
		
		for thisSectionName in self.packageGroups:
			for thisItem in self.packageGroups[thisSectionName]:
				# progressReporter
				progressReporter = displayTools.statusHandler(taskMessage='	' + thisItem.displayName + ' -')
				thisItem.findItem(progressReporter=progressReporter)
	
	def arrangeFolders(self):
		"Create the folder structure for InstaDMG, and pop in soft-links to the items in the cache folder"
		
		assert isinstance(self.sectionFolders, list), "sectionfolders is required, and must be a list of dicts"
		
		import math
		
		for thisSectionFolder in self.sectionFolders:
			
			sectionTypes = thisSectionFolder["sections"]
			updateFolder = thisSectionFolder["folderPath"]
			
			itemsToProcess = []
			for thisSection in sectionTypes:
				itemsToProcess += self.packageGroups[thisSection]
			
			# Get the number of leading 0s we need
			leadingZeroes = 0
			if len(itemsToProcess) > 0:
				leadingZeroes = int(math.log10(len(itemsToProcess)))
			fileNameFormat = '%0' + str(leadingZeroes + 1) + "d %s"
			
			# Create symlinks for all of the items
			itemCounter = 1
			for thisItem in itemsToProcess:
				
				targetFileName = fileNameFormat % (itemCounter, thisItem.displayName)
				targetFilePath = pathHelpers.normalizePath(os.path.join(updateFolder, targetFileName), followSymlink=True)
				
				if thisItem.installerChoicesPath is None:
					# a straight link to the file
					os.symlink(thisItem.filePath, targetFilePath)
				
				else:
					# build a folder linking the item ant the choices path into it
					os.mkdir(targetFilePath)
					os.symlink(thisItem.filePath, os.path.join(targetFilePath, os.path.basename(thisItem.filePath)))
					os.symlink(thisItem.installerChoicesPath, os.path.join(targetFilePath, 'installerChoices.xml'))
				
				assert os.path.exists(targetFilePath), "Something went wrong linking from %s to %s" % (targetFilePath, pathFromTargetToSource) # this should catch bad links
				
				itemCounter += 1
				
		return True
	
	def cleanInstaDMGFolders(self):
		'''Clean the chosen folders, removing folders and symlinks, not actual data.'''
		
		assert isinstance(self.sectionFolders, list), "sectionfolders is required, and must be a list of dicts"
		
		for sectionFolder in self.sectionFolders:
			assert isinstance(sectionFolder, dict) and "folderPath" in sectionFolder and "sections" in sectionFolder, "sectionfolder information must be a dict with a 'folderPath' value, instead got: %s" % sectionFolder
			assert os.path.isdir(sectionFolder['folderPath']), "The sectionfolder did not seem to exist: %s" % sectionFolder['folderPath']
			assert os.path.isabs(sectionFolder['folderPath']), "cleanInstaDMGFolders was passed a non-abs path to a folder: %s" % sectionFolder['folderPath']
			
			# clean the folders
			for thisItem in os.listdir(sectionFolder['folderPath']):
				
				# skip over a few types of items
				if thisItem in [".svn", ".DS_Store"]:
					continue
				
				pathToThisItem = os.path.join(sectionFolder['folderPath'], thisItem)
				
				# remove all links
				if os.path.islink(pathToThisItem):
					os.unlink(pathToThisItem)
					continue
				
				# remove the links from any folder, and if it then empty, remove it (otherwise bail)
				if os.path.isdir(pathToThisItem):
					for thisSubItem in os.listdir(pathToThisItem):
						pathToThisSubItem = os.path.join(pathToThisItem, thisSubItem)
						if os.path.islink(pathToThisSubItem):
							os.unlink(pathToThisSubItem)
						else:
							raise Exception('While cleaning folder: %s found a non-softlinked item: %s' % (sectionFolder['folderPath'], pathToThisSubItem))
					os.rmdir(pathToThisItem)
					continue
				
				raise Exception('While cleaning folder: %s found a non-softlinked item: %s' % (sectionFolder['folderPath'], pathToThisItem))
	
	def runInstaDMG(self, scratchFolder=None, outputFolder=None):
		
		assert isinstance(self.sectionFolders, list), "sectionFolders should be a list of hashes"
		
		# Todo: create a routine to validate things before the run
		
		instaDMGCommand	= [ commonConfiguration.pathToInstaDMG, "-f" ]
		
		# ISO Language Code
		if self.isoLanguageCode is not None:
			instaDMGCommand += ["-i", self.isoLanguageCode]
			# TODO: check with installer to see if it will accept this language code
		
		# Installer and Supporting Discs
		instaDMGCommand += ['-I', self.installerDiscPath]
		for thisDisc in self.supportingDiscPath:
			instaDMGCommand += ['-J', thisDisc]
		
		# InstallerChoices file
		if self.installerChoicesFilePath is not None:
			instaDMGCommand += ["-L", self.installerChoicesFilePath]
		
		# Output Volume Name
		if self.outputVolumeName is not None:
			instaDMGCommand += ["-n", self.outputVolumeName]
		else:
			instaDMGCommand += ["-n", self.outputVolumeNameDefault]
		
		# Output File Name
		if self.outputFileName is not None:
			self.outputFilePath = os.path.join(commonConfiguration.standardOutputFolder, self.outputFileName)
		else:
			# default to the name portion of the catalog file name
			self.outputFilePath = os.path.join(commonConfiguration.standardOutputFolder, os.path.splitext(os.path.basename(self.catalogFilePath))[0])
		
		if os.path.splitext(os.path.basename(self.outputFilePath))[1].lower() != '.dmg':
			self.outputFilePath += '.dmg'
		
		instaDMGCommand += ["-m", os.path.basename(self.outputFilePath)]
		
		# Scratch foler
		if scratchFolder is not None:
			instaDMGCommand += ["-t", scratchFolder]
		
		# Section folders
		for thisSectionFolder in self.sectionFolders:
			instaDMGCommand += ['-K', thisSectionFolder['folderPath']]
		
		# Output folder
		if outputFolder is not None:
			instaDMGCommand += ["-o", outputFolder]
		else:
			instaDMGCommand += ["-o", commonConfiguration.standardOutputFolder]

		print("\nRunning InstaDMG: %s\n" % " ".join(instaDMGCommand))
		# we should be in the same directory as InstaDMG
		
		if subprocess.call(instaDMGCommand) != 0:
			raise RuntimeError('InstaDMG process did not run sucessfully')
		# TODO: a lot of improvements in handling of InstaDMG
	
	def restoreImageToVolume(self, targetVolume):
		
		# ---- validate input and sanity check
		
		# targetVolume should be a container of type volume (not dmg)
		if not hasattr(targetVolume, 'isContainerType') or not targetVolume.isContainerType('volume') or targetVolume.isContainerType('dmg'):
			raise ValueError('Unable to restore onto: ' + str(targetVolume))
		
		if self.outputFilePath is None:
			raise RuntimeError('Restoring a volume requires that the image have been built')
		
		# ---- process
		
		# unmount the volume
		targetVolume.unmount()
		
		# restore the image onto the volume by bsd path
		asrCommand = ['/usr/sbin/asr', 'restore', '--verbose', '--source', self.outputFilePath, '--target', targetVolume.bsdPath, '--erase', '--noprompt']
		managedSubprocess(asrCommand)
		
		# bless the volume so that it is bootable
		blessCommand = ['/usr/sbin/bless', '--device', targetVolume.bsdPath, '--verbose']
		managedSubprocess(blessCommand)
		
		# bless the volume so that it is the nextboot device
		blessCommand = ['/usr/sbin/bless', '--device', targetVolume.bsdPath, '--setBoot', '--nextonly', '--verbose']
		managedSubprocess(blessCommand)
		
		# reboot
		rebootCommand = ['/usr/bin/osascript', '-e', 'tell application "System Events" to restart']
		managedSubprocess(rebootCommand)
	
#--------------------------------MAIN--------------------------------

def main ():
	import optparse
	
	# ------- defaults -------
	
	outputVolumeName	= "MacintoshHD"
	outputFileName		= str(datetime.date.today().month) + "-" + str(datetime.date.today().day) + "-" + str(datetime.date.today().year)
	
	# ---- parse options ----
	
	def print_version(option, opt, value, optionsParser):
		optionsParser.print_version()
		sys.exit(0)
	
	optionsParser = optparse.OptionParser("%prog [options] catalogFile1 [catalogFile2 ...]", version="%%prog %s" % versionString)
	optionsParser.remove_option('--version')
	optionsParser.add_option("-v", "--version", action="callback", callback=print_version, help="Print the version number and quit")
	
	# catalog items
	
	optionsParser.add_option("-a", "--add-catalog", action="append", type="string", dest="addOnCatalogFiles", help="Add the items in this catalog file to all catalog files processed. Can be called multiple times", metavar="FILE_PATH")
	
	# instaDMG options
	
	optionsParser.add_option("-p", "--process", action="store_true", default=False, dest="processWithInstaDMG", help="Run InstaDMG for each catalog file processed")
	optionsParser.add_option("", "--instadmg-scratch-folder", action="store", dest="instadmgScratchFolder", default=None, type="string", metavar="FOLDER_PATH", help="Tell InstaDMG to use FOLDER_PATH as the scratch folder")
	optionsParser.add_option("", "--instadmg-output-folder", action="store", dest="instadmgOutputFolder", default=None, type="string", metavar="FOLDER_PATH", help="Tell InstaDMG to place the output image in FOLDER_PATH")
	
	# source folder options
	
	optionsParser.add_option('', '--add-catalog-folder', action='append', default=None, type='string', dest='catalogFolders', help='Set the folders searched for catalog files', metavar="FILE_PATH")
	optionsParser.add_option('', '--set-cache-folder', action='store', default=None, type='string', dest='cacheFolder', help='Set the folder used to store downloaded files', metavar="FILE_PATH")
	optionsParser.add_option('', '--add-source-folder', action='append', default=[], type='string', dest='searchFolders', help='Set the folders searched for items to install', metavar="FILE_PATH")
	
	# post-processing
	
	optionsParser.add_option('', '--restore-onto-volume', default=None, type='string', dest='restoreTarget', help='After creating the image, restore onto volume. WARNING: this will destroy all data on the volume', metavar="VOLUME")
	
	# run the parser
	
	options, catalogFiles = optionsParser.parse_args()
	
	# ---- police options
	
	# catalogFiles
	if len(catalogFiles) < 1:
		optionsParser.error("At least one catalog file is required")
	
	if options.processWithInstaDMG is True:
		
		# check that we are running as root
		if os.getuid() != 0:
			optionsParser.error("When using the -p/--process flag this must be run as root (sudo is fine)")
		
		# instadmgScratchFolder
		if options.instadmgScratchFolder is not None and not os.path.isdir(options.instadmgScratchFolder):
			optionsParser.error("The --instadmg-scratch-folder option requires a valid folder path, but got: %s" % options.instadmgScratchFolder)
		
		# instadmgOutputFolder
		if options.instadmgOutputFolder is not None and not os.path.isdir(options.instadmgOutputFolder):
			optionsParser.error("The instadmg-output-folder option requires a valid folder path, but got: %s" % options.instadmgOutputFolder)
		
		# restoreTarget
		if options.restoreTarget is not None:
			
			if len(catalogFiles) > 1:
				optionsParser.error('When using the --restore-onto-volume option option only a single catalog file can be processed')
			
			try:
				options.restoreTarget = container(options.restoreTarget)
			except:
				optionsParser.error("Could not understand the value of the --restore-onto-volume option: " + str(options.restoreTarget))
			
			if not options.restoreTarget.isContainerType('volume') or options.restoreTarget.isContainerType('dmg'):
				optionsParser.error("The --restore-onto-volume option can only accept volumes on a HD, not dmgs or folder-like objects: " + str(options.restoreTarget))
		
	else:
		
		# instadmgScratchFolder, instadmgOutputFolder, and restoreTarget are meaningless without the --process option
		for optionName, optionVariable in {
			'--instadmg-scratch-folder':'instadmgScratchFolder',
			'--instadmg-output-folder':'instadmgOutputFolder',
			'--restore-onto-volume':'restoreTarget'
		}.items():
			if getattr(options, optionVariable) is not None:
				optionsParser.error("The %s option requires the -p/--process option to also be enabled" % optionName)
	
	# ---- process options

	if options.catalogFolders is None:
		options.catalogFolders = commonConfiguration.standardCatalogFolder
		
	baseCatalogFiles = []
	for thisCatalogFile in catalogFiles:
		try:
			baseCatalogFiles.append(instaUpToDate.getCatalogFullPath(thisCatalogFile, options.catalogFolders))
			
		except commonExceptions.CatalogNotFoundException:
			optionsParser.error("There does not seem to be a catalog file at: %s" % thisCatalogFile)
	
	addOnCatalogFiles = []
	if options.addOnCatalogFiles is not None:
		for thisCatalogFile in options.addOnCatalogFiles:
			try:
				addOnCatalogFiles.append(instaUpToDate.getCatalogFullPath(thisCatalogFile, options.catalogFolders))
			
			except commonExceptions.CatalogNotFoundException:
				optionsParser.error("There does not seem to be a catalog file at: %s" % thisCatalogFile)
	
	if options.cacheFolder is None:
		options.cacheFolder = commonConfiguration.standardCacheFolder
	
	if commonConfiguration.standardUserItemsFolder not in options.searchFolders:
		options.searchFolders.append(commonConfiguration.standardUserItemsFolder)
	
	# ----- setup system ----
	
	# ToDo: evaluate removing these
	
	try:
		cacheController.setCacheFolder(options.cacheFolder)
	except ValueError, error:
		optionsParser.error(error)
	
	try:
		cacheController.addSourceFolders(options.searchFolders)
	except ValueError, error:
		optionsParser.error(error)	
	
	# ----- run process -----
	
	controllers = []
	# create the InstaUp2Date controllers
	for catalogFilePath in baseCatalogFiles:
		
		sectionFolders = None
		if options.processWithInstaDMG is True:
			tempFolder = tempFolderManager.getNewTempFolder(prefix='items-')
			
			sectionFolders = [
				{"folderPath":tempFolder, "sections":["OS Updates", "System Settings", "Apple Updates", "Third Party Software", "Third Party Settings", "Software Settings"]}
			]
		else:
			sectionFolders = [
				{"folderPath":os.path.join(commonConfiguration.pathToInstaDMGFolder, "InstallerFiles", "BaseUpdates"), "sections":["OS Updates", "System Settings"]},
				{"folderPath":os.path.join(commonConfiguration.pathToInstaDMGFolder, "InstallerFiles", "CustomPKG"), "sections":["Apple Updates", "Third Party Software", "Third Party Settings", "Software Settings"]}
			]
		
		controllers.append(instaUpToDate(catalogFilePath, sectionFolders, options.catalogFolders)) # note: we have already sanitized catalogFilePath
	
	# process the catalog files
	for thisController in controllers:
		print('\nParsing the catalog files for ' + thisController.getMainCatalogName())
		thisController.parseCatalogFile()
		
		# add any additional catalogs to this one
		for addOnCatalogFile in addOnCatalogFiles:
			thisController.parseCatalogFile(addOnCatalogFile)
	
	# find all of the items
	for thisController in controllers:
		print('\nFinding and validating the sources for ' + thisController.getMainCatalogName())
		thisController.findItems()
	
	# find the os installer disc
	for thisController in controllers:
		print('\nFinding the Installer disc for ' + thisController.getMainCatalogName())
		foundInstallerDiscs = None
		if thisController.installerDiscBuilds is not None:
			foundInstallerDiscs = findInstallerDisc.findInstallerDisc(allowedBuilds=thisController.installerDiscBuilds)
		else:
			foundInstallerDiscs = findInstallerDisc.findInstallerDisc()
		
		thisController.installerDiscPath = foundInstallerDiscs['InstallerDisc'].getStoragePath()
		print('\tFound Installer Disc:\t' + thisController.installerDiscPath)
		
		for thisDisc in foundInstallerDiscs['SupportingDiscs']:
			thisDiscPath = thisDisc.getStoragePath()
			print('\tFound Supporting Disc:\t' + thisDiscPath)
			thisController.supportingDiscPath.append(thisDiscPath)
	
	# run the job
	for thisController in controllers:
		print('\nSetting up for ' + thisController.getMainCatalogName())
		
		if options.processWithInstaDMG is False:
			# empty the folders
			print('\tCleaning InstaDMG folders')
			thisController.cleanInstaDMGFolders()
		
		# create the folder strucutres needed
		print('\tSetting up InstaDMG folders')
		thisController.arrangeFolders()
		
		if options.processWithInstaDMG is True:
			# the run succeded, and it has been requested to run InstaDMG
			thisController.runInstaDMG(scratchFolder=options.instadmgScratchFolder, outputFolder=options.instadmgOutputFolder)
			
			if options.restoreTarget is not None:
				print('\nRestoring to volume' + options.restoreTarget.getDisplayName())
				thisController.restoreImageToVolume(options.restoreTarget)
	
	print('\nDone')
		
#------------------------------END MAIN------------------------------

if __name__ == "__main__":
    main()
