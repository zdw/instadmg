#!/usr/bin/python

import os

from folder					import folder

try:
	from .managedSubprocess					import managedSubprocess
except ImportError:
	from .Resources.managedSubprocess		import managedSubprocess



class volume(folder):
	
	# ------ instance properties
	
	volumeName				= None	# possibly seperate from the display name
	
	bsdName					= None
	bsdPath					= None
	
	deviceBSDName			= None
	deviceBSDPath			= None
	
	mountedReadWrite		= None
	
	# ------ class properties
	
	volumeTypesHandled		= []
	
	# ------ instance methods
	
	# ------ class methods
	
	@classmethod
	def diskutilInfo(myclass, identifier):
		'''Return processed information from hdiutil about this path'''
		
		if not isinstance(identifier, str):
			raise ValueError('getVolumeInfo requires a path, bsd name, or a dev path. Got: ' + str(identifier))
		
		command = ['/usr/sbin/diskutil', 'info', '-plist', str(identifier)]
		try:
			process = managedSubprocess(command, processAsPlist=True)
		except RuntimeError, error:
			raise ValueError('The input to getVolumeInfo does not look like it was valid: ' + str(identifier) + "\nError:\n" + str(error))
		volumeProperties = process.getPlistObject()
		
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
	def scoreItemMatch(myClass, itemPath, processInformation):
		
		if os.path.ismount(itemPath):
			return (myClass.getMatchScore(), processInformation)
		
		return (0, processInformation)
	
	@classmethod
	def isVolume(self):
		return True