#!/usr/bin/python

import os, sys, stat, atexit, tempfile

from volumeManager import volumeManager

class tempFolderManager(object):
	
	#---------- class properties ----------
	
	classActivated			= False
	
	defaultFolder			= None				# used when no containing folder is given
	managedItems			= []				# class-wide array, used in atexit cleanup
	
	tempFolderPrefix		= 'InstaDMGTemp'	# default name prefix for temporary folers
	
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
			targetFolder = tempfile.mkdtemp(prefix='InstaDMGTempFolder.', dir='/private/tmp')
			myClass.managedItems.append(targetFolder) # ToDo: log this
			myClass.defaultFolder = targetFolder
			return myClass.defaultFolder
			
		elif targetFolder is None:
			# we are already setup, use the default folder
			return myClass.defaultFolder
		
		targetFolder = os.path.realpath(os.path.normpath(str(targetFolder))) # this will deal with any trailing slashes
		
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
	def cleanupForExit(myClass):
		'''Clean up everything, should be called by an atexit handler'''
		
		while myClass.managedItems is not None and len(myClass.managedItems) > 0:
			thisManagedItem = myClass.managedItems[0]
			
			try:
				if os.path.exists(thisManagedItem):
					myClass.cleanupItem( os.path.realpath(os.path.normpath(thisManagedItem)) )
			
			except Exception, error: # catch everything
				sys.stderr.write('Unable to process the folder: "%s" got error: %s\n' % (thisManagedItem, str(error))) # ToDo: logging
				myClass.managedItems.remove(thisManagedItem)
			
			if thisManagedItem in myClass.managedItems:
				sys.stderr.write('Warning: had to skip "%s", it might not have been deleted!' % thisManagedItem) # ToDo: logging
				myClass.managedItems.remove(thisManagedItem) # get out of bad loops
			
		if myClass.managedItems is not None and not len(myClass.managedItems) == 0:
			raise RuntimeError('cleanupForExit was unable to clean all of the items:\n\t' + '\n\t'.join(myClass.managedItems)) # ToDo: logging and rethink this error classification
		
		myClass.defaultFolder	= None
	
	@classmethod
	def cleanupItem(myClass, targetPath):
		'''Dispose of an item'''
		
		# ToDo: figure out how errors are handled in atexit
		
		if targetPath is None:
			raise ValueError('cleanupItem called with an empty targetPath')
		
		if not os.path.lexists(targetPath):
			raise ValueError('cleanupItem called with a targetPath that does not exist: ' + targetPath)
		
		targetPath = os.path.realpath(os.path.normpath(str(targetPath)))
		
		# check to make sure that this is something we are watching over or a subdirectory of something we are watching over, so we don't get bad calls to this
		inManagedPath = False
		removeManagedFolder = None
		for thisPath in myClass.managedItems:
			
			normedPath = os.path.realpath(os.path.normpath(thisPath))
			
			if os.path.samefile(thisPath, targetPath):
				# the exact path
				inManagedPath = True
				removeManagedFolder = thisPath
			
			elif targetPath.lower().startswith( normedPath.lower() + os.sep ) and os.lstat(targetPath)[stat.ST_DEV] == os.lstat(thisPath)[stat.ST_DEV]:
				# a subpath on the same device
				inManagedPath = True
			
			# check to see if there are managed items within this path - clean them first
			elif normedPath.lower().startswith(targetPath.lower()) and os.lstat(targetPath)[stat.ST_DEV] == os.lstat(thisPath)[stat.ST_DEV]:
				myClass.cleanupItem(thisPath)
		
		if inManagedPath is not True:
			raise ValueError('cleanupItem called with a targetPath that was not in a manged path: ' + targetPath)
		
		# catch things if it is a file or a link
		if os.path.isfile(targetPath) or os.path.islink(targetPath):
			try:
				os.unlink(targetPath)
			except: # ToDo: make this more specific
				pass # ToDo: log this
		
		# walk up the tree to remove any volumes mounted into the path
		for root, dirs, files in os.walk(targetPath, topdown=True):
			
			# unmount the directory if it is a volume
			if os.path.ismount(root):
				volumeManager.unmountVolume(root) # ToDo: log this
				dirs = [] # make sure we don't try to decend into folders that are no longer there
				continue
			
			# delete all files, allowing things to fail
			for thisFile in [os.path.join(root, internalName) for internalName in files]:
				try:
					os.unlink(thisFile)
				except: # ToDo: make this more specific
					pass # ToDo: log this
			
			# catch any symlinks
			for thisFolder in [os.path.join(root, internalName) for internalName in dirs]:
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
		
		if removeManagedFolder is not None:
			myClass.managedItems.remove(removeManagedFolder)
	
	@classmethod
	def addManagedItem(myClass, targetPath):
		'''Add an item to be watched over'''
		
		targetPath = os.path.realpath(os.path.normpath(str(targetPath)))
		
		if not os.path.lexists(targetPath):
			raise ValueError('addmanagedItem called with a targetPath that does not exist: ' + targetPath)
		
		if myClass.getManagedPathForPath(targetPath) is not None:
			return # we are already managing this space

		# the item exists, and is not otherwise accounted for
		myClass.managedItems.append(targetPath)
		return
	
	@classmethod
	def getManagedPathForPath(myClass, targetPath):
		'''Find any managed items that already house this path'''
		
		if targetPath is None or not isinstance(targetPath, str):
			raise ValueError('getManagedPathForPath recieved a target path that it could not understand: ' + str(targetPath))
		
		targetPath = os.path.realpath(os.path.normpath(str(targetPath)))
		
		# rewind back through folders untill we get a path that actually exists
		existingPath = targetPath
		while not os.path.exists(existingPath):
			existingPath = os.path.dirname(existingPath)
		
		for thisMangedPath in myClass.managedItems:
			
			if os.path.exists(targetPath) and os.path.samefile(targetPath, thisMangedPath):
				return thisMangedPath
			
			elif os.path.samefile(existingPath, thisMangedPath):
				return thisMangedPath
			
			elif os.path.isdir(thisMangedPath) and existingPath.lower().startswith( os.path.realpath(os.path.normpath(thisMangedPath)).lower() + os.sep ) and os.lstat(existingPath)[stat.ST_DEV] == os.lstat(thisMangedPath)[stat.ST_DEV]:
				return thisMangedPath
		
		return None
		
	@classmethod
	def getNewTempFolder(myClass, parentFolder=None, prefix=None):
		'''Create a new managed folder and return the path'''
		
		pathToReturn = None
		
		if prefix is None:
			prefix = myClass.tempFolderPrefix
		
		if parentFolder is None:
			# create a new folder inside the current default one
			pathToReturn = tempfile.mkdtemp(dir=myClass.getDefaultFolder(), prefix=prefix)
		
		elif not os.path.isdir(str(parentFolder)):
			raise ValueError('getNewTempFolder called with a parentFolder path that does not exist is is not a directory: ' + str(parentFolder))
		
		else:
			# create the new folder
			pathToReturn = tempfile.mkdtemp(dir=parentFolder, prefix=prefix)
			
			if myClass.getManagedPathForPath(parentFolder) is None:
				# this is an unmanaged path, and we need to add it
				myClass.addManagedItem(pathToReturn)
		
		# return a fully normalized path
		return os.path.realpath(os.path.normpath(pathToReturn))
	
	#---------- instance methods ----------
	
	def __enter__(self):
		return self
	
	def __init__(self, targetPath=None):
				
		if targetPath is None:
			# create a new folder inside the default temporary folder
			targetPath = tempfile.mkdtemp(prefix=self.tempFolderPrefix, dir=self.getDefaultFolder())
		
		targetPath = os.path.realpath(os.path.normpath(str(targetPath)))
		
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
