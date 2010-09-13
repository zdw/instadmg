#!/usr/bin/python

import weakref, warnings

from .pathHelpers			import normalizePath

class container(object):
	'''An abstract class underlying file, folder, volume, and dmg classes'''
	
	# ------ instance properties
	
	filePath				= None		# path to the item in the filesystem
	
	chrootFilePath			= None		# the full path to a copy useable in a chroot environment
	
	displayName				= None
	
	# ------ class properties
	
	uniqueAttributes		= []		# place attribute names here that should be used to decide when items are unique
	itemAlreadySetup		= False		# keep existing items from being re-setup
	
	matchScoreIncrement		= 5
	
	
	
	# ------ instance methods
	
	def __new__(myClass, itemPath, processInformation=None, **kwargs):
		'''Ensure that only a single object gets created for each targeted object'''
		
		# ensure that the class has been setup
		try:
			myClass.__instances__
		except AttributeError:
			myClass.__instances__ = weakref.WeakValueDictionary()
		
		# get the key
		thisKey = itemPath
		for thisAttribute in myClass.uniqueAttributes:
			if thisAttribute in kwargs:
				thisKey += ":" + kwargs[thisAttribute]
		
		# check if we already have an object for this
		if thisKey not in myClass.__instances__:
			with warnings.catch_warnings():
				warnings.simplefilter("ignore")
				returnObject = object.__new__(myClass, itemPath, processInformation, **kwargs)
				myClass.__instances__[thisKey] = returnObject
		
		return myClass.__instances__[thisKey]
	
	def __init__(self, itemPath, processInformation=None, **kwargs):
		
		if self.itemAlreadySetup is False:
		
			self.filePath = itemPath
			
			self.classInit(itemPath, processInformation, *kwargs)
		
		self.itemAlreadySetup = True
	
	def classInit(self, itemPath, processInformation, **kwargs):
		'''Perform validation and setup specific to this class'''
	
	def getWorkingPath(self):
		'''Return path used to work with this item, possibly a copy inside a chroot'''
		
		if self.chrootFilePath is not None:
			return self.chrootFilePath
		
		return self.filePath
	
	def setupForUseAtPath(self, path):
		raise NotImplementedError('This method is virtual, and should be implimented in the subclasses')
	
	def getStoragePath(self):
		'''Return path to the local archive path for this item'''
		
		return self.filePath
	
	# ------ class methods
	
	@classmethod
	def getSubclasses(myClass):
		'''Get the iterative list of all subclasess of this class'''
		
		classList = myClass.__subclasses__()
		
		for thisClass in myClass.__subclasses__():
			classList += thisClass.getSubclasses()
		
		return classList
	
	@classmethod
	def getMatchScore(myClass):
		if myClass.__name__ != 'container':
			return myClass.__mro__[1].getMatchScore() + myClass.matchScoreIncrement
		
		return myClass.matchScoreIncrement
	
	@classmethod
	def scoreItemMatch(myClass, itemPath, processInformation):
		'''All classes should impliment this method to help figure out which type should be used for each item'''
		raise NotImplementedError('This method is virtual, and should be implimented in the subclasses')
	
	@classmethod
	def getContainerType(myClass):
		return myClass.__name__
		
	@classmethod
	def isVolume(self):
		return False


		