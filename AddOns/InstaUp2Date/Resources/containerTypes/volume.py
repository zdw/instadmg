#!/usr/bin/python

import os, Foundation

from folder					import folder

try:
	from .volumeTools			import getDiskutilInfo
	from .managedSubprocess				import managedSubprocess
	from .tempFolderManager				import tempFolderManager
	from .volumeTools			import unmountVolume
	from .pathHelpers			import pathInsideFolder
except ImportError:
	from ..volumeTools			import getDiskutilInfo
	from ..managedSubprocess			import managedSubprocess
	from ..tempFolderManager			import tempFolderManager
	from ..volumeTools			import unmountVolume
	from ..pathHelpers			import pathInsideFolder


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
	
	weMounted			= False	# set to True if this code mounted the dmg
		
	# ------ class properties
	
	volumeTypesHandled		= []
	
	# ------ instance methods
	
	def classInit(self, itemPath, processInformation):
		
		# -- get and populate the information from diskutil about this item
		
		diskutilInfo = None
		if 'diskutilInfo' in processInformation:
			diskutilInfo = processInformation['diskutilInfo']
		else:
			wasMounted = True
			mountPoint = self.getMountPoint()
			if mountPoint is None:
				wasMounted = False
				mountPoint = self.mount()
			
			diskutilInfo = self.diskutilInfo(self.getMountPoint())
			
			if wasMounted is False:
				self.unmount()
		
		# volumeName
		if 'volumeName' in diskutilInfo:
			self.volumeName = diskutilInfo['volumeName']
			self.displayName = diskutilInfo['volumeName']
		else:
			self.displayName = diskutilInfo['bsdPath']
		
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
	
	def mount(self, mountPoint=None, mountInFolder=None, mountReadWrite=None):
		
		# -- police the input
		
		deviceInfo = self.diskutilInfo(self.bsdPath)
		currentMountPoint = None
		if 'mountPath' in deviceInfo:
			currentMountPoint = deviceInfo['mountPath']
		
		# mountReadWrite
		if mountReadWrite is None:
			pass # nothing to do here
		
		elif mountReadWrite not in [True, False]:
			raise ValueError('mountReadWrite can only by None, True, or False')
			
		elif currentMountPoint is not None and deviceInfo['mountedReadWrite'] != mountReadWrite:
			raise RuntimeError('mount called with mountReadWrite=%s, but the volume was already mounted with mountReadWrite=%s' % (mountReadWrite, deviceInfo['mountedReadWrite']))
		
		# mountPoint/mountInFolder
		
		if mountPoint is not None and mountInFolder is not None:
			raise ValueError('mount can only be called with mountPoint or mountInFolder, not both')
		
		if currentMountPoint is not None and mountPoint is not None:
			if os.path.samefile(mountPoint, currentMountPoint):
				return currentMountPoint # nothing to do here
			else:
				raise RuntimeError('This volume "%s" (%s) was already mounted at "%s" when it was requested at "%s"' % (self.getDisplayName(), self.bsdPath, currentMountPoint, mountPoint))
		
		elif mountPoint is not None and os.path.ismount(mountPoint):
			raise ValueError('mount called with a mountpoint that already has something mounted at it: ' + str(mountPoint))
		
		elif mountPoint is not None and os.path.exists(mountPoint) and not os.path.isdir(mountPoint):
			raise ValueError('mount called with a mountpoint that is not a folder: ' + str(mountPoint))
		
		elif mountPoint is not None and not os.path.exists(mountPoint) and os.path.isdir(os.path.dirname(mountPoint)):
			# create a temporary folder for this
			os.mkdir(mountPoint)
			tempFolderManager.addManagedItem(mountPoint)
		
		elif mountPoint is not None and not os.path.isdir(os.path.dirname(mountPoint)):
			 raise ValueError('mount called with a mountpoint whose parent folder is not a directory: ' + str(mountPoint))
		
		elif mountInFolder is not None and not os.path.isdir(mountInFolder):
			raise ValueError('mount called with a mountInFolder value that is not a directory: ' + str(mountInFolder))
		
		elif currentMountPoint is not None and mountInFolder is not None:
			if not pathInsideFolder(currentMountPoint, mountInFolder):
				raise RuntimeError('mount called on %s (%s) with a mountInFolder value of "%s", but it was already mounted at: %s' % (self.getDisplayName(), self.bsdPath, currentMountPoint, mountPoint))
			
			# create the mount point
			mountPoint = tempFolderManager.getNewMountPoint(parentFolder=mountInFolder)
		
		# -- build the command
		
		command = ['/usr/sbin/diskutil', 'mount']
		
		if mountReadWrite is True:
			command.append('readOnly')
		
		if mountPoint is not None:
			command += ['-mountPoint', mountPoint]
		
		command.append(self.bsdPath)
		
		# -- run the command
		
		managedSubprocess(command)
		
		# -- find and return the mount point
		
		self.weMounted = True
		return self.getMountPoint()
	
	def unmount(self):
		
		currentMountPoint = self.getMountPoint()
		if currentMountPoint in [None, '']:
			return # ToDo: log this, maybe error out here
		
		if self.weMounted is not True:
			raise ValueError('Asked to unmount a volume that we did not mount: %s' % self.getDisplayName())
		
		if tempFolderManager.isManagedItem(currentMountPoint):
			tempFolderManager.cleanupItem(currentMountPoint)
		else:
			unmountVolume(currentMountPoint)
			self.weMounted = False
	
	def prepareForUse(self, inVolumeOrFolder=None):
		
		enclosingFolder = None
		
		# vaidate input
		if inVolumeOrFolder is not None:
			
			if os.path.ismount(inVolumeOrFolder):
				if not os.path.isdir(os.path.join(inVolumeOrFolder, "Volumes")):
					raise Exception('When preparing "%s" for use was given "%s", but that path does not have a "Volumes" folder in it' % (self.getDisplayName(), inVolumeOrFolder))
				enclosingFolder = os.path.join(inVolumeOrFolder, "Volumes")
				
			elif os.path.isdir(inVolumeOrFolder):
				enclosingFolder = inVolumeOrFolder
			
			else:
				raise ValueError('inVolumeOrFolder nots not exist, or was not recognized: ' + str(inVolumeOrFolder))
		
		mountPoint = self.getMountPoint()
		
		if mountPoint is not None:
			
			if enclosingFolder is not None and pathInsideFolder(mountPoint, enclosingFolder) is False: # otherwise we are ok with where it is mounted
				
				if self.weMounted is False:
					raise RuntimeError('Was asked to make sure that "%s" was mounted in "%s" (rather in "%s"), but it was already mounted, and not by this system' % (self.getDisplayName(), enclosingFolder, mountPoint))
				
				# re-mount the volume as desired
				self.unmount()
				self.mount(mountInFolder=enclosingFolder)
			
		else:
			# mount it
			self.mount(mountInFolder=enclosingFolder)
		
	def cleanupAfterUse(self):
		
		if self.isMounted() is True and self.weMounted is True:
			self.unmount()
		
		if self.weMounted is True:
			self.weMounted = False
	
	def getTopLevelItems(self):
		'''Return an array of files in the top-level of this volume, mounting (then unmounting) if necessary'''
		
		# make sure that is mounted
		wasMounted = self.isMounted()
		if wasMounted is False:
			self.mount()
		
		results = [os.path.join(self.getWorkingPath(), itemName) for itemName in os.listdir(self.getMountPoint())]
		
		# unount the volume if we just mounted it
		if wasMounted is False:
			self.unmount()
		
		return results
	
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
		
		wasAlreadyMounted = True
		if self.isMounted() is False:
			wasAlreadyMounted = False
			self.mount()
		
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
		
		if os.path.exists(os.path.join(currentMountPoint, "System/Installation/Packages/OSInstall.mpkg")) or os.path.exists( os.path.join(currentMountPoint, "Packages/OSInstall.mpkg") ):
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
		if 'MountPoint' in diskutilInfo and diskutilInfo['MountPoint'] not in [None, '']:
			result['mountPath'] = str(diskutilInfo['MountPoint'])
			
			# mountedReadWrite
			if ('Writable' in diskutilInfo and diskutilInfo['Writable'] is True) or ('WritableVolume' in diskutilInfo and diskutilInfo['WritableVolume'] is True):
				result['mountedReadWrite'] = True
			else:
				result['mountedReadWrite'] = False
		
		# volumeName
		if 'VolumeName' in diskutilInfo:
			result['volumeName'] = str(diskutilInfo['VolumeName'])
		
		# bsdPath/bsdName
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
		if 'BusProtocol' not in diskutilInfo or diskutilInfo['BusProtocol'] is None:
			raise NotImplementedError('getVolumeInfo does not know how to deal with this volume:\n' + str(diskutilInfo))
		elif diskutilInfo['BusProtocol'] == 'Disk Image':
			result['diskType'] = 'Disk Image'
		elif 'OpticalDeviceType' in diskutilInfo:
			result['diskType'] = 'Optical Disc'
		else:
			# default to treating it like a volume
			result['diskType'] = 'Hard Drive'
		
		return result
	
	@classmethod
	def scoreItemMatch(myClass, itemPath, processInformation, **kwargs):
		
		# -- validate input
		
		if not hasattr(itemPath, 'capitalize'):
			raise ValueError('Did not understand itempath: ' + str(itemPath))
		
		# -- check with informaiton from diskutil
		
		# make sure we have the information
		if 'hdiutilInfo' not in processInformation:
			try:
				canidateDiskutilInfo = myClass.diskutilInfo(itemPath)
				
				mountPoint = None
				if 'mountPath' in canidateDiskutilInfo:
					mountPoint = canidateDiskutilInfo['mountPath']
				
				if itemPath in [mountPoint, canidateDiskutilInfo['bsdPath'], canidateDiskutilInfo['bsdName']]:
					processInformation['diskutilInfo'] = canidateDiskutilInfo
				else:
					return 0 # we are getting information for this items parent
			except:
				return 0 # if diskutil does not understand it, it is not a volume
		
		mountPoint = None
		if 'mountPath' in processInformation['diskutilInfo']:
			mountPoint = processInformation['diskutilInfo']['mountPath']
		
		if itemPath in [processInformation['diskutilInfo']['bsdPath'], processInformation['diskutilInfo']['bsdName']] or os.path.samefile(mountPoint, itemPath):
			processInformation['instanceKeys'][myClass.__name__] = processInformation['diskutilInfo']['bsdPath']
			return myClass.getMatchScore()
		
		return 0
	
	@classmethod
	def isVolume(self):
		return True