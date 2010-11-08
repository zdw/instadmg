#!/usr/bin/python

import weakref, warnings

warnings.simplefilter("ignore", DeprecationWarning) # supress the warnings about "new" not taking paramaters

class actionBase(object):
	'''An abstract class underlying the classes that install things on target dmgs'''
	
	container				= None
	
	matchScoreIncrement		= 5

	# -------- class methods
	
	def __init__(self, inputItem, processInformation=None, **kwargs):
		
		if not hasattr(inputItem, "isContainerType"):
			raise ValueError('%s recieved an inputItem that was not a container: %s (%s)' % (self.__class__.__name__, str(inputItem), type(inputItem)))
		
		self.container = inputItem
		
		# -- setup the subclass
		self.subclassInit(inputItem, **kwargs)
	
	def __new__(myClass, inputItem, processInformation, **kwargs):
		'''Ensure that only a single object gets created for each targeted object'''
		
		# -- validate input 
		
		if not hasattr(inputItem, "getStoragePath"):
			raise ValueError('inputItem must be a subclass of containerBase, got: %s (%s)' % (str(inputItem), type(inputItem)))
		
		# --
		
		# ensure that the class has been setup
		try:
			myClass.__instances__
		except AttributeError:
			myClass.__instances__ = weakref.WeakValueDictionary()
		
		# get the instance key
		instanceKey = inputItem.getInstanceKey()
		if 'instanceKeys' in processInformation and myClass.__name__ in processInformation['instanceKeys']:
			instanceKey = processInformation['instanceKeys'][myClass.__name__]
		
		# check if we already have an object for this
		if instanceKey not in myClass.__instances__:
			
			returnObject = object.__new__(myClass, inputItem, processInformation, **kwargs)
			
			# do the setup on this object with the modified values
			returnObject.__init__(inputItem, processInformation, **kwargs)
			
			# get a weak refernce
			myClass.__instances__[instanceKey] = returnObject
		
		return myClass.__instances__[instanceKey]
	
	@classmethod
	def getSubclasses(myClass):
		return myClass.__subclasses__()
	
	@classmethod
	def scoreItemMatch(myClass, pathToTarget):
		'''All classes should impliment this method to help figure out which type should be used for each item'''
		raise NotImplementedError('This method is virtual, and should be implimented in the subclasses')
	
	@classmethod
	def getMatchScore(myClass):
		if myClass not in myClass.__mro__[-2:]: # this is not the base class or 'object'
			return myClass.__mro__[1].getMatchScore() + myClass.matchScoreIncrement
		
		return myClass.matchScoreIncrement
	
	@classmethod
	def getType(myClass):
		return myClass.__name__
	
	# -------- instance methods
	
	def subclassInit(self, itemPath, **kwargs):
		'''Any subclasses that need to set themselves up should impliment this'''
	
	# ---- container methods
	
	# ---- action methods
	
	def performActionOnVolume(self, targetVolume):
		raise NotImplementedError('This method is virtual, and should be implimented by the appropriate subclass')
