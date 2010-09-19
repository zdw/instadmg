#!/usr/bin/python

import os, Foundation

from folder					import folder

try:
	from .Resources.volumeTools				import getDiskutilInfo
	from .Resources.managedSubprocess		import managedSubprocess
except ImportError:
	from .volumeTools						import getDiskutilInfo
	from .managedSubprocess					import managedSubprocess


class volume(folder):
	
	# ------ instance properties
	
	volumeName				= None	# possibly seperate from the display name
	volumeType				= None
	
	bsdName					= None
	bsdPath					= None
	
	deviceBSDName			= None
	deviceBSDPath			= None
	
	mountedReadWrite		= None
	
	testedForMacOS			= False
	macOSType				= None
	macOSVersion			= None
	macOSBuild				= None
	macOSInstallerDisc		= None
		
	# ------ class properties
	
	volumeTypesHandled		= []
	
	# ------ instance methods
	
	def classInit(self, itemPath, processInformation):
		
		# -- get and populate the information from diskutil about this item
		
		diskutilInfo = None
		if 'diskutilInfo' in processInformation:
			diskutilInfo = processInformation['diskutilInfo']
		else:
			diskutilInfo = self.diskutilInfo(self.getStoragePath())
		
		# volumeName
		if 'volumeName' in diskutilInfo:
			self.volumeName = diskutilInfo['volumeName']
			self.displayName = diskutilInfo['volumeName']
		
		# bsdName/bsdPath
		if 'bsdName' in diskutilInfo:
			self.bsdName = diskutilInfo['bsdName']
		if 'bsdPath' in diskutilInfo:
			self.bsdPath = diskutilInfo['bsdPath']
		
		# diskBsdName/diskBsdPath
		if 'diskBsdName' in diskutilInfo:
			self.diskBsdName = diskutilInfo['diskBsdName']
		if 'diskBsdPath' in diskutilInfo:
			self.diskBsdPath = diskutilInfo['diskBsdPath']
		
		# volumeUuid
		if 'volumeUuid' in diskutilInfo:
			self.volumeUuid = diskutilInfo['volumeUuid']
		
		# volumeSizeInBytes
		if 'volumeSizeInBytes' in diskutilInfo:
			self.volumeSizeInBytes = diskutilInfo['volumeSizeInBytes']
		
		# volumeFormat
		if 'volumeFormat' in diskutilInfo:
			self.volumeFormat = diskutilInfo['volumeFormat']
		
		# diskType
		if 'diskType' in diskutilInfo:
			self.volumeType = diskutilInfo['diskType']
		
		self.getMacOSInformation()
	
	def isMounted(self):
		
		mountPoint = self.getMountPoint()
		
		if mountPoint is not None:
			return True
		
		return False
	
	def getMountPoint(self):
		
		if self.bsdPath is None:
			raise Exception('There was no bsdPath for this item, something is not right')
		
		currentInfo = getDiskutilInfo(self.bsdPath)
		
		if 'mountPath' in currentInfo:
			return currentInfo['mountPath']
		
		return None
	
	def getMacOSInformation(self):
		
		# -- see if we already have this information
		
		if self.testedForMacOS is True:
			# we already have the information
			return {
				'macOSType':self.macOSType,
				'macOSVersion':self.macOSVersion,
				'macOSBuild':self.macOSBuild,
				'macOSInstallerDisc':self.macOSInstallerDisc
			}
		
		# -- get the information from the disc
		
		wasAlreadyMounted = False
		if self.isMounted():
			wasAlreadyMounted = True
		
		currentMountPoint = self.getWorkingPath()
		
		systemVersionFile = os.path.join(currentMountPoint, "System/Library/CoreServices/SystemVersion.plist")
		
		if not os.path.isfile(systemVersionFile):
			# this is not a MacOS X disc
			self.testedForMacOS = True
			return None
		
		plistNSData = Foundation.NSData.dataWithContentsOfFile_(systemVersionFile)
		plistData, format, error = Foundation.NSPropertyListSerialization.propertyListFromData_mutabilityOption_format_errorDescription_(plistNSData, Foundation.NSPropertyListMutableContainersAndLeaves, None, None)
		if error:
			raise RuntimeError('Unable to get ther version of MacOS on: "%s". Error was: %s' % (self.getStoragePath(), str(error)))
		
		if not ("ProductBuildVersion" in plistData and "ProductUserVisibleVersion" in plistData):
			raise RuntimeError(' Unable to get the version, build, or type of MacOS on volume:' + self.getStoragePath())
		
		result = {
			'macOSVersion':str(plistData["ProductUserVisibleVersion"]),
			'macOSBuild':str(plistData["ProductBuildVersion"])
		}
		self.macOSVersion	= str(plistData["ProductUserVisibleVersion"])
		self.macOSBuild		= str(plistData["ProductBuildVersion"])
		
		# check if this is client or server
		
		if os.path.exists(os.path.join(currentMountPoint, "System/Library/CoreServices/ServerVersion.plist")):
			result['macOSType']	= 'MacOS X Server'
			self.macOSType		= 'MacOS X Server'
		else:
			result['macOSType']	= 'MacOS X Client'
			self.macOSType		= 'MacOS X Client'
		
		# check if this is an installer disc
		
		if os.path.exists(os.path.join(currentMountPoint, "System/Installation/Packages/OSInstall.mpkg")):
			result['macOSInstallerDisc']	= True
			self.macOSInstallerDisc			= True
		else:
			result['macOSInstallerDisc']	= False
			self.macOSInstallerDisc			= False
		
		if wasAlreadyMounted is False:
			self.unmount()
		
		# return the result
		self.testedForMacOS = True
		return result
	
	# ------ class methods
	
	@classmethod
	def getMountedVolumes(myClass, excludeRoot=True):
		
		diskutilArguments = ['/usr/sbin/diskutil', 'list', '-plist']
		diskutilProcess = managedSubprocess(diskutilArguments, processAsPlist=True)
		diskutilOutput = diskutilProcess.getPlistObject()
		
		if not "AllDisks" in diskutilOutput or not hasattr(diskutilOutput["AllDisks"], '__iter__'):
			raise RuntimeError('Error: The output from diksutil list does not look right:\n%s\n' % str(diskutilOutput))  
		
		mountedVolumes = []
		
		for thisVolume in diskutilOutput["AllDisks"]:
			
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
	def diskutilInfo(myclass, identifier):
		'''Return processed information from hdiutil about this path'''
		
		if not hasattr(identifier, 'capitalize'):
			raise ValueError('getVolumeInfo requires a path, bsd name, or a dev path. Got: ' + str(identifier))
		
		command = ['/usr/sbin/diskutil', 'info', '-plist', str(identifier)]
		try:
			process = managedSubprocess(command, processAsPlist=True)
		except RuntimeError, error:
			raise ValueError('The input to getVolumeInfo does not look like it was valid: ' + str(identifier) + "\nError:\n" + str(error))
		diskutilInfo = process.getPlistObject()
		
		result = {}
		
		# mountPath
		if 'MountPoint' in diskutilInfo:
			result['mountPath'] = str(diskutilInfo['MountPoint'])
		
		# volumeName
		if 'VolumeName' in diskutilInfo:
			result['volumeName'] = str(diskutilInfo['VolumeName'])
		
		# bsdPath/bsdName
		if 'DeviceNode' in diskutilInfo:
			if diskutilInfo['DeviceNode'].startswith('/dev/'):
				result['bsdPath'] = str(diskutilInfo['DeviceNode'])
				result['bsdName'] = str(result['bsdPath'])[len('/dev/'):]
			else:
				result['bsdPath'] = '/dev/' + str(diskutilInfo['DeviceNode'])
				result['bsdName'] = str(diskutilInfo['DeviceNode'])
		
		# diskBsdPath/diskBsdName
		if 'ParentWholeDisk' in diskutilInfo:
			if diskutilInfo['ParentWholeDisk'].startswith('/dev/'):
				result['diskBsdPath'] = str(diskutilInfo['ParentWholeDisk'])
				result['diskBsdName'] = str(diskutilInfo['ParentWholeDisk'])[len('/dev/'):]
			else:
				result['diskBsdPath'] = '/dev/' + str(diskutilInfo['ParentWholeDisk'])
				result['diskBsdName'] = str(diskutilInfo['ParentWholeDisk'])
		
		# volumeUuid
		if 'VolumeUUID' in diskutilInfo:
			result['volumeUuid'] = str(diskutilInfo['VolumeUUID'])
		
		# volumeSizeInBytes
		result['volumeSizeInBytes'] = int(diskutilInfo['TotalSize'])
		
		# volumeFormat
		if 'FilesystemName' in diskutilInfo:
			result['volumeFormat'] = str(diskutilInfo['FilesystemName'])
		
		# diskType
		if diskutilInfo['BusProtocol'] == 'Disk Image':
			result['diskType'] = 'Disk Image'
		elif 'OpticalDeviceType' in diskutilInfo:
			result['diskType'] = 'Optical Disc'
		elif diskutilInfo['BusProtocol'] in ['SATA', 'SAS', 'FireWire', 'USB', 'Fibre Channel Interface']:
			result['diskType'] = 'Hard Drive'
		else:
			raise NotImplementedError('getVolumeInfo does not know how to deal with this volume:\n' + str(diskutilInfo))
		
		return result
	
	@classmethod
	def scoreItemMatch(myClass, itemPath, processInformation, **kwargs):
		
		if os.path.ismount(itemPath):
			return (myClass.getMatchScore(), processInformation)
		
		return (0, processInformation)
	
	@classmethod
	def isVolume(self):
		return True