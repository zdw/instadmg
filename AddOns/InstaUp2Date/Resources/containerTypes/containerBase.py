#!/usr/bin/python

import os, weakref, warnings

warnings.simplefilter("ignore", DeprecationWarning) # supress the warnings about new not taking paramaters

try:
	from .pathHelpers					import normalizePath
except ImportError:
	from .Resources.pathHelpers			import normalizePath

class containerBase(object):
	'''An abstract class underlying file, folder, volume, and dmg classes'''
	
	# ------ instance properties
	
	filePath				= None		# path to the item in the filesystem
	displayName				= None
	
	instanceKey				= None		# string used to confirm the uniqueness of the object
	
	# ------ class properties
	
	itemAlreadySetup		= False		# keep existing items from being re-setup
	
	matchScoreIncrement		= 5
	
	# ------ instance methods
	
	def __new__(myClass, itemPath, processInformation, **kwargs):
		'''Ensure that only a single object gets created for each targeted object'''
		
		# ensure that the class has been setup
		try:
			myClass.__instances__
		except AttributeError:
			myClass.__instances__ = weakref.WeakValueDictionary()
		
		# get the instance key
		instanceKey = itemPath
		if 'instanceKeys' in processInformation and myClass.__name__ in processInformation['instanceKeys']:
			instanceKey = processInformation['instanceKeys'][myClass.__name__]
		
		# check if we already have an object for this
		if instanceKey not in myClass.__instances__:
			
			returnObject = object.__new__(myClass, itemPath, processInformation, **kwargs)
			
			# do the setup on this object with the modified values
			returnObject.__init__(itemPath, processInformation, **kwargs)
			returnObject.instanceKey = instanceKey
			
			# get a weak refernce
			myClass.__instances__[instanceKey] = returnObject
		
		return myClass.__instances__[instanceKey]
	
	def __init__(self, itemPath, processInformation=None, **kwargs):
		
		if self.itemAlreadySetup is False:
			
			self.filePath = itemPath
			self.displayName = os.path.basename(itemPath)
			
			self.classInit(itemPath, processInformation, **kwargs)
		
		self.itemAlreadySetup = True
	
	def getInstanceKey(self):
		return self.instanceKey
	
	# ---- subclass methods
	
	def classInit(self, itemPath, processInformation, **kwargs):
		'''Perform validation and setup specific to this class'''
	
	def getDisplayName(self):
		'''Get a user-oriented string for this item'''
		return self.displayName
	
	def getStoragePath(self):
		'''Return path to the local archive path for this item'''
		return self.filePath
	
	def prepareForUse(self, inVolume=None):
		'''Return path to the local archive path for this item - noop for most types'''
	
	def getWorkingPath(self):
		'''Return path used to work with this item, possibly a copy inside a volume for use with chroot'''
		return self.filePath
	
	def getTopLevelItems(self):
		'''Return an array of files in the top-level of this container'''
		raise NotImplementedError('This class must be implemented by the subclass')

	def cleanupAfterUse(self):
		'''Allow the item to cleanup, such as unmounting or deleting copies made for use in a chroot - noop for most types'''
	
	# ------ class methods
	
	@classmethod
	def isContainerType(myClass, thisType, includeSubclasses=True):
		'''If this item/class is the class or a subclass of the type given'''
		
		if includeSubclasses is False:
			if myClass.__name__ == str(thisType):
				return True
		else:
			for thisClass in myClass.__mro__:
				if thisClass.__name__ == str(thisType):
					return True
		
		return False
	
	@classmethod
	def getSubclasses(myClass):
		'''Get the iterative list of all subclasess of this class'''
		
		classList = myClass.__subclasses__()
		
		for thisClass in myClass.__subclasses__():
			classList += thisClass.getSubclasses()
		
		return classList
	
	@classmethod
	def getMatchScore(myClass):
		if myClass not in myClass.__mro__[-2:]: # this is not the base class or 'object'
			return myClass.__mro__[1].getMatchScore() + myClass.matchScoreIncrement
		
		return myClass.matchScoreIncrement
	
	@classmethod
	def scoreItemMatch(myClass, inputItem, processInformation, **kwargs):
		'''All classes should impliment this method to help figure out which type should be used for each item'''
		raise NotImplementedError('This method is virtual, and should be implimented in the subclasses')
	
	@classmethod
	def getType(myClass):
		return myClass.__name__
		
	@classmethod
	def isVolume(self):
		return False


		