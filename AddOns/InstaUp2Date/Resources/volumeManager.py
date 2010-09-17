#!/usr/bin/python

import os, subprocess, Foundation

import pathHelpers
import volumeTools

from managedSubprocess import managedSubprocess
from tempFolderManager import tempFolderManager

class volumeManager(object):
	
	#---------- class properties ----------
	
	volumeTypesHandled	= ['Optical Disc', 'Hard Drive']
	
	#-------- instance properties ---------
	
	diskType			= None
	
	mountPath			= None
	
	volumeName			= None
	volumeUuid			= None
	volumeFormat		= None		# eg: 'Mac OS Extended (Journaled)'
	volumeSizeInBytes	= None
	
	bsdPath				= None		# eg: /dev/disk0s2
	bsdName				= None		# eg: disk0s2
	diskBsdName			= None		# label of the physical item (parent), eg: disk0
	
	#----------- class methods ------------
	
	@classmethod
	def detectDiskType(self, targetPath):
		'''Iterate through the subclasses of volumeManager to find the one that handles targetPath'''
		
		raise NotImplementedError()
	
	@classmethod
	def getVolumeInfo(myClass, identifier):
		'''Return the following information about the mount point, bsd name, or dev path provided: mountPath, volumeName, bsdPath, volumeFormat, diskType, bsdName, diskBsdName, volumeSizeInBytes, volumeUuid'''
		
		if not hasattr(identifier, 'capitalize'):
			raise ValueError('getVolumeInfo requires a path, bsd name, or a dev path. Got: ' + str(identifier))
		
		command = ['/usr/sbin/diskutil', 'info', '-plist', str(identifier)]
		try:
			process = managedSubprocess(command, processAsPlist=True)
		except RuntimeError, error:
			raise ValueError('The input to getVolumeInfo does not look like it was valid: ' + str(identifier) + "\nError:\n" + str(error))
		volumeProperties = process.getPlistObject()
		
		# ToDo: validate things
		
		result = {}
		
		# mountPath
		if 'MountPoint' in volumeProperties:
			result['mountPath'] = str(volumeProperties['MountPoint'])
		
		# volumeName
		if 'VolumeName' in volumeProperties:
			result['volumeName'] = str(volumeProperties['VolumeName'])
		
		# bsdPath/bsdName
		if 'DeviceNode' in volumeProperties:
			if volumeProperties['DeviceNode'].startswith('/dev/'):
				result['bsdPath'] = str(volumeProperties['DeviceNode'])
				result['bsdName'] = str(result['bsdPath'])[len('/dev/'):]
			else:
				result['bsdPath'] = '/dev/' + str(volumeProperties['DeviceNode'])
				result['bsdName'] = str(volumeProperties['DeviceNode'])
		
		# diskBsdName
		result['diskBsdName'] = str(volumeProperties['ParentWholeDisk'])
		
		# volumeUuid
		if 'VolumeUUID' in volumeProperties:
			result['volumeUuid'] = str(volumeProperties['VolumeUUID'])
		
		# volumeSizeInBytes
		result['volumeSizeInBytes'] = int(volumeProperties['TotalSize'])
		
		# volumeFormat
		if 'FilesystemName' in volumeProperties:
			result['volumeFormat'] = str(volumeProperties['FilesystemName'])
		
		# diskType
		if volumeProperties['BusProtocol'] == 'Disk Image':
			result['diskType'] = 'Disk Image'
		elif 'OpticalDeviceType' in volumeProperties:
			result['diskType'] = 'Optical Disc'
		elif volumeProperties['BusProtocol'] in ['SATA', 'FireWire', 'USB']:
			result['diskType'] = 'Hard Drive'
		else:
			raise NotImplementedError('getVolumeInfo does not know how to deal with this volume:\n' + str(volumeProperties))
		
		return result
	
	@classmethod
	def getMountedVolumes(myClass, excludeRoot=True):
		
		diskutilArguments = ['/usr/sbin/diskutil', 'list', '-plist']
		diskutilProcess = managedSubprocess(diskutilArguments, processAsPlist=True)
		diskutilOutput = diskutilProcess.getPlistObject()
		
		if not "AllDisks" in diskutilOutput or not hasattr(diskutilOutput["AllDisks"], '__iter__'):
			raise RuntimeError('Error: The output from diksutil list does not look right:\n%s\n' % str(diskutilOutput))  
		
		possibleDisks = []
		
		for thisDisk in diskutilOutput["AllDisks"]:
			
			# get the mount
			thisVolumeInfo = volumeManager.getVolumeInfo(str(thisDisk))
			
			# exclude whole disks
			if thisVolumeInfo['bsdName'] == thisVolumeInfo['diskBsdName']:
				continue
			
			# exclude unmounted disks
			if not 'mountPath' in thisVolumeInfo or thisVolumeInfo['mountPath'] in [None, '']:
				continue
			# exclude the root mount if it is not requested
			elif thisVolumeInfo['mountPath'] == '/' and excludeRoot == True:
				continue
			
			possibleDisks.append(str(thisVolumeInfo['mountPath']))
		
		return possibleDisks
	
	@classmethod
	def getMacOSVersionAndBuildOfVolume(myClass, mountPoint):
		if not os.path.ismount(mountPoint):
			raise ValueError('The path "%s" is not a mount point' % mountPoint)
		
		if not os.path.isfile(os.path.join(mountPoint, "System/Library/CoreServices/SystemVersion.plist")):
			raise ValueError('The item given does not seem to be a MacOS X volume: ' + mountPoint)
		
		plistNSData = Foundation.NSData.dataWithContentsOfFile_(os.path.join(mountPoint, "System/Library/CoreServices/SystemVersion.plist"))
		plistData, format, error = Foundation.NSPropertyListSerialization.propertyListFromData_mutabilityOption_format_errorDescription_(plistNSData, Foundation.NSPropertyListMutableContainersAndLeaves, None, None)
		if error:
			raise RuntimeError('Unable to get ther version of MacOS on volume: "%s". Error was: %s' % (mountPoint, str(error)))
		
		if not ("ProductBuildVersion" in plistData and "ProductUserVisibleVersion" in plistData):
			raise RuntimeError(' Unable to get the version, build, or type of MacOS on volume:' + mountPoint)
		
		return (str(plistData["ProductUserVisibleVersion"]), str(plistData["ProductBuildVersion"]))
	
	@classmethod
	def getInstallerDiskType(myClass, mountPoint):
		'''Returns "MacOS X Client" for client versions, "MacOS X Server" for server versions, or raises a ValueError if this is not an installer disk'''
		 
		if not os.path.ismount(mountPoint):
			raise ValueError('The path "%s" is not a mount point' % mountPoint)
		
		if os.path.exists( os.path.join(mountPoint, "System/Installation/Packages/MacOSXServerInstall.mpkg") ):
			return "MacOS X Server"
		
		elif os.path.exists( os.path.join(mountPoint, "System/Installation/Packages/OSInstall.mpkg") ):
			return "MacOS X Client"
			
		raise ValueError('The volume "%s" does not look like a MacOS X installer disc.' % mountPoint)
	
	@classmethod
	def unmountVolume(self, mountPath):
		if mountPath is None:
			return # ToDo: log this, maybe error out here
		
		if os.path.samefile("/", mountPath):
			raise ValueError('Can not unmount the root partition, this is definatley a bug')
		
		if os.path.ismount(mountPath):
			volumeTools.unmountVolume(mountPath)
		# ToDo: otherwise check to see if it is mounted by dev entry
	
	#---------- instance methods ----------
	
	def __init__(self, identifier):
		
		if not hasattr(identifier, 'capitalize'):
			raise ValueError('%s requires a path, bsd name, or a dev path. Got: %s' % (self.__class__.__name__, str(identifier)))
		
		volumeInfo = None
		try:
			volumeInfo = self.getVolumeInfo(identifier)
		except ValueError, error:
			raise ValueError('%s requires a valid path, bsd name, or a dev path. Got: %s' % (self.__class__.__name__, str(identifier)))
		
		# confirm that this is a cd/dvd or a hard drive
		if volumeInfo['diskType'] not in self.volumeTypesHandled:
			raise ValueError('%s only handles the following types of disc: %s, this item (%s) was a %s and should have been handled by differnt subclass' % (self.__class__.__name__, str(self.volumeTypesHandled), str(identifier), volumeInfo['diskType']))
		
		# copy the values over into the item
		for thisAttribute in volumeInfo.keys():
			if not hasattr(self, thisAttribute):
				raise NotImplementedError('%s does not yet have a "%s" property which getVolumeInfo records' % (self.__class__.__name__, thisAttribute))
			setattr(self, thisAttribute, volumeInfo[thisAttribute])
	
	def isMounted(self):
		
		if self.mountPath is not None and os.path.ismount(self.mountPath):
			return self.mountPath
		
		# ToDo: check with diskutil/hdiutil to see if it is actually mounted
		
		return None
	
	def unmount(self):
		if self.mountPath is None:
			return # ToDo: log this, maybe error out here
		
		self.unmountVolume(self.mountPath)
		self.mountPath = None

class dmgManager(volumeManager):
	
	#---------- class properties ----------
	
	volumeTypesHandled	= ['Disk Image']
	
	#-------- instance properties ---------
	
	filePath			= None		# path of the source file or bundle
	
	dmgFomat			= None		# eg: UDRW
	writeable			= None
	
	dmgChecksumType		= None
	dmgChecksumValue	= None
	
	#----------- class methods ------------
	
#	@classmethod
#	def createNewEmptyDMG(myClass, volumeName, size, volumeFormat='', mountPoint=None):
#		
#		raise NotImplementedError()
#		
#		# validate the input
#		
#		if mountPoint is None:
#			pass # nothing to do here
#		elif mountPoint is True:
#			# replace this with a temporary mount point
#			mountPoint = tempFolderManager.getNewMountPoint()
#		elif os.path.ismount(mountPoint) or os.path.isfile(mountPoint) or os.path.islink(mountPoint):
#			# we can't use this as a mount point
#			raise ValueError('createNewEmptyDMG can not put a mount point at the selected location: ' + str(mountPoint))
#		elif not os.path.exists(mountPoint) and os.path.isdir(os.path.dirname(mountPoint)):
#			# create the mount point and make sure we clean up after ourselves
#			os.mkdir(mountPoint)
#			tempFolderManager.addManagedItem(mountPoint)
#		elif os.path.isdir(mountPoint):
#			# only allow this if the directory is empty
#			if len(os.listdir(mountPoint)) > 0:
#				raise ValueError('createNewEmptyDMG can not mount something on a folder that already has contents')
#		
#		# ToDo: WORK HERE
			
	@classmethod
	def verifyIsDMG(myClass, identifier, checksumDMG=False):
		'''Confirm with hdiutil that the object identified is a dmg, optionally checksumming it'''
		
		if not hasattr(identifier, 'capitalize'):
			raise ValueError('verifyIsDMG requires a path, bsd name, or a dev path. Got: ' + str(identifier))
		
		if not checksumDMG in [True, False]:
			raise ValueError('The option checksumDMG given to verifyIsDMG must be either True or False. Got: ' + str(checksumDMG))
		
		command = ['/usr/bin/hdiutil', 'imageinfo', str(identifier)]
		try:
			process = managedSubprocess(command)
		except RuntimeError:
			return False
		
		if checksumDMG is True:
			command = ['/usr/bin/hdiutil', 'verify', str(identifier)]
			try:
				process = managedSubprocess(command)
			except RuntimeError:
				return False
		
		return True
	
	@classmethod
	def getVolumeInfo(myClass, identifier):
		'''Get the following information for a volume (if avalible) and return it as a hash:
			filePath, dmgFormat, writeable, dmg-checksum-type, dmg-checksum-value
		Additionally, provide information from the superclass if it is mounted:
			volumeName, mount-points, bsd-label
		'''
		
		if not hasattr(identifier, 'capitalize'):
			raise ValueError('getVolumeInfo requires a path, bsd name, or a dev path. Got: ' + str(identifier))
		
		result = None
		# look to see if this is a mount path, bsd name, or a dev path that diskutil can work with
		try:
			result = super(self.__class__, self).getVolumeInfo(identifier)
			
			if result['diskType'] is not 'Disk Image':
				raise ValueError("%s's getVolumeInfo method requires a disk image as the argument. Got a %s as the argument: %s" % (myClass.__name__, result['diskType'], identifier))
			
			# if we are here, then the identifier must be the mounted path, or something in it
			identifier = result['mountPath']
			
		except ValueError:
			# this might be a pointer to the dmg file 
			result = {}
		
		# try for information on this as a dmg
		command = ['/usr/bin/hdiutil', 'imageinfo', '-plist', str(identifier)]
		try:
			process = managedSubprocess(command, processAsPlist=True)
		except RuntimeError:
			raise ValueError('The item given does not seem to be a DMG: ' + str(identifier))
		dmgProperties = process.getPlistObject()
		
		# filePath
		result['filePath'] = dmgProperties['Backing Store Information']['URL']
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
	
#	@classmethod
#	def getMountedDMGFiles(myClass):
#		
#		hdiutilArguments = ['/usr/bin/hdiutil', 'list', '-plist']
#		hdiutilProcess = managedSubprocess(diskutilArguments, processAsPlist=True)
#		hdiutilOutput = diskutilProcess.getPlistObject()
#		
#		mountedFiles = []
#		
#		if 'images' in hdiutilOutput:
#			for thisDMG in hdiutilOutput['images']:
#				mountedFiles.append(str(thisDMG['image-path']))
#		
#		return mountedFiles
	
	@classmethod
	def getDMGMountPoints(myClass, dmgFilePath):
		
		if not os.path.exists(dmgFilePath):
			raise ValueError('getDMGMountPoint called with a dmgFilePath that does not exist: ' + dmgFilePath)
		
		hdiutilArguments = ['/usr/bin/hdiutil', 'info', '-plist']
		hdiutilProcess = managedSubprocess(hdiutilArguments, processAsPlist=True)
		hdiutilOutput = hdiutilProcess.getPlistObject()
		
		if 'images' in hdiutilOutput:
			for thisDMG in hdiutilOutput['images']:
				if os.path.samefile(thisDMG['image-path'], dmgFilePath):
					mountPoints = []
					
					for thisEntry in thisDMG['system-entities']:
						if 'mount-point' in thisEntry:
							mountPoints.append(str(thisEntry['mount-point']))
					
					if len(mountPoints) > 0:
						return mountPoints
					
					break
		
		return None
	
	@classmethod
	def mountImage(myClass, dmgFile, mountPoint=None, mountInFolder=None, mountReadWrite=None, shadowFile=None, paranoidMode=False):
		'''Mount an image'''
		
		# -- validate input
		
		# dmgFile
		if dmgFile is None or not os.path.exists(dmgFile) or os.path.ismount(dmgFile):
			raise ValueError('mountImage requires dmgFile be a path to a file, got: ' + dmgFile)
		dmgFile = pathHelpers.normalizePath(dmgFile, followSymlink=True)
		
		# mountPoint/mountInFolder
		if mountPoint is not None and mountInFolder is not None:
			raise ValueError('mountImage can only be called with mountPoint or mountInFolder, not both')
		
		elif mountPoint is not None and os.path.ismount(mountPoint):
			raise ValueError('mountImage called with a mountPoint that is already a mount point: ' + mountPoint)
		
		elif mountPoint is not None and os.path.isdir(mountPoint):
			if len(os.listdir(mountPoint)) != 0:
				raise ValueError('mountImage called with a mountPoint that already has contents: %s (%s)' % (mountPoint, str(os.listdir(mountPoint))))
		
		elif mountPoint is not None and os.path.exists(mountPoint):
			raise ValueError('mountImage called with a mountPoint that already exists and is not a folder: ' + mountPoint)
		
		elif mountPoint is not None:
			tempFolderManager.add
		
		elif mountInFolder is not None and not os.path.isdir(mountInFolder):
			raise ValueError('mountImage called with a mountInFolder path that is not a folder: ' + mountInFolder)
		
		elif mountInFolder is not None:
			mountPoint = tempFolderManager.getNewMountPoint()
		
		else:
			# create a default mount point
			mountPoint = tempFolderManager.getNewMountPoint()
		mountPoint = pathHelpers.normalizePath(mountPoint, followSymlink=True)
		
		# mountReadWrite
		if mountReadWrite not in [None, True, False]:
			raise ValueError('The only valid options for mountReadWrite are True or False')
		
		# shadowFile
		if shadowFile is True:
			# generate a temporary one
			shadowFile = tempFolderManager.getNewTempFile(suffix='.shadow')
			
		elif shadowFile is not None:
			shadowFile = pathHelpers.normalizePath(shadowFile, followSymlink=True)
			
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
		
		# paranoidMode
		if paranoidMode not in [True, False]:
			raise ValueError('checksumImage must be either True, or False. Got: ' + str(paranoidMode))		
		
		# -- check to see if it is already mounted
		
		existingMountPoints = myClass.getDMGMountPoints(dmgFile)
		if existingMountPoints is not None:
			raise RuntimeError('The image (%s) was already mounted: %s' % (dmgFile, ", ".join(existingMountPoints)))
		
		# -- construct the command
		
		command = ['/usr/bin/hdiutil', 'attach', dmgFile, '-plist', '-mountpoint', mountPoint, '-nobrowse', '-owners', 'on']
		
		if mountReadWrite is True and shadowFile is None and self.writeable is False:
			shadowFile = tempFolderManager.getNewTempFile(suffix='.shadow')
		elif mountReadWrite is False and shadowFile is None:
			command += ['-readonly']
		
		if paranoidMode is False:
			command += ['-noverify', '-noautofsck']
		else:
			command += ['-verify', '-autofsck']
		
		if shadowFile is not None:
			command += ['-shadow', shadowFile]
		
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
	
	#---------- instance methods ----------
	
	def isMounted(self):
		'''Return True if hdiutil says this is mounted, False otherwise'''
		
		if self.filePath is None:
			raise RuntimeError('isMounted called on an dmg that does not have a filePath setup, this should not happen')
		
		if self.getDMGMountPoints(self.filePath) is None:
			return False
		
		return True
	
	def getMountPoint(self, returnAllMounts=False):
		'''Return the first mount point, as diutil sees it, or all of them if asked. If it is not mounted return None'''
		
		if self.filePath is None:
			raise RuntimeError('getMountPoint called on an dmg that does not have a filePath setup, this should not happen')
		
		mountPoints = self.getDMGMountPoints(self.filePath)
		
		if mountPoints is None or len(mountPoints) == 0:
			return None
		elif returnAllMounts is False:
			return mountPoints[0]
		else:
			return mountPoints
	
	def mount(self, mountPoint=None, mountInFolder=None, mountReadWrite=None, shadowFile=None, paranoidMode=False):
		'''Mount this image'''
		
		# -- sanity check
		
		if self.filePath is None:
			raise RuntimeError('mount called on an dmg that does not have a filePath setup, this should not happen')
		
		# -- run command
		
		self.mountPath = self.mountImage(self.filePath, mountPoint, mountInFolder, mountReadWrite, shadowFile, paranoidMode)
		

		
		
		
		
		
		
		

		
		
			
			
		
		
		
	