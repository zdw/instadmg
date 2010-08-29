#!/usr/bin/python

import os, subprocess, Foundation

from managedSubprocess import managedSubprocess
from tempFolderManager import tempFolderManager

class volumeManager(object):
	
	#---------- class properties ----------
	
	
	#-------- instance properties ---------
	
	mountedPath		= None
	
	#----------- class methods ------------
	
	@classmethod
	def detectDiskType(self, targetPath):
		'''Iterate through the subclasses of volumeManager to find the one that handles targetPath'''
		
		raise NotImplementedError()
	
	@classmethod
	def getVolumeInfo(myClass, identifier):
		'''Return the following information about the mount point, bsd name, or dev path provided: mount-path, volume-name, bsd-path, volume-format, disk-type, bsd-name, disk-bsd-name, volume-size-in-bytes, volume-uuid'''
		
		if not isinstance(identifier, str):
			raise ValueError('getVolumeInfo requires a path, bsd name, or a dev path. Got: ' + str(identifier))
		
		command = ['/usr/sbin/diskutil', 'info', '-plist', str(identifier)]
		try:
			process = managedSubprocess(command, processAsPlist=True)
		except RuntimeError, error:
			raise ValueError('The input to getVolumeInfo does not look like it was valid: ' + str(identifier) + "\nError:\n" + str(error))
		volumeProperties = process.getPlistObject()
		
		# ToDo: validate things
		
		result = {}
		
		# mount-path
		if 'MountPoint' in volumeProperties:
			result['mount-path'] = str(volumeProperties['MountPoint'])
		
		# volume-name
		if 'VolumeName' in volumeProperties:
			result['volume-name'] = str(volumeProperties['VolumeName'])
		
		# bsd-path
		result['bsd-path'] = str(volumeProperties['DeviceNode'])
		
		# bsd-name
		result['bsd-name'] = str(result['bsd-path'])[len('/dev/'):]
		
		# disk-bsd-name
		result['disk-bsd-name'] = str(volumeProperties['ParentWholeDisk'])
		
		# volume-uuid
		if 'VolumeUUID' in volumeProperties:
			result['volume-uuid'] = str(volumeProperties['VolumeUUID'])
		
		# volume-size-in-bytes
		result['volume-size-in-bytes'] = str(volumeProperties['TotalSize'])
		
		# volume-format
		if 'FilesystemUserVisibleName' in volumeProperties:
			result['volume-format'] = str(volumeProperties['FilesystemUserVisibleName'])
		
		# disk-type
		if volumeProperties['BusProtocol'] == 'Disk Image':
			result['disk-type'] = 'Disk Image'
		elif 'OpticalDeviceType' in volumeProperties:
			result['disk-type'] = 'Optical Disc'
		elif volumeProperties['BusProtocol'] in ['SATA', 'FireWire', 'USB']:
			result['disk-type'] = 'Hard Drive'
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
			if thisVolumeInfo['bsd-name'] == thisVolumeInfo['disk-bsd-name']:
				continue
			
			# exclude unmounted disks - not sure this ever happens
			if not 'mount-path' in thisVolumeInfo:
				continue
			# exclude the root mount
			elif thisVolumeInfo['mount-path'] == '/' and excludeRoot == True:
				continue
			
			possibleDisks.append(str(thisVolumeInfo['mount-path']))
		
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
		
		return (plistData["ProductUserVisibleVersion"], plistData["ProductBuildVersion"])
	
	@classmethod
	def getInstallerDiskType(mountPoint):
		'''Returns "MacOS X Client" for client versions, "MacOS X Server" for server versions, or raises a ValueError if this is not an installer disk'''
		 
		if not os.path.ismount(mountPoint):
			raise ValueError('The path "%s" is not a mount point' % mountPoint)
		
		if os.path.exists( os.path.join(mountPoint, "System/Installation/Packages/MacOSXServerInstall.mpkg") ):
			return "MacOS X Server"
		
		elif os.path.exists( os.path.join(mountPoint, "System/Installation/Packages/OSInstall.mpkg") ):
			return "MacOS X Client"
			
		raise ValueError('The volume "%s" does not look like a MacOS X installer disc.' % mountPoint)
	
	#---------- instance methods ----------
	
	def __init__(self, targetPath):
		pass
	
	def unmount(self):
		if self.mountedPath is None:
			return # ToDo: log this, maybe error out here
		
		if os.path.samefile("/", self.mountedPath):
			raise ValueError('Can not unmount the root partition, this is definatley a bug')
		
		if os.path.ismount(self.mountedPath):
			tempFolderManager.unmountVolume(self.mountedPath)
		# ToDo: otherwise check to see if it is mounted by dev entry
		
		self.mountedPath = None

class dmgManager(volumeManager):
	
	#---------- class properties ----------
	
	@classmethod
	def createNewEmptyDMG(myClass, volumeName, size, volumeFormat='', mountPoint=None):
		
		raise NotImplementedError()
		
		# validate the input
		
		if mountPoint is None:
			pass # nothing to do here
		elif mountPoint is True:
			# replace this with a temporary mount point
			mountPoint = tempFolderManager.getNewMountPoint()
		elif os.path.ismount(mountPoint) or os.path.isfile(mountPoint) or os.path.islink(mountPoint):
			# we can't use this as a mount point
			raise ValueError('createNewEmptyDMG can not put a mount point at the selected location: ' + str(mountPoint))
		elif not os.path.exists(mountPoint) and os.path.isdir(os.path.dirname(mountPoint)):
			# create the mount point and make sure we clean up after ourselves
			os.mkdir(mountPoint)
			tempFolderManager.addManagedItem(mountPoint)
		elif os.path.isdir(mountPoint):
			# only allow this if the directory is empty
			if len(os.listdir(mountPoint)) > 0:
				raise ValueError('createNewEmptyDMG can not mount something on a folder that already has contents')
		
		# ToDo: WORK HERE
			
	@classmethod
	def verifyIsDMG(myClass, identifier, checksumDMG=False):
		'''Confirm with hdiutil that the object identified is a dmg, optionally checksumming it'''
		
		if not isinstance(identifier, str):
			raise ValueError('verifyIsDMG requires a path, bsd name, or a dev path. Got: ' + str(identifier))
		
		if not checksumDMG in [True, False]:
			raise ValueError('The option checksumDMG given to verifyIsDMG must be either True or False. Got: ' + str(checksumDMG))
		
		command = ['/usr/bin/hdiutil', 'imageinfo', str(identifier)]
		try:
			process = managedSubprocess(command, processAsPlist=True)
		except RuntimeError:
			return False
		
		if checksumDMG is True:
			command = ['/usr/bin/hdiutil', 'verify', str(identifier)]
			try:
				process = managedSubprocess(command, processAsPlist=True)
			except RuntimeError:
				return False
		
		return True
	
	@classmethod
	def getVolumeInfo(myClass, identifier):
		'''Get the following information for a volume (if avalible) and return it as a hash:
			file-path, dmg-format, writeable, dmg-checksum-type, dmg-checksum-value
		Additionally, provide information from the superclass if it is mounted:
			volume-name, mount-points, bsd-label
		'''
		
		if not isinstance(identifier, str):
			raise ValueError('getVolumeInfo requires a path, bsd name, or a dev path. Got: ' + str(identifier))
		
		result = None
		# look to see if this is a mount path, bsd name, or a dev path that diskutil can work with
		try:
			result = super(self.__class__, self).getVolumeInfo(identifier)
			
			if result['disk-type'] is not 'Disk Image':
				raise ValueError("%s's getVolumeInfo method requires a disk image as the argument. Got a %s as the argument: %s" % (myClass.__name__, result['disk-type'], identifier))
			
			# if we are here, then the identifier must be the mounted path, or something in it
			identifier = result['mount-path']
			
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
		
		# file-path
		result['file-path'] = dmgProperties['Backing Store Information']['URL']
		if result['file-path'].startswith('file://localhost'):
			result['file-path'] = result['file-path'][len('file://localhost'):]
		elif result['file-path'].startswith('file://'):
			result['file-path'] = result['file-path'][len('file://'):]
		
		# dmg-format
		result['dmg-format'] = dmgProperties['Format']
		
		# writable
		if dmgProperties['Format'] in ['UDRW', 'UDSP', 'UDSB', 'RdWr']:
			result['writeable'] = True
		else:
			result['writeable'] = False
		
		# dmg-checksum-type
		if 'Checksum Type' in dmgProperties:
			result['dmg-checksum-type'] = dmgProperties['Checksum Type']
		
		# dmg-checksum-value
		if 'Checksum Value' in dmgProperties:
			result['dmg-checksum-value'] = dmgProperties['Checksum Value']
		
		return result

	
	#-------- instance properties ---------
	
	filePath		= None		# path of the source file or bundle
	
	#----------- class methods ------------
	
	#---------- instance methods ----------
	