#!/usr/bin/python

# InstaUpToDate
#
#	This script parses one or more catalog files to setup InstaDMG

import os, sys, re
import hashlib, urlparse, subprocess, datetime

import Resources.commonConfiguration	as commonConfiguration
from Resources.tempFolderManager		import tempFolderManager
from Resources.installerPackage			import installerPackage
from Resources.commonExceptions			import FileNotFoundException, CatalogNotFoundException

#------------------------------SETTINGS------------------------------

svnRevision					= int('$Revision$'.split(" ")[1])
versionString				= "0.5b (svn revision: %i)" % svnRevision

allowedCatalogFileSettings	= [ "ISO Language Code", "Output Volume Name", "Output File Name" ]

# these should be in the order they run in
systemSectionTypes			= [ "OS Updates", "System Settings" ]
addedSectionTypes			= [ "Apple Updates", "Third Party Software", "Third Party Settings", "Software Settings" ]	

#------------------------RUNTIME ADJUSTMENTS-------------------------

appleUpdatesFolderPath		= os.path.join(commonConfiguration.pathToInstaDMGFolder, "InstallerFiles", "BaseUpdates")
customPKGFolderPath			= os.path.join(commonConfiguration.pathToInstaDMGFolder, "InstallerFiles", "CustomPKG")

#-------------------------------CLASSES------------------------------

class instaUpToDate:
	"The central class to manage the process"
		
	#---------------------Class Variables-----------------------------
	
	sectionStartParser		= re.compile('^(?P<sectionName>[^\t]+):\s*(#.*)?$')
	packageLineParser		= re.compile('^\t(?P<displayName>[^\t]*)\t(?P<fileLocation>[^\t]+)\t(?P<fileChecksum>\S+)\s*(#.*)?$')
	emptyLineParser			= re.compile('^\s*(?P<comment>#.*)?$')
	settingLineParser		= re.compile('^(?P<variableName>[^=]+) = (?P<variableValue>.*)')
	includeLineParser		= re.compile('^\s*include-file:\s+(?P<location>.*)(\s*#.*)?$')
	
	fileExtensions			= ['.catalog']
	
	#--------------------Instance Variables---------------------------
	
	catalogFilePath			= None	# the main catalog file
	
	sectionFolders			= None
	
	packageGroups 			= None	# a Hash
	parsedFiles 			= None	# an Array, for loop checking
	
	# defaults
	outputVolumeNameDefault = "MacintoshHD"
	
	# things below this line will usually come from the first catalog file (top) that sets them
	catalogFileSettings		= None	# a hash

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
			return os.path.abspath(os.path.realpath(catalogFileInput))
		
		# cycle through the folders we have been given to see if it is there
		for thisFolder in catalogFolders:
			
			# try the simple path:
			if os.path.isfile( os.path.join(thisFolder, catalogFileInput) ):
				return os.path.abspath(os.path.realpath(os.path.join(thisFolder, catalogFileInput)))
			
			# try appending file extension(s)
			for thisExtension in myClass.fileExtensions:
				if os.path.isfile( os.path.join(thisFolder, catalogFileInput + thisExtension) ):
					return os.path.abspath(os.path.realpath(os.path.join(thisFolder, catalogFileInput + thisExtension)))
		
		raise CatalogNotFoundException("The file input is not one that getCatalogFullPath understands, or can find: %s" % catalogFileInput)
		
	#------------------------Functions--------------------------------
	
	def __init__(self, catalogFilePath, sectionFolders, catalogFolders):
		
		# set up section folders structure
		self.sectionFolders 		= []
		self.catalogFolders			= []
		self.packageGroups			= {}
		self.catalogFileSettings	= {}
		self.parsedFiles			= []
				
		# catalogFilePath
		if not os.path.exists(catalogFilePath):
			raise FileNotFoundException('The catalog file does not exist: ' + str(catalogFilePath))
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
		
		# --- runtime checks ----
		assert os.path.isfile(commonConfiguration.pathToInstaDMG), "InstaDMG was not where it was expected to be: %s" % commonConfiguration.pathToInstaDMG
	
	def getMainCatalogName(self):
		return os.path.splitext(os.path.basename(self.catalogFilePath))[0]
	
	def parseFile(self, fileLocation):
		
		global allowedCatalogFileSettings
					
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
			
			# ------- settings lines -------
			settingLineMatch = self.settingLineParser.search(line)
			if settingLineMatch:
				try:
					if allowedCatalogFileSettings.index( settingLineMatch.group("variableName") ):
						if not(self.catalogFileSettings.has_key( settingLineMatch.group("variableName") )):
							# Since it is not set, we can set it
							# TODO: log something if there is a conflict
							self.catalogFileSettings[settingLineMatch.group("variableName")] = settingLineMatch.group("variableValue")
				except:
					raise Exception('Unknown setting in catalog file: %s line number: %i\n%s' % (fileLocation, lineNumber, line)) # TODO: improve error handling
					
				continue
			
			# ----- file includes lines ----
			includeLineMatch = self.includeLineParser.search(line)
			if includeLineMatch:
				self.parseFile( self.getCatalogFullPath(includeLineMatch.group("location"), self.catalogFolders) )
				continue
			
			# ------- section lines --------
			sectionTitleMatch = self.sectionStartParser.search(line)
			if sectionTitleMatch:
				if sectionTitleMatch.group("sectionName") not in self.packageGroups and sectionTitleMatch.group("sectionName") != "Base OS Disk":
					raise Exception('Unknown section title: "%s" on line: %i of file: %s\n%s' % (sectionTitleMatch.group("sectionName"), lineNumber, fileLocation, line) ) # TODO: improve error handling
				
				currentSection = sectionTitleMatch.group("sectionName")
				continue
			
			# --------- item lines ---------
			packageLineMatch = self.packageLineParser.search(line)
			if packageLineMatch:
				if currentSection == None:
					# we have to have a place to put this
					raise Exception('Every item must belong to a section') # TODO: improve error handling
				
				thisPackage = installerPackage(
					displayName = packageLineMatch.group("displayName"),
					sourceLocation = packageLineMatch.group("fileLocation"),
					checksumString = packageLineMatch.group("fileChecksum"),
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
				thisItem.findItem()
	
	def arrangeFolders(self, sectionFolders=None):
		"Create the folder structure in the InstaDMG areas, and pop in soft-links to the items in the cache folder"
		
		assert isinstance(sectionFolders, list), "sectionfolders is required, and must be a list of dicts"
		
		import math
		
		for thisSectionFolder in sectionFolders:
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
				targetFilePath = os.path.realpath(os.path.join(updateFolder, targetFileName))
				
				if os.path.isabs(targetFilePath):
					os.symlink(thisItem.filePath, targetFilePath)
				else:
					pathFromTargetToSource = os.path.relpath(thisItem.filePath, os.path.dirname(targetFilePath))
					os.symlink(pathFromTargetToSource, targetFilePath)
				# ToDo: capture and better explain any errors here
				
				assert os.path.exists(targetFilePath), "Something went wrong linking from %s to %s" % (targetFilePath, pathFromTargetToSource) # this should catch bad links
				
				itemCounter += 1
				
		return True
	
	def setupInstaDMGFolders(self):
		'''Clean the chosen folders, and setup the package groups. This will only remove folders and symlinks, not actual data.'''
		
		assert isinstance(self.sectionFolders, list), "sectionfolders is required, and must be a list of dicts"
		
		for sectionFolder in self.sectionFolders:
			assert isinstance(sectionFolder, dict) and "folderPath" in sectionFolder and "sections" in sectionFolder, "sectionfolder information must be a dict with a 'folderPath' value, instead got: %s" % sectionFolder
			assert os.path.isdir(sectionFolder['folderPath']), "The sectionfolder did not seem to exist: %s" % sectionFolder['folderPath']
			assert os.path.isabs(sectionFolder['folderPath']), "setupInstaDMGFolders was passed a non-abs path to a folder: %s" % sectionFolder['folderPath']
			
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
		
		if self.catalogFileSettings.has_key("ISO Language Code"):
			instaDMGCommand += ["-i", self.catalogFileSettings["ISO Language Code"]]
			# TODO: check with installer to see if it will accept this language code
		
		if self.catalogFileSettings.has_key("Output Volume Name"):
			instaDMGCommand += ["-n", self.catalogFileSettings["Output Volume Name"]]
		
		if self.catalogFileSettings.has_key("Output File Name"):
			instaDMGCommand += ["-m", self.catalogFileSettings["Output File Name"]]
		
		if scratchFolder is not None:
			instaDMGCommand += ["-t", scratchFolder]
		
		for thisSectionFolder in self.sectionFolders:
			instaDMGCommand += ['-K', thisSectionFolder['folderPath']]
		
		if outputFolder is not None:
			instaDMGCommand += ["-o", outputFolder]

		print("\nRunning InstaDMG: %s\n" % " ".join(instaDMGCommand))
		# we should be in the same directory as InstaDMG
		
		subprocess.call(instaDMGCommand)
		# TODO: a lot of improvements in handling of InstaDMG

	
#--------------------------------MAIN--------------------------------

def main ():
	
	# ------- defaults -------
	
	outputVolumeName	= "MacintoshHD"
	outputFileName		= str(datetime.date.today().month) + "-" + str(datetime.date.today().day) + "-" + str(datetime.date.today().year)
	
	# ---- parse options ----
	
	def print_version(option, opt, value, optionsParser):
		optionsParser.print_version()
		sys.exit(0)
	
	import optparse
	optionsParser = optparse.OptionParser("%prog [options] catalogFile1 [catalogFile2 ...]", version="%%prog %s" % versionString)
	optionsParser.remove_option('--version')

	
	optionsParser.add_option("-a", "--add-catalog", action="append", type="string", dest="addOnCatalogFiles", help="Add the items in this catalog file to all catalog files processed. Can be called multiple times", metavar="FILE_PATH")
	optionsParser.add_option("-v", "--version", action="callback", callback=print_version, help="Print the version number and quit")
	
	# instaDMG options
	
	optionsParser.add_option("-p", "--process", action="store_true", default=False, dest="processWithInstaDMG", help="Run InstaDMG for each catalog file processed")
	optionsParser.add_option("", "--instadmg-scratch-folder", action="store", dest="instadmgScratchFolder", default=None, type="string", metavar="FOLDER_PATH", help="Tell InstaDMG to use FOLDER_PATH as the scratch folder")
	optionsParser.add_option("", "--instadmg-output-folder", action="store", dest="instadmgOutputFolder", default=None, type="string", metavar="FOLDER_PATH", help="Tell InstaDMG to place the output image in FOLDER_PATH")
	
	# source folder options
	
	optionsParser.add_option('', '--add-catalog-folder', action='append', default=None, type='string', dest='catalogFolders', help='Set the folders searched for catalog files', metavar="FILE_PATH")
	optionsParser.add_option('', '--set-cache-folder', action='store', default=None, type='string', dest='cacheFolder', help='Set the folder used to store downloaded files', metavar="FILE_PATH")
	optionsParser.add_option('', '--add-source-folder', action='append', default=None, type='string', dest='searchFolders', help='Set the folders searched for items to install', metavar="FILE_PATH")
	
	
	options, catalogFiles = optionsParser.parse_args()
	
	# --- police options ----
	
	if len(catalogFiles) < 1:
		optionsParser.error("At least one catalog file is required")
	
	if (options.instadmgScratchFolder != None or options.instadmgOutputFolder != None) and options.processWithInstaDMG == False:
		optionsParser.error("The instadmg-scratch-folder and instadmg-output-folder options require the -p/--process option to also be enabled")
	
	if options.instadmgScratchFolder != None and not os.path.isdir(options.instadmgScratchFolder):
		optionsParser.error("The instadmg-scratch-folder option requires a valid folder path, but got: %s" % options.instadmgScratchFolder)
	
	if options.instadmgOutputFolder != None and not os.path.isdir(options.instadmgOutputFolder):
		optionsParser.error("The instadmg-output-folder option requires a valid folder path, but got: %s" % options.instadmgOutputFolder)
	
	# if we are running InstaDMG, then we need to be running as root
	if options.processWithInstaDMG is True and os.getuid() != 0:
		optionsParser.error("When using the -p/--process flag this must be run as root (sudo is fine)")
	
	# --- process options ---

	if options.catalogFolders is None:
		options.catalogFolders = commonConfiguration.standardCatalogFolder
		
	baseCatalogFiles = []
	for thisCatalogFile in catalogFiles:
		try:
			baseCatalogFiles.append(instaUpToDate.getCatalogFullPath(thisCatalogFile, options.catalogFolders))
			
		except CatalogNotFoundException:
			optionsParser.error("There does not seem to be a catalog file at: %s" % thisCatalogFile)
	
	addOnCatalogFiles = []
	if options.addOnCatalogFiles is not None:
		for thisCatalogFile in options.addOnCatalogFiles:
			try:
				addOnCatalogFiles.append(instaUpToDate.getCatalogFullPath(thisCatalogFile, options.catalogFolders))
			
			except CatalogNotFoundException:
				optionsParser.error("There does not seem to be a catalog file at: %s" % thisCatalogFile)
	
	sectionFolders = None
	if options.processWithInstaDMG is True:
		tempFolder = tempFolderManager.getNewTempFolder(prefix='InstaUp2DateFolder-')
		
		sectionFolders = [
			{"folderPath":tempFolder, "sections":["OS Updates", "System Settings", "Apple Updates", "Third Party Software", "Third Party Settings", "Software Settings"]}
		]
	else:
		sectionFolders = [
			{"folderPath":os.path.join(commonConfiguration.pathToInstaDMGFolder, "InstallerFiles", "BaseUpdates"), "sections":["OS Updates", "System Settings"]},
			{"folderPath":os.path.join(commonConfiguration.pathToInstaDMGFolder, "InstallerFiles", "CustomPKG"), "sections":["Apple Updates", "Third Party Software", "Third Party Settings", "Software Settings"]}
		]
	
	if options.cacheFolder is None:
		options.cacheFolder = commonConfiguration.standardCacheFolder
	
	if options.searchFolders is None:
		options.searchFolders = commonConfiguration.standardUserItemsFolder
	
	# ----- setup system ----
	
	try:
		installerPackage.setCacheFolder(options.cacheFolder)
	except ValueError, error:
		optionsParser.error(error)
	
	try:
		installerPackage.addSourceFolders(options.searchFolders)
	except ValueError, error:
		optionsParser.error(error)	
	
	# ----- run process -----
	
	controllers = []
	# create the InstaUp2Date controllers
	for catalogFilePath in baseCatalogFiles:
		controllers.append(instaUpToDate(catalogFilePath, sectionFolders, options.catalogFolders)) # note: we have already sanitized catalogFilePath
	
	# process the catalog files
	for thisController in controllers:
		print('\nParsing the catalog files for ' + thisController.getMainCatalogName())
		thisController.parseFile(catalogFilePath)
		
		# add any additional catalogs to this one
		for addOnCatalogFile in addOnCatalogFiles:
			thisController.parseFile(addOnCatalogFile)
	
	# find all of the items
	for thisController in controllers:
		print('\nFinding and validating the sources for ' + thisController.getMainCatalogName())
		thisController.findItems()
	
	# run the job
	for thisController in controllers:
		
		# empty the folders
		thisController.setupInstaDMGFolders()
		
		# create the folder strucutres needed
		thisController.arrangeFolders(sectionFolders=sectionFolders)
		
		if options.processWithInstaDMG == True:
			# the run succeded, and it has been requested to run InstaDMG
			thisController.runInstaDMG(scratchFolder=options.instadmgScratchFolder, outputFolder=options.instadmgOutputFolder)
		
#------------------------------END MAIN------------------------------

if __name__ == "__main__":
    main()
