#!/usr/bin/python

# InstaUpToDate
#
#	This script parses one or more catalog files to fill in the 

import os, sys, re
import hashlib, urlparse, urllib, urllib2, tempfile, shutil, subprocess
import Foundation, checksum
from datetime import date

#------------------------------SETTINGS------------------------------

svnRevision					= int('$Revision$'.split(" ")[1])
versionString				= "0.5b (svn revision: %i)" % svnRevision

relativePathToInstaDMG		= "../../" # the relative path between InstaUp2date and InstaDMG
relativePathFromInstaDMG	= "AddOns/InstaUp2Date/"
instaDMGName				= "instadmg.bash" # name of the InstaDMG executable

# this group needs to be relative to InstaDMG
appleUpdatesFolder			= "InstallerFiles/BaseUpdates"
customPKGFolder 			= "InstallerFiles/CustomPKG"
userSuppliedPKGFolder		= "InstallerFiles/InstaUp2DatePackages" # user-created packages

catalogFolderName			= "CatalogFiles"
catalogFileExension			= ".catalog"

cacheFolder					= "Caches/InstaUp2DateCache" # the location of the cache folder relative to the InstaDMG folder

READ_CHUNK_SIZE				= 1024; # how large a chunk to grab while checksumming. changing this can affect performance

baseOSSectionName			= "Base OS Disk"

allowedCatalogFileSettings	= [ "ISO Language Code", "Output Volume Name", "Output File Name" ]

# these should be in the order they run in
systemSectionTypes			= [ "OS Updates", "System Settings" ]
addedSectionTypes			= [ "Apple Updates", "Third Party Software", "Third Party Settings", "Software Settings" ]	

#------------------------RUNTIME ADJUSTMENTS-------------------------

absPathToInstaDMGFolder		= os.path.normpath(os.path.join( os.path.dirname(sys.argv[0]), relativePathToInstaDMG ))

appleUpdatesFolderPath		= os.path.join(absPathToInstaDMGFolder, appleUpdatesFolder)
customPKGFolderPath			= os.path.join(absPathToInstaDMGFolder, customPKGFolder)

userSuppliedPKGFolderPath	= os.path.join(absPathToInstaDMGFolder, userSuppliedPKGFolder)
cacheFolderPath				= os.path.join(absPathToInstaDMGFolder, cacheFolder)

catalogFolderPath			= os.path.join(os.path.dirname(sys.argv[0]), catalogFolderName)

#-------------------------------CLASSES------------------------------

class CatalogNotFoundException(Exception):
	pass

class FileNotFoundException(Exception):
	pass

class instaUpToDate:
	"The central class to manage the process"
		
	#---------------------Class Variables-----------------------------
	
	sectionStartParser	= re.compile('^(?P<sectionName>[^\t]+):\s*(#.*)?$')
	packageLineParser	= re.compile('^\t(?P<displayName>[^\t]*)\t(?P<fileLocation>[^\t]+)\t(?P<fileChecksum>\S+)\s*(#.*)?$')
	emptyLineParser		= re.compile('^\s*(?P<comment>#.*)?$')
	settingLineParser	= re.compile('^(?P<variableName>[^=]+) = (?P<variableValue>.*)')
	includeLineParser	= re.compile('^\s*include-file:\s+(?P<location>.*)(\s*#.*)?$')
	
	#--------------------Instance Variables---------------------------

	packageGroups 			= None	# an Array, init-ed in cleanInstaDMGFolders
	parsedFiles 			= None	# an Array, for loop checking
	
	absPathToInstaDMGFolder	= None
	
	# defaults
	outputVolumeNameDefault = "MacintoshHD"
	
	# things below this line will usually come from the first catalog file (top) that sets them
	catalogFileSettings		= None	# a hash

	#---------------------Class Functions-----------------------------
	
	@classmethod
	def getCatalogFullPath(myClass, catalogFileInput):
		'''Classmethod to translate input to a abs-path from one of the accepted formats (checked in this order):
	- ToDo: http or https reference (will be downloaded and temporary filepath returned)
	- absolute path to a file
	- catalog file name within the CatalogFiles folder, with or without the .catalog extension
	- relative path from CatalogFiles folder, with or without the .catalog extension
	- relative path from the pwd, with or without the .catalog extension
'''
		global catalogFolderName, catalogFileExension
		
		absPathToCatalogFilesFolder = os.path.abspath( os.path.join(os.path.dirname(sys.argv[0]), catalogFolderName) )
		
		# http/https url
		if urlparse.urlparse(catalogFileInput).scheme in ["http", "https"]:
			raise Exception("URL catalog files are not done yet")
			# ToDo: download the files, then return the path
		
		# ToDo: rework this for better url handling
		
		# absolute path to a file
		elif os.path.isabs(catalogFileInput):
			return catalogFileInput
		
		# file name in the CatalogFiles folder, or relative path
		elif os.path.isfile(os.path.join(absPathToCatalogFilesFolder, catalogFileInput)) or os.path.isfile(os.path.join(absPathToCatalogFilesFolder, catalogFileInput + catalogFileExension)):
			if catalogFileInput.lower().endswith(catalogFileExension):
				return os.path.join(absPathToCatalogFilesFolder, catalogFileInput)
			else:
				return os.path.join(absPathToCatalogFilesFolder, catalogFileInput + catalogFileExension)
		
		# file path relative to pwd
		elif os.path.isfile(catalogFileInput) or os.path.isfile(catalogFileInput + catalogFileExension):
			if catalogFileInput.lower().endswith(catalogFileExension):
				return os.path.abspath(catalogFileInput)
			else:
				return os.path.abspath(catalogFileInput + catalogFileExension)
		
		else:
			raise CatalogNotFoundException("The file input is not one that getCatalogFullPath understands, or can find: %s" % catalogFileInput)
		
	#------------------------Functions--------------------------------
	
	def runtimeChecks(self, runStyle="classic"):
		'''Some sanity checks to make sure that things are not going to fail later'''
		
		#global relativePathToInstaDMG, catalogFolderName, cacheFolder, userSuppliedPKGFolder
		#global appleUpdatesFolder, customPKGFolder
		
		# Note on runStyle:
		#	"classic": use the "BaseUpdates" and "CustomPKG" folders
		#	"tempFolder": use a temporary to hold all of the update links, deleted at close
		
		# --- generic checks ----
		
		assert os.path.isfile( os.path.join(absPathToInstaDMGFolder, instaDMGName) ), "InstaDMG was not where it was expected to be: %s" % os.path.join(absPathToInstaDMGFolder, instaDMGName)
		assert os.path.isdir(catalogFolderPath), "The catalog files folder was not where it was expected to be: %s" % catalogFolderPath
		assert os.path.isdir(userSuppliedPKGFolderPath), "The catalog files folder was not where it was expected to be: %s" % userSuppliedPKGFolderPath
		assert os.path.isdir(cacheFolderPath), "The instaDMG cache folder was not where it was expected to be: %s" % cacheFolderPath
		
		# --- classic checks ----
		if runStyle == "classic":
			assert os.path.isdir(appleUpdatesFolderPath), "The BaseUpdates folder was not where it was expected to be: %s" % appleUpdatesFolderPath
			assert os.path.isdir(customPKGFolderPath), "The CustomPKGs folder was not where it was expected to be: %s" % customPKGFolderPath
		
		# -- tempFolder checks --
		elif runStyle == "tempFolder":
			pass
		
	
	def parseFile(self, fileLocation):
		
		global catalogFileExension
		global allowedCatalogFileSettings
					
		# the file passed could be an absolute path, a relative path, or a catalog file name
		#	the first two are handled without a special section, but the name needs some work
		
		fileLocation = self.getCatalogFullPath(fileLocation) # there should not be an error here, since we have already validated it
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
				self.parseFile( self.getCatalogFullPath(includeLineMatch.group("location")) )
				continue
			
			# ------- section lines --------
			sectionTitleMatch = self.sectionStartParser.search(line)
			if sectionTitleMatch:
				if sectionTitleMatch.group("sectionName") not in self.packageGroups and sectionTitleMatch.group("sectionName") != baseOSSectionName:
					raise Exception('Unknown section title: "%s" on line: %i of file: %s\n%s' % (sectionTitleMatch.group("sectionName"), lineNumber, fileLocation, line) ) # TODO: improve error handling
				
				currentSection = sectionTitleMatch.group("sectionName")
				continue
			
			# --------- item lines ---------
			packageLineMatch = self.packageLineParser.search(line)
			if packageLineMatch:
				if currentSection == None:
					# we have to have a place to put this
					raise Exception() # TODO: improve error handling
				
				thisPackage = installerPackage(
					displayName = packageLineMatch.group("displayName"),
					sourceLocation = packageLineMatch.group("fileLocation"),
					checksumString = packageLineMatch.group("fileChecksum"),
					mainCacheFolder = cacheFolderPath,
					additionalCacheFolders = userSuppliedPKGFolderPath
				)
		
				thisPackage.printPackageInformation(tabsToPrefix=1)
				
				self.packageGroups[currentSection].append(thisPackage)
				
				continue
				
			# if we got here, the line was not good
			raise Exception('Error in config file: %s line number: %i\n%s' % (fileLocation, lineNumber, line)) # TODO: improve error handling
			
		inputfile.close()
		
	def arrangeFolders(self):
		"Create the folder structure in the InstaDMG areas, and pop in soft-links to the items in the cache folder"
		
		import math
		
		groupings = [ [systemSectionTypes, appleUpdatesFolderPath], [addedSectionTypes, customPKGFolderPath] ]
		for sectionTypes, updateFolder in groupings:
			
			itemsToProcess = []
			for thisSection in sectionTypes:
				itemsToProcess += self.packageGroups[thisSection]
			
			# Get the number of leading 0s we need
			leadingZeroes = int(math.log10(len(itemsToProcess)))
			fileNameFormat = '%0' + str(leadingZeroes) + "d %s"
			
			# Create symlinks for all of the items
			itemCounter = 1
			for thisItem in itemsToProcess:
				
				targetFileName = fileNameFormat % (itemCounter, thisItem.displayName)
				targetFilePath = os.path.join(updateFolder, targetFileName)
				pathFromTargetToSource = os.path.relpath(thisItem.filePath, os.path.dirname(targetFilePath))
				
				os.symlink(pathFromTargetToSource, targetFilePath)
				# ToDo: capture and better explain any errors here
				
				assert os.path.exists(targetFilePath), "Something went wrong linking from %s to %s" % (targetFilePath, pathFromTargetToSource) # this should catch bad links
				
				itemCounter += 1
				
		return True

	def cleanInstaDMGFolders(self):
		"This will go through and clean out the InstaDMG folders. It will choke on any real files in the hirarchy (it expects soft-links). It also cleans and sets-up instance variables for a new run."
		
		# clean out the instance variables
		self.packageGroups = {}
		for group in systemSectionTypes + addedSectionTypes:
			self.packageGroups[group] = []
				
		for instaDMGFolder in [appleUpdatesFolderPath, customPKGFolderPath]: # these should be abspaths
			for subFolder in os.listdir(instaDMGFolder):
				thisFolder = os.path.join(instaDMGFolder, subFolder)
				
				if re.match("\.", subFolder):
					continue
				
				if os.path.islink(thisFolder):
					os.remove(thisFolder)
					continue
				
				if not(os.path.isdir(thisFolder)):
					raise Exception("Not a folder: %s" % thisFolder) # TODO: improve error handling
				
				for thisItem in os.listdir(thisFolder):
					thisItemPath = os.path.join(thisFolder, thisItem)
					
					if not(os.path.islink(thisItemPath)) and not(re.match("\.DS_Store", thisItem)) and not(re.match("\.svn", thisItem)):
						raise Exception("Not a soft link: %s" % thisItemPath) # TODO: improve error handling
					
					if not(re.match("\.svn", thisItem)):
						os.remove(thisItemPath)
					
				os.rmdir(thisFolder)
	
	def runInstaDMG(self, scratchFolder=None, outputFolder=None):
		global instaDMGName
		
		instaDMGCommand			= [ os.path.join( os.getcwd(), instaDMGName ), "-f" ]
		
		if self.catalogFileSettings.has_key("ISO Language Code"):
			instaDMGCommand += ["-i", self.catalogFileSettings["ISO Language Code"]]
			# TODO: check with installer to see if it will accept this language code
		
		if self.catalogFileSettings.has_key("Output Volume Name"):
			instaDMGCommand += ["-n", self.catalogFileSettings["Output Volume Name"]]
		
		if self.catalogFileSettings.has_key("Output File Name"):
			instaDMGCommand += ["-m", self.catalogFileSettings["Output File Name"]]
		
		
		if scratchFolder != None:
			instaDMGCommand += ["-t", scratchFolder]
		
		if outputFolder != None:
			instaDMGCommand += ["-o", outputFolder]

		
		print("Running InstaDMG:\n\n")
		# we should be in the same directory as InstaDMG
		
		subprocess.call(instaDMGCommand)
		# TODO: a lot of improvements in handling of InstaDMG

class installerPackage:
	"This class represents a .pkg installer, and does much of the work."
		
	#---------------------Class Variables-----------------------------
	
	
	#--------------------Instance Variables---------------------------
	
	displayName			= None		# arbitrary text string for display	
	
	checksum			= None
	checksumType		= None
	
	source				= None
	filePath			= None		# a local location to link to
	
	#------------------------Functions--------------------------------
	
	def __init__(self, displayName, sourceLocation, checksumString, mainCacheFolder, additionalCacheFolders=None):	
		
		assert isinstance(displayName, str), "Recieved an empty or invalid name"
		assert sourceLocation is not None, "Recieved an empty location"
		assert isinstance(checksumString, str) is not None, "Recieved an empty or invalid checksum string"
		assert additionalCacheFolders is None or isinstance(additionalCacheFolders, str) or isinstance(additionalCacheFolders, list)
		
		assert checksumString.count(":") > 0, "Checksum string is not of the right format"
		checksumType, checksumValue = checksumString.split(":", 1)
		assert checksumType is not None, "There was no checksum type"
		assert checksumValue is not None, "There was no checksum"
		
		# confirm that hashlib supports the hash type:
		try:
			hashlib.new(checksumType)
		except ValueError:
			raise Exception("Hash type: %s is not supported by hashlib" % checksumType)
		
		# set basic values
		self.source = sourceLocation
		self.displayName = displayName
		self.checksum = checksumValue
		self.checksumType = checksumType
		
		# put together the list of cache folders
		cacheFolders = [mainCacheFolder]
		if isinstance(additionalCacheFolders, str):
			cacheFolders.append(additionalCacheFolders)
		elif isinstance(additionalCacheFolders, list):
			cacheFolders += additionalCacheFolders
		
		# values we need to find or create
		cacheFilePath = None
		
		print("Looking for %s" % displayName)
		
		# check the caches for an item with this checksum
		cacheFilePath = self.checkCacheForItem(None, checksumType, checksumValue, cacheFolders)
		if cacheFilePath is not None:
			print("	Found in cache folder by checksum")
		
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
					filePath = self.checkCacheForItem(filePath, checksumType, checksumValue, cacheFolders)
					
				# try this as a relative path from cwd
				elif not os.path.isabs(filePath) and os.path.exists(filePath):
					filePath = os.path.abspath(filePath)
				
				# try this path in each of the cache folders
				elif not os.path.isabs(filePath):
					
					for cacheFolder in cacheFolders:
						
						if os.path.exists( os.path.join(cacheFolder, filePath) ):
							filePath = os.path.abspath(os.path.join(cacheFolder, filePath))
							break
				
				# final check to make sure the file exists
				if not os.path.exists(filePath):
					raise FileNotFoundException("The referenced file/folder does not exist: %s" % filePath)
				
				print("	Found at the provided path")
				
				cacheFilePath = filePath
				
			elif parsedSourceLocationURL.scheme in ["http", "https"]:
				# url to download
				
				# guess the name from the URL
				cacheFilePath = self.checkCacheForItem(os.path.basename(parsedSourceLocationURL.path), checksumType, checksumValue, cacheFolders)
				if cacheFilePath is not None:
					print("	Found using name in URL")
					
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
					cacheFilePath = self.checkCacheForItem(fileName, checksumType, checksumValue, cacheFolders)
					
					if cacheFilePath is not None:
						print("	Found using name in a redirected URL or content disposition header")
					
					if cacheFilePath is None:
						# continue downloading into the main cache folder
						hashGenerator = hashlib.new(checksumType)
						
						targetFilePath = os.path.join(mainCacheFolder, os.path.splitext(fileName)[0] + " " + checksumType + "-" + checksumValue + os.path.splitext(fileName)[1])
						
						checksum.cheksumFileObject(hashGenerator, readFile, fileName, expectedLength, chunkSize=1024*100, fileType="download", copyToPath=targetFilePath, reportProgress=True, tabsToPrefix=1)
						
						if hashGenerator.hexdigest() != checksumValue:
							os.unlink(targetFilePath)
							raise Exception("Downloaded file did not match checksum: %s" % sourceLocation)
						
						cacheFilePath = targetFilePath
						print("	Downloaded and verified")
							
					readFile.close()
				
			else:
				raise Exception("Unknown or unsupported source location type: %s" % sourceLocation)
		
		# at this point we know that we have a file at cacheFilePath
		self.filePath = cacheFilePath
	
	def printPackageInformation(self, tabsToPrefix=0):
		
		print('''%(tabPrefix)sDisplay Name: %(displayName)s
%(tabPrefix)sChecksum:	%(checksumType)s:%(checksum)s
%(tabPrefix)sSource:		%(source)s
%(tabPrefix)sCache:		%(cacheLocation)s
''' % { "tabPrefix":"\t" * tabsToPrefix, "displayName":self.displayName, "checksum":self.checksum, "checksumType":self.checksumType, "source":self.source, "cacheLocation":self.filePath })
	
	@classmethod
	def checkCacheForItem(myClass, itemName, checksumType, checksumValue, cacheFolders):
		'''Look through the caches for this file'''
		
		assert checksumType is not None, "Checksum Type is required"
		assert checksumValue is not None, "Checksum is required"
		assert cacheFolders is not None, "Cache folders required"
		
		if isinstance(cacheFolders, str):
			cacheFolders = [cacheFolders]
		elif isinstance(cacheFolders, list):
			pass # in the right format
		else:
			raise Exception("cacheFolders is not the right format: %s" % cacheFolders)
		
		# ToDo: put in logging of this event
		
		# create a list of cache folder to check
		
		for thisCacheFolder in cacheFolders:
			assert os.path.isdir(thisCacheFolder), "The cache folder does not exist or is not a folder: %s" % thisCacheFolder
			
			# ToDo: think through the idea of having nested folders
			for thisItemName in os.listdir(thisCacheFolder):
				
				# check for an item with the same name
				if itemName is not None and thisItemName == itemName:
					if checksumValue == checksum.checksum(os.path.join(thisCacheFolder, thisItemName), checksumType, tabsToPrefix=1)['checksum']:
						return os.path.join(thisCacheFolder, thisItemName)
				
				# check to see if the last "word" of the item name is the checksum string and is the same
				itemNameStriped = os.path.splitext(thisItemName)[0]
				if itemNameStriped.split(" ")[-1] == checksumType + "-" + checksumValue:
					if checksumValue == checksum.checksum(os.path.join(thisCacheFolder, thisItemName), checksumType, tabsToPrefix=1)['checksum']:
						return os.path.join(thisCacheFolder, thisItemName)
		
		return None
	
#--------------------------------MAIN--------------------------------

def print_version(option, opt, value, parser):
	print("InstaUp2Date version %s" % versionString)
	sys.exit(0)

def main ():
	
	global catalogFolder
	
	# ------- defaults -------
	
	outputVolumeName	= "MacintoshHD"
	outputFileName		= str(date.today().month) + "-" + str(date.today().day) + "-" + str(date.today().year)
	
	# ---- parse options ----
	
	import optparse
	optionsParser = optparse.OptionParser("%prog [options] catalogFile1 [catalogFile2 ...]" )
	optionsParser.add_option("-a", "--add-catalog", action="append", type="string", dest="addOnCatalogFiles", help="Add the items in this catalog file to all catalog files processed. Can be called multiple times", metavar="FILE_PATH")
	optionsParser.add_option("-p", "--process", action="store_true", default=False, dest="processWithInstaDMG", help="Run InstaDMG for each catalog file processed")
	optionsParser.add_option("-v", "--version", action="callback", callback=print_version, help="Print the version number and quit")
	optionsParser.add_option("", "--instadmg-scratch-folder", action="store", dest="instadmgScratchFolder", default=None, type="string", metavar="FOLDER_PATH", help="Tell InstaDMG to use FOLDER_PATH as the scratch folder")
	optionsParser.add_option("", "--instadmg-output-folder", action="store", dest="instadmgOutputFolder", default=None, type="string", metavar="FOLDER_PATH", help="Tell InstaDMG to place the output image in FOLDER_PATH")
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
	
	baseCatalogFiles = []
	for thisCatalogFile in catalogFiles:
		try:
			baseCatalogFiles.append(instaUpToDate.getCatalogFullPath(thisCatalogFile))
			
		except CatalogNotFoundException:
			optionsParser.error("There does not seem to be a catalog file at: %s" % thisCatalogFile)
	
	addOnCatalogFiles = []
	if options.addOnCatalogFiles is not None:
		for thisCatalogFile in options.addOnCatalogFiles:
			try:
				addOnCatalogFiles.append(instaUpToDate.getCatalogFullPath(thisCatalogFile))
			
			except CatalogNotFoundException:
				optionsParser.error("There does not seem to be a catalog file at: %s" % thisCatalogFile)
	
	# ------- process -------
	
	thisController = instaUpToDate()
	thisController.runtimeChecks()
	
	os.chdir(absPathToInstaDMGFolder) # ToDo: remove the necessity of this
	
	for catalogFilePath in baseCatalogFiles:
		
		# setup for the run
		thisController.cleanInstaDMGFolders()
		thisController.catalogFileSettings = {}
		thisController.parsedFiles = []
		
		# parse the tree of catalog files		
		thisController.parseFile(catalogFilePath)
		
		# add any additional catalogs to this one
		for addOnCatalogFile in addOnCatalogFiles:
			thisController.parseFile(addOnCatalogFile)
		
		# create the folder strucutres needed	
		thisController.arrangeFolders()
		
		if options.processWithInstaDMG == True:
			# the run succeded, and it has been requested to run InstaDMG
			thisController.runInstaDMG(scratchFolder=options.instadmgScratchFolder, outputFolder=options.instadmgOutputFolder)
		
		
#------------------------------END MAIN------------------------------

if __name__ == "__main__":
    main()
