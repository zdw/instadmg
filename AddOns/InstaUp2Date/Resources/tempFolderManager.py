#!/usr/bin/python

import os, sys, stat, atexit, tempfile, subprocess

import pathHelpers, volumeTools

class tempFolderManager(object):
	
	#---------- class properties ----------
	
	classActivated			= False
	
	defaultFolder			= None			# used when no containing folder is given
	managedItems			= []			# class-wide array, used in atexit cleanup
	managedMounts			= []			# class-wide array, used in atexit cleanup
	
	tempFolderPrefix		= 'idmg_temp.'	# default name prefix for temporary folers
	tempFilePrefix			= 'idmg_file.'	# default name prefix for temporaty files
	mountPointPrefix		= 'idmg_mp.'	# default name prefix for mount points
	
	#-------- instance properties ---------
	
	itemPath				= None
	
	#----------- class methods ------------
	
	@classmethod
	def setDefaultFolder(myClass, targetFolder=None):
		
		if myClass.classActivated is False:
			# arm the atexit handler
			atexit.register(myClass.cleanupForExit)
		
		if targetFolder is None and myClass.defaultFolder is None:
			# setup the system with a default value
			targetFolder = tempfile.mkdtemp(prefix=myClass.tempFolderPrefix, dir='/private/tmp')
			myClass.managedItems.append(targetFolder) # ToDo: log this
			myClass.defaultFolder = targetFolder
			return myClass.defaultFolder
			
		elif targetFolder is None:
			# we are already setup, use the default folder
			return myClass.defaultFolder
		
		targetFolder = pathHelpers.normalizePath(targetFolder) # this will deal with any trailing slashes
		
		if not os.path.isdir(targetFolder):
			raise ValueError('setDefaultFolder called with a path that was not an existing folder: ' + targetFolder)
		
		# check if we are already managing an enclosing folder
		if myClass.getManagedPathForPath(targetFolder) is not None:
			myClass.defaultFolder = targetFolder
			return myClass.defaultFolder
		
		# a new item, not one we had before
		
		if os.path.isdir(targetFolder):
			# the directory already exists, we don't want to potentially kill something
			
			# search through the folder to see if there is anything to protect (not folders, symlinks, or a few select file types)
			for root, dirs, files in os.walk(targetFolder):
				for thisFile in files:
					thisFilePath = os.path.join(root, thisFile)
					if os.path.islink(thisFilePath) or thisFile in [".svn", ".DS_Store"]:
						continue
					
					raise ValueError('setDefaultFolder called with a non-empty folder: %s (%s)' % (targetFolder, thisFilePath))
			
			# register everything to be cleaned up at exit
			myClass.managedItems.append(targetFolder)
			# ToDo: log this
		
		elif os.path.lexists(targetFolder):
			raise ValueError('setDefaultFolder called on a path that is not a directory: ' + targetFolder)
		
		else:
			# since there is nothing in our way, check that the enclosing folder exists and create the temp directory
			if not os.path.isdir(os.path.dirname(targetFolder)):
				raise ValueError('setDefaultFolder can create the target folder, but the enclosing folder must already exist: ' + targetFolder)
			
			# create the directory
			os.mkdir(targetFolder) # ToDo: think through the permissions
			
			# register everything to be cleaned up at exit
			myClass.managedItems.append(targetFolder)
			# ToDo: log this
		
		myClass.defaultFolder = targetFolder
		return myClass.defaultFolder
	
	@classmethod
	def getDefaultFolder(myClass):
		if myClass.defaultFolder is not None:
			return myClass.defaultFolder
		
		else:
			return myClass.setDefaultFolder(None)
	
	@classmethod
	def findManagedItemsInsideDirectory(myClass, targetDirectory):
		'''Return a list of managed items below this path in rough order that they should be cleaned'''
		
		targetDirectory = pathHelpers.normalizePath(targetDirectory)
		
		if not os.path.isdir(targetDirectory) or os.path.islink(targetDirectory):
			raise ValueError('findManagedItemsInsideDirectory requires a directory as the input, and it can not be a symlink' + str(targetDirectory))
		
		itemsToClean = []
		if myClass.managedItems is not None:
			for thisItem in myClass.managedItems:
				if pathHelpers.pathInsideFolder(thisItem, targetDirectory):
					itemsToClean.append(thisItem)
		# Note: this should mean that once sorted and reversed that mounted items get taken care of before their mount-points
		if myClass.managedMounts is not None:
			for thisMount in myClass.managedMounts:
				if pathHelpers.pathInsideFolder(thisMount, targetDirectory):
					itemsToClean.append(thisMount)
		
		itemsToClean.sort() # items inside others should now be below their parents
		itemsToClean.reverse() # the opposite should now be true
		
		return itemsToClean
		
	
	@classmethod
	def cleanupForExit(myClass):
		'''Clean up everything, should be called by an atexit handler'''
		
		for itemToClean in myClass.findManagedItemsInsideDirectory('/'):
			try:
				if os.path.exists(itemToClean):
					myClass.cleanupItem(pathHelpers.normalizePath(itemToClean))
			
			except ValueError, error:
				pass # means the item does not exist
			
			except Exception, error: # catch everything else
				sys.stderr.write('Unable to process the folder: "%s" got error: %s\n' % (itemToClean, str(error))) # ToDo: logging
		
		# check that everything has been cleaned
		
		if myClass.managedItems is None or myClass.managedMounts is None:
			raise RuntimeError('At the end of cleanupForExit managedItems (%s) or managedMounts (%s) was None, this should not happen' % (str(myClass.managedItems), str(myClass.managedMounts)))
		
		elif len(myClass.managedItems) == 0 and len(myClass.managedMounts) == 0:
			pass # the best case, nothing to do here
		
		elif len(myClass.managedItems) == 0 and len(myClass.managedMounts) != 0:
			# just missed mount(s)
			raise RuntimeError('cleanupForExit was unable to clean all of the mount points:\n\t' + '\n\t'.join(myClass.managedMounts)) # ToDo: logging and rethink this error classification
		
		elif len(myClass.managedItems) != 0 and len(myClass.managedMounts) == 0:
			# just missed item(s)
			raise RuntimeError('cleanupForExit was unable to clean all of the items:\n\t' + '\n\t'.join(myClass.managedItems)) # ToDo: logging and rethink this error classification
		
		else:
			# both mounts and items (likely if there is a mount problem)
			raise RuntimeError('cleanupForExit was unable to clean all of the items and mounts:\n\t' + '\n\t'.join(myClass.managedItems + myClass.managedMounts)) # ToDo: logging and rethink this error classification
		
		myClass.defaultFolder	= None
	
	@classmethod
	def cleanupItem(myClass, targetPath):
		'''Dispose of an item'''
		
		if targetPath is None:
			raise ValueError('cleanupItem called with an empty targetPath')
		
		targetPath = pathHelpers.normalizePath(targetPath)
		
		# -- confirm that this item is a managed item, or in a manged space
		
		managedItem		= False
		managedMount	= False
		managedSpace	= False
		
		if targetPath in myClass.managedItems:
			managedItem = True
			managedSpace = True
		else:
			for thisManagedSpace in myClass.managedItems:
				if os.path.isdir(thisManagedSpace) and not os.path.islink(thisManagedSpace) and os.path.lexists(targetPath):
					if pathHelpers.pathInsideFolder(targetPath, thisManagedSpace) and os.lstat(targetPath)[stat.ST_DEV] == os.lstat(thisManagedSpace)[stat.ST_DEV]:
						managedSpace = True
						break
		
		if targetPath in myClass.managedMounts:
			managedMount = True
		
		if managedMount is False and managedSpace is False:
			raise ValueError('cleanupItem handed a path that was not in a managed space or a managed mount: ' + targetPath)
		
		if not os.path.lexists(targetPath):
			if True in [managedItem, managedSpace]:
				# the item no longer exists, we just have to clean it out of managedItems and/or managedMount
				if managedItem is True:
					myClass.managedItems.remove(targetPath)
				if managedMount is True:
					myClass.managedMounts.remove(targetPath)
				
				return
			else:
				raise ValueError('cleanupItem handed a path that does not exist: ' + targetPath)
		
		# -- find any managed items inside this one, and let them handle their business first
		if os.path.isdir(targetPath) and not os.path.islink(targetPath):
			for thisItem in myClass.findManagedItemsInsideDirectory(targetPath):
				myClass.cleanupItem(thisItem)
		
		# -- if this is a mount, unmount it
		if os.path.ismount(targetPath):
			volumeTools.unmountVolume(targetPath)
		
		# -- if this is in controlled space, wipe it
		if managedSpace is True:
			
			# handle the simple cases of a soft-link or a file
			if os.path.islink(targetPath) or os.path.isfile(targetPath):
				try:
					os.unlink(targetPath)
				except OSError:
					# assume that this was a permissions error, and try to chmod it into cooperating
					os.chmod(thisFile, stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH)
					os.unlink(thisFile)
			
			# handle folders
			else:
				# make sure that the permissions on the root folder are ok
				if not os.access(targetPath, os.R_OK | os.X_OK):
					os.chmod(targetPath, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
				
				# walk up the tree to remove any volumes mounted into the path
				for root, dirs, files in os.walk(targetPath, topdown=True):
					
					# unmount the directory if it is a volume
					if os.path.ismount(root):
						volumeTools.unmountVolume(root) # ToDo: log this
						dirs = [] # make sure we don't try to decend into folders that are no longer there
						continue
					
					# delete all files, continuing through failures
					for thisFile in [os.path.join(root, internalName) for internalName in files]:
						try:
							try:
								os.unlink(thisFile)
							except OSError:
								# assume that this was a permissions error, and try to chmod it into cooperating
								os.chmod(thisFile, stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH)
								os.unlink(thisFile)
						
						except: # ToDo: make this more specific
							pass # ToDo: log this				
				
					# catch any symlinks
					for thisFolder in [os.path.join(root, internalName) for internalName in dirs]:
						# make sure we can make it into all sub-folders and delete them:
						if not os.access(thisFolder, os.R_OK | os.X_OK):
							os.chmod(thisFolder, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
						
						if os.path.islink(thisFolder):
							try:
								os.unlink(thisFolder)
							except: # ToDo: make this more specific
								pass # ToDo: log this	
				
				# now that there are no mounted volumes, there should be no files, so delete the folders
				for root, dirs, files in os.walk(targetPath, topdown=False):
					try:
						os.rmdir(root)
					except Exception, error: # ToDo: make this more specific
						sys.stderr.write('Unable to delete folder: "%s" got error: %s' % (root, str(error))) # ToDo: logging
		
		# -- clean this out of both managedItems and managedMounts
		if targetPath in myClass.managedItems:
			myClass.managedItems.remove(targetPath)
		if targetPath in myClass.managedMounts:
			myClass.managedMounts.remove(targetPath)

	
	@classmethod
	def addManagedItem(myClass, targetPath):
		'''Add an item to be watched over'''
		
		targetPath = pathHelpers.normalizePath(targetPath)
		
		if not os.path.lexists(targetPath):
			raise ValueError('addmanagedItem called with a targetPath that does not exist: ' + targetPath)
		
		if myClass.getManagedPathForPath(targetPath) is not None:
			return # we are already managing this space

		# the item exists, and is not otherwise accounted for
		myClass.managedItems.append(targetPath)
	
	@classmethod
	def addManagedMount(myClass, mountPoint):
		
		mountPoint = pathHelpers.normalizePath(mountPoint, followSymlink=True)
		
		myClass.addManagedItem(mountPoint)
		
		for thisMount in myClass.managedMounts:
			if os.path.samefile(thisMount, mountPoint):
				return
		
		myClass.managedMounts.append(mountPoint)
	
	@classmethod
	def removeManagedItem(myClass, targetPath):
		'''Remove an item from the list of managed items'''
		
		targetPath = pathHelpers.normalizePath(targetPath)
		
		if not targetPath in myClass.managedItems:
			raise ValueError('removeManagedItem called with a targetPath that was not a managed path: ' + targetPath)
		
		myClass.managedItems.remove(targetPath)
	
	@classmethod
	def isManagedItem(myClass, thisItem):
		
		if thisItem is None or not os.path.exists(thisItem):
			raise ValueError('isManagedMount requires a valid item, got: ' + str(thisItem))
		
		thisItem = pathHelpers.normalizePath(thisItem)
		
		for thisMount in myClass.managedMounts:
			if pathHelpers.normalizePath(thisMount) == thisItem:
				return True
		
		return myClass.isManagedMount(thisItem)
	
	@classmethod
	def isManagedMount(myClass, mountPoint):
		
		if mountPoint is None or not os.path.ismount(mountPoint):
			raise ValueError('isManagedMount requires a valid mount point, got: ' + str(mountPoint))
		
		mountPoint = pathHelpers.normalizePath(mountPoint)
		
		for thisMount in myClass.managedMounts:
			if pathHelpers.normalizePath(thisMount) == mountPoint:
				return True
		
		return False
	
	@classmethod
	def getManagedPathForPath(myClass, targetPath):
		'''Find any managed items that already house this path'''
		
		if targetPath is None or not hasattr(targetPath, 'capitalize'):
			raise ValueError('getManagedPathForPath recieved a target path that it could not understand: ' + str(targetPath))
		
		targetPath = pathHelpers.normalizePath(targetPath)
		
		# rewind back through folders untill we get a path that actually exists
		existingPath = targetPath
		while not os.path.exists(existingPath):
			existingPath = os.path.dirname(existingPath)
		
		for thisMangedPath in myClass.managedItems:
			
			if os.path.exists(targetPath) and os.path.samefile(targetPath, thisMangedPath):
				return thisMangedPath
			
			elif os.path.samefile(existingPath, thisMangedPath):
				return thisMangedPath
			
			elif os.path.isdir(thisMangedPath) and existingPath.lower().startswith( pathHelpers.normalizePath(thisMangedPath).lower() + os.sep ) and os.lstat(existingPath)[stat.ST_DEV] == os.lstat(thisMangedPath)[stat.ST_DEV]:
				return thisMangedPath
		
		return None
	
	@classmethod
	def getNewTempItem(myClass, fileOrFolder, parentFolder=None, prefix=None, suffix=None):
		'''Create a new managed file or folder and return the path'''
		
		if not fileOrFolder in ['file', 'folder']:
			raise ValueError('getNewTempITem only accepts "file" or "folder" for the fileOrFolder attribute, was given: ' + str(fileOrFolder))
		
		pathToReturn = None
		
		if prefix is None:
			if fileOrFolder == 'file':
				prefix = myClass.tempFilePrefix
			else:
				prefix = myClass.tempFolderPrefix
		
		if suffix is None:
			suffix=''
		
		if parentFolder is None:
			# create a new folder/file inside the current default one
			parentFolder = myClass.getDefaultFolder()
		
		elif not os.path.isdir(str(parentFolder)):
			raise ValueError('getNewTempFolder called with a parentFolder path that does not exist is is not a directory: ' + str(parentFolder))
		
		if fileOrFolder == 'file':
			openFile, pathToReturn = tempfile.mkstemp(dir=parentFolder, prefix=prefix, suffix=suffix)
			os.close(openFile)
		else:
			# create the new folder
			pathToReturn = tempfile.mkdtemp(dir=parentFolder, prefix=prefix)
		
		pathToReturn = pathHelpers.normalizePath(pathToReturn)
		
		# make sure that this file/folder is in managed space
		if myClass.getManagedPathForPath(pathToReturn) is None:
			# this is an unmanaged path, and we need to add it
			myClass.addManagedItem(pathToReturn)
		
		# return a fully normalized path
		return pathToReturn
	
	@classmethod
	def getNewTempFolder(myClass, parentFolder=None, prefix=None, suffix=None):
		'''Create a new managed file or folder and return the path'''
		
		return myClass.getNewTempItem('folder', parentFolder=parentFolder, prefix=prefix, suffix=suffix)
	
	@classmethod
	def getNewMountPoint(myClass, parentFolder=None, prefix=None, suffix=None):
		'''Create a new folder as a mount point'''
		newMountPoint = myClass.getNewTempItem('folder', parentFolder=parentFolder, prefix=prefix, suffix=suffix)
		myClass.addManagedMount(newMountPoint)
		return newMountPoint
	
	@classmethod
	def getNewTempFile(myClass, parentFolder=None, prefix=None, suffix=None):
		'''Create a new managed file or folder and return the path'''
		
		return myClass.getNewTempItem('file', parentFolder=parentFolder, prefix=prefix, suffix=suffix)
	
	#---------- instance methods ----------
	
	def __enter__(self):
		return self
	
	def __init__(self, targetPath=None):
				
		if targetPath is None:
			# create a new folder inside the default temporary folder
			targetPath = tempfile.mkdtemp(prefix=self.tempFolderPrefix, dir=self.getDefaultFolder())
		
		targetPath = pathHelpers.normalizePath(targetPath)
		
		if not os.path.isdir(os.path.dirname(targetPath)):
			raise ValueError('%s called with a targePath whose parent directory does not exist: %s' % (self.__class__.__name__, targetPath))
		
		elif not os.path.lexists(targetPath):
			# create a folder here
			os.mkdir(targetPath)
		
		self.addManagedItem(targetPath)
		self.itemPath = targetPath
	
	def __exit__(self, type, value, traceback):
		self.cleanup()
	
	def getPath(self):
		return self.itemPath
	
	def cleanup(self):
		'''dispose of this item'''
		self.cleanupItem(self.itemPath)
