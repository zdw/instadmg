#!/usr/bin/python

import os, subprocess

import pathHelpers
from managedSubprocess	import managedSubprocess

def getDiskutilInfo(identifier):
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
	elif volumeProperties['BusProtocol'] in ['ATA', 'SCSI', 'SATA', 'FireWire', 'USB', 'SAS', 'Fibre Channel Interface']:
		result['diskType'] = 'Hard Drive'
	else:
		raise NotImplementedError('getVolumeInfo does not know how to deal with this volume:\n' + str(volumeProperties))
	
	return result

def getMountedVolumes(excludeRoot=True):
		
	diskutilArguments = ['/usr/sbin/diskutil', 'list', '-plist']
	diskutilProcess = managedSubprocess(diskutilArguments, processAsPlist=True)
	diskutilOutput = diskutilProcess.getPlistObject()
	
	if not "AllDisks" in diskutilOutput or not hasattr(diskutilOutput["AllDisks"], '__iter__'):
		raise RuntimeError('Error: The output from diksutil list does not look right:\n%s\n' % str(diskutilOutput))  
	
	mountedVolumes = []
	
	for thisVolume in diskutilOutput["AllDisks"]:
		
		# get the mount
		thisVolumeInfo = getDiskutilInfo(str(thisVolume))
		
		# exclude whole disks
		if thisVolumeInfo['bsdName'] == thisVolumeInfo['diskBsdName']:
			continue
		
		# exclude unmounted disks
		if not 'mountPath' in thisVolumeInfo or thisVolumeInfo['mountPath'] in [None, '']:
			continue
		# exclude the root mount if it is not requested
		elif thisVolumeInfo['mountPath'] == '/' and excludeRoot == True:
			continue
		
		mountedVolumes.append(str(thisVolumeInfo['mountPath']))
	
	return mountedVolumes

def unmountVolume(targetPath):
	'''Unmount a volume or dmg mounted at the path given'''
	
	if not os.path.ismount(targetPath):
		raise ValueError('unmountVolume valled on a path that was not a mount point: ' + targetPath)
	
	targetPath = pathHelpers.normalizePath(targetPath)
	
	# check to see if this is a disk image
	isMountedDMG = False
	command = ['/usr/bin/hdiutil', 'info', '-plist']
	process = managedSubprocess(command, processAsPlist=True)
	plistData = process.getPlistObject()
	
	if not hasattr(plistData, 'has_key') or not plistData.has_key('images') or not hasattr(plistData['images'], '__iter__'):
		raise RuntimeError('The "%s" output does not have an "images" array as expected. Output was:\n%s' % (' '.join(command), output))
	
	for thisImage in plistData['images']:
	
		if not hasattr(thisImage, '__iter__') or not thisImage.has_key('system-entities') or not hasattr(thisImage['system-entities'], '__iter__'):
			raise RuntimeError('The "%s" output had an image entry that was not formed as expected. Output was:\n%s' % (' '.join(command), output))
		
		for thisEntry in thisImage['system-entities']:
			if thisEntry.has_key('mount-point') and os.path.samefile(thisEntry['mount-point'], targetPath):
				isMountedDMG = True
				break
		if isMountedDMG is True: break
	
	if isMountedDMG is True:
		# ToDo: log this
		command = ['/usr/bin/hdiutil', 'eject', targetPath]
		process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		
		if process.wait() != 0 and os.path.ismount(targetPath):
			# try again with a bit more force
			# ToDo: log this
			
			command = ['/usr/bin/hdiutil', 'eject', '-force', targetPath]
			managedSubprocess(command)
	
	else:
		# a non dmg mount point
		# ToDo: log this
		command = ['/usr/sbin/diskutil', 'unmount', targetPath]
		process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		
		if process.wait() != 0 and os.path.ismount(targetPath):
			# try again with a bit more force
			# ToDo: log this
			
			command = ['/usr/sbin/diskutil', 'unmount', 'force', targetPath]
			managedSubprocess(command)
