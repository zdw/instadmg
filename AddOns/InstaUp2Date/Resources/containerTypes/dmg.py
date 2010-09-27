#!/usr/bin/python

import os, re, time, urllib

from volume		import volume

try:
	from .managedSubprocess					import managedSubprocess
	from .tempFolderManager					import tempFolderManager
	from .pathHelpers						import normalizePath, pathInsideFolder
	
except ImportError:
	from .Resources.managedSubprocess		import managedSubprocess
	from .Resources.tempFolderManager		import tempFolderManager
	from .Resources.pathHelpers				import normalizePath, pathInsideFolder


class dmg(volume):
	
	# ------ instance properties
	
	shadowFilePath			= None
	
	dmgFormat				= None
	writeable				= None
	
	dmgChecksumType			= None
	dmgChecksumValue		= None
	
	
	# ------ class properties
	
	wholeDiskRegEx			= re.compile('^(?P<bsdPath>/dev/(?P<bsdName>disk\d+))$')
	volumeSliceRegEx		= re.compile('^(?P<bsdPath>/dev/(?P<bsdName>disk\d+s\d+))$')
	
	# ------ instance methods
	def classInit(self, itemPath, processInformation, shadowFile=None):
		
		# -- validate and store input
		
		# get the information from diskutil via the volume class
		super(self.__class__, self).classInit(itemPath, processInformation)
		
		# reset key diffferences from the superclass
		
		if 'dmgFilePath' in processInformation:
			self.filePath = normalizePath(processInformation['dmgFilePath'], followSymlink=True)
		else:
			self.filePath = normalizePath(itemPath, followSymlink=True)
		
		if 'shadowFilePath' in processInformation:
			self.shadowFilePath = processInformation['shadowFilePath']
		else:
			self.shadowFilePath = self.validateShadowfile(shadowFile)
		
		# get and store the information from hdiutil
		
		hdiutilInfo = None
		if 'hdiutilInfo' in processInformation:
			hdiutilInfo = processInformation['hdiutilInfo']
		else:
			hdiutilInfo = self.hdiutilInfo(self.filePath)
		
		# dmgFormat
		if 'dmgFormat' in hdiutilInfo:
			self.dmgFormat = hdiutilInfo['dmgFormat']
		
		# writable
		if 'writable' in hdiutilInfo:
			self.writable = hdiutilInfo['writable']
		
		# dmgChecksumType
		if 'dmgChecksumType' in hdiutilInfo:
			self.dmgChecksumType = hdiutilInfo['dmgChecksumType']
		
		# dmgChecksumValue
		if 'dmgChecksumValue' in hdiutilInfo:
			self.dmgChecksumValue = hdiutilInfo['dmgChecksumValue']
	
	def getShadowFile(self):
		'''Return the path of the shadow file this is mounted with, or none if it has none'''
		
		return self.shadowFilePath
	
	def getMountPoint(self):
		'''Get the mount point with the current shadow file settings'''
		
		for thisMount in self.getMountedImages():
			if os.path.samefile(self.getStoragePath(), thisMount['filePath']):
				
				# make sure the shadowPath settings match
				if (self.shadowFilePath is None and 'shadowFilePath' in thisMount) or (self.shadowFilePath is not None and 'shadowFilePath' not in thisMount):
					continue
				if self.shadowFilePath is not None and not normalizePath(self.shadowFilePath, followSymlink=True) == normalizePath(thisMount['shadowFilePath'], followSymlink=True):
					continue
				
				return thisMount['mountPoint']
		
		return None
		
	def mount(self, mountPoint=None, mountInFolder=None, mountReadWrite=False, paranoidMode=False):
		'''Mount the image'''
		
		# -- validate input
		
		currentMountPoint = self.getMountPoint()
		if currentMountPoint is not None:
			return currentMountPoint
		
		# mountPoint/mountInFolder
		if mountPoint is not None and mountInFolder is not None:
			raise ValueError('mount() can only be called with mountPoint or mountInFolder, not both')
		
		if mountPoint is not None and currentMountPoint is not None:
			if os.path.samefile(mountPoint, currentMountPoint):
				return # nothing to do here
			else:
				raise ValueError('This image (%s) was already mounted with the same settings (shadowFile = %s)' % (self.getStoragePath(), self.shadowFilePath))
		
		elif mountPoint is not None and os.path.ismount(mountPoint):
			raise ValueError('mount() called with a mountPoint that is already a mount point: ' + mountPoint)
		
		elif mountPoint is not None and os.path.isdir(mountPoint):
			if len(os.listdir(mountPoint)) != 0:
				raise ValueError('mount() called with a mountPoint that already has contents: %s (%s)' % (mountPoint, str(os.listdir(mountPoint))))
		
		elif mountPoint is not None and os.path.exists(mountPoint):
			raise ValueError('mount() called with a mountPoint that already exists and is not a folder: ' + mountPoint)
		
		elif mountPoint is not None: # it has to be a suitable directory at this point
			mountPoint = normalizePath(mountPoint, followSymlink=True)
			tempFolderManager.addManagedMount(mountPoint)
		
		elif mountInFolder is not None and not os.path.isdir(mountInFolder):
			raise ValueError('mount() called with a mountInFolder path that is not a folder: ' + mountInFolder)
		
		elif mountPoint is None and mountInFolder is not None:
			mountPoint = tempFolderManager.getNewMountPoint(parentFolder=mountInFolder)
		
		else:
			mountPoint = tempFolderManager.getNewMountPoint()
		
		# mountReadWrite
		if mountReadWrite not in [None, True, False]:
			raise ValueError('The only valid options for mountReadWrite are True, False, or None')

		# paranoidMode
		if paranoidMode not in [True, False]:
			raise ValueError('checksumImage must be either True, or False. Got: ' + str(paranoidMode))		
		
		# -- construct the command
		
		command = ['/usr/bin/hdiutil', 'attach', self.getStoragePath(), '-plist', '-mountpoint', mountPoint, '-nobrowse', '-owners', 'on']
		
		if mountReadWrite is True and self.shadowFilePath is None and self.writeable is False:
			shadowFile = tempFolderManager.getNewTempFile(suffix='.shadow')
		elif mountReadWrite is False and self.shadowFilePath is None:
			command += ['-readonly']
		
		if paranoidMode is False:
			command += ['-noverify', '-noautofsck']
		else:
			command += ['-verify', '-autofsck']
		
		if self.shadowFilePath is not None:
			command += ['-shadow', self.shadowFilePath]
		
		# -- run the command
		
		process = managedSubprocess(command, processAsPlist=True)
		mountInfo = process.getPlistObject()
		
		actualMountedPath = None
		
		for thisEntry in mountInfo['system-entities']:
			if 'mount-point' in thisEntry:
				if actualMountedPath != None and os.path.ismount(actualMountedPath):
					# ToDo: think all of this through, prefereabley before it is needed
					raise Exception('This item (%s) seems to be mounted at two places , this is possible, but now that it is happening larkost needs to work on this' % self.filePath)
				
				actualMountedPath = thisEntry['mount-point'] # ToDo: make sure that this is the mount point we requested
				break # assume that there is only one mountable item... otherwise we are hosed already
		
		if actualMountedPath is None:
			raise RuntimeError('Error: image could not be mounted')
		
		return actualMountedPath
	
	def getWorkingPath(self, withinFolder=None):
		'''Return the mounted path, mounting or re-mounting if necessary'''
		
		if withinFolder is not None and not os.path.isdir(withinFolder):
			raise ValueError('When using the withinFolder option the item must be a folder')
		
		currentMountPoint = self.getMountPoint()
		
		if currentMountPoint is None:
			return self.mount(mountInFolder=withinFolder)
		
		elif withinFolder is not None and not pathInsideFolder(currentMountPoint, withinFolder):
			# re-mount inside the path
			self.unmount()
			return self.mount(mountInFolder=withinFolder)
		
		return str(currentMountPoint)
	
	# ------ class methods
	
	@classmethod
	def validateShadowfile(self, shadowFile):
		
		# shadowFile
		if shadowFile is True:
			# generate a temporary one
			shadowFile = tempFolderManager.getNewTempFile(suffix='.shadow')
			
		elif shadowFile is not None:
			shadowFile = normalizePath(shadowFile, followSymlink=True)
			
			if os.path.isfile(shadowFile): # work here
				pass # just use the file
			
			elif os.path.isdir(shadowFile):
				# a directory to put the shadow file in
				shadowFile = tempFolderManager.getNewTempFile(parentFolder=shadowFile, suffix='.shadow')
			
			elif os.path.isdir(os.path.dirname(shadowFile)):
				# the path does not exist, but the directory it is in looks good
				pass
			
			else:
				# not valid
				raise ValueError('The path given for the shadow file does not look valid: ' + str(shadowFile))
		
		return shadowFile
	
	@classmethod
	def getVersionWithShadowFile(myClass, imageFile, shadowFile=None):
		'''Mount an image, possibly with a shadow file, and return the appropriate item'''
		
		return myClass(imageFile, {}, shadowFile=shadowFile)
		
	@classmethod
	def getMountedImages(myClass):
		'''Get a list of mounted images'''
		
		command = ['/usr/bin/hdiutil', 'info', '-plist']
		process = managedSubprocess(command, processAsPlist=True)
		# note: if there was an error it will already send up a RuntimeError
		hdiutilOutput = process.getPlistObject()
		
		imageList = []
		if 'images' in hdiutilOutput:
			for thisImage in hdiutilOutput['images']:
				imageInfo = { 'filePath':thisImage['image-path'] }
				
				if thisImage['writeable'] is True:
					imageInfo['readWrite'] = True
				else:
					imageInfo['readWrite'] = False
				
				if 'shadow-path' in thisImage:
					imageInfo['shadowFilePath'] = thisImage['shadow-path']
				
				for thisSystemEntity in thisImage['system-entities']:
					wholeDiskResult = myClass.wholeDiskRegEx.match(thisSystemEntity['dev-entry'])
					volumeSliceResult = myClass.volumeSliceRegEx.match(thisSystemEntity['dev-entry'])
					
					if wholeDiskResult is not None:
						imageInfo.update({ 'diskBsdName':wholeDiskResult.group('bsdName'), 'diskBsdPath':wholeDiskResult.group('bsdPath') })
					
					elif myClass.volumeSliceRegEx is not None and 'mount-point' in thisSystemEntity:
						imageInfo.update({ 'bsdName':volumeSliceResult.group('bsdName'), 'bsdPath':volumeSliceResult.group('bsdPath'), 'mountPoint':thisSystemEntity['mount-point'] })
					
					if 'mount-point' in thisSystemEntity:
						imageInfo['mountPoint'] = thisSystemEntity['mount-point']
				
				imageList.append(imageInfo)
		
		return imageList
	
	@classmethod
	def hdiutilInfo(myClass, identifier):
		
		if not hasattr(identifier, 'capitalize'):
			raise ValueError('getVolumeInfo requires a path, bsd name, or a dev path. Got: ' + str(identifier))
		
		normalizedIdentifier = normalizePath(identifier, followSymlink=True)
		if os.path.exists(normalizedIdentifier):
			identifier = normalizedIdentifier
		
		command = ['/usr/bin/hdiutil', 'imageinfo', '-plist', str(identifier)]
		try:
			process = managedSubprocess(command, processAsPlist=True)
		except RuntimeError, error:
			raise ValueError('The item given does not seem to be a DMG: ' + str(identifier) + "\n" + str(error))
		dmgProperties = process.getPlistObject()
		
		result = {}
		
		# volumeName
		result['volumeName'] = dmgProperties['Backing Store Information']['Name']
		
		# filePath
		result['filePath'] = urllib.unquote(dmgProperties['Backing Store Information']['URL'])
		if result['filePath'].startswith('file://localhost'):
			result['filePath'] = result['filePath'][len('file://localhost'):]
		elif result['filePath'].startswith('file://'):
			result['filePath'] = result['filePath'][len('file://'):]
		
		# dmgFormat
		result['dmgFormat'] = dmgProperties['Format']
		
		# writable
		if dmgProperties['Format'] in ['UDRW', 'UDSP', 'UDSB', 'RdWr']:
			result['writeable'] = True
		else:
			result['writeable'] = False
		
		# dmg-checksum-type
		if 'Checksum Type' in dmgProperties:
			result['dmgChecksumType'] = dmgProperties['Checksum Type']
		else:
			result['dmgChecksumType'] = None # just in case we ever re-do this
		
		# dmg-checksum-value
		if 'Checksum Value' in dmgProperties:
			result['dmgChecksumValue'] = dmgProperties['Checksum Value']
		else:
			result['dmgChecksumValue'] = None # just in case we ever re-do this
		
		return result
	
	@classmethod
	def scoreItemMatch(myClass, itemPath, processInformation, **kwargs):
		
		# -- validate input
		
		if not hasattr(itemPath, 'capitalize'):
			raise ValueError('scoreItemMatch requires a string, got: %s (%s)' % (str(itemPath), type(itemPath)))
		
		# -- validate input
		
		matchScore = 0
		
		shadowFilePath = None
		if 'shadowFile' in kwargs and kwargs['shadowFile'] is not False:
			shadowFilePath = myClass.validateShadowfile(kwargs['shadowFile'])
		
		# -- see if itemPath matches a mounted image
		
		if 'mountedImages' not in processInformation:
			processInformation['mountedImages'] = myClass.getMountedImages()
		
		for thisMountedImage in processInformation['mountedImages']:
			
			# mountPoint
			if (
				# mountPoint
				os.path.samefile(itemPath, thisMountedImage['mountPoint']) or
				
				# shadow file
				('shadowFilePath' in thisMountedImage and os.path.samefile(itemPath, thisMountedImage['shadowFilePath'])) or
				
				# file path to dmg
				os.path.samefile(itemPath, thisMountedImage['filePath']) or
				
				# bsdName/bsdPath
				itemPath in [thisMountedImage['bsdName'], thisMountedImage['bsdPath']]
				
				# ToDo: think through also including the diskBsdName/diskBsdPath
			):
				processInformation['dmgFilePath'] = normalizePath(thisMountedImage['filePath'], followSymlink=True)
				if 'shadowFilePath' in thisMountedImage:
					shadowFilePath = thisMountedImage['shadowFilePath']
				break
		
		# -- check with diskutil to see if we can resolve this
		
		if 'diskutilInfo' not in processInformation:
			try:
				canidateDiskutilInfo = myClass.diskutilInfo(itemPath)
				
				mountPoint = None
				if 'mountPath' in canidateDiskutilInfo:
					mountPoint = canidateDiskutilInfo['mountPath']
				
				if itemPath in [mountPoint, canidateDiskutilInfo['bsdPath'], canidateDiskutilInfo['bsdName']]:
					processInformation['diskutilInfo'] = canidateDiskutilInfo
			except:
				pass # if could be the path to a closed image
		
		if 'diskutilInfo' in processInformation:
			if processInformation['diskutilInfo']['diskType'] != 'Disk Image':
				return (0, processInformation)
			
			# make sure we have the path to the mount point
			itemPath = processInformation['diskutilInfo']['mountPath']
		
		# -- use 'hdiutil imageinfo' to see if it is an image
		
		if not 'dmgFilePath' in processInformation:
			if 'hdiutilInfo' not in processInformation:
				try:
					processInformation['hdiutilInfo'] = myClass.hdiutilInfo(itemPath)
					
					# if we did not error out, it is a dmg
					
					processInformation['dmgFilePath'] = normalizePath(processInformation['hdiutilInfo']['filePath'], followSymlink=True)
					
					if 'shadowFilePath' in processInformation:
						shadowFilePath = processInformation['shadowFilePath']
				
				except ValueError:
					pass
		
		# -- make the score decision
		
		if 'dmgFilePath' in processInformation:
			
			if shadowFilePath is None:
				processInformation['instanceKeys'][myClass.__name__] = processInformation['dmgFilePath']
			else:
				processInformation['dmgShadowFilePath'] = myClass.validateShadowfile(shadowFilePath)
				processInformation['instanceKeys'][myClass.__name__] = processInformation['dmgFilePath'] + '&' + processInformation['dmgShadowFilePath']
			
			return myClass.getMatchScore(), processInformation
		
		return 0, processInformation
	