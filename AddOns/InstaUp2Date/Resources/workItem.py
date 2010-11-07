#!/usr/bin/python

import urlparse, hashlib, traceback

from containerTypes		import *
from actionTypes		import *

class workItem(object):
	
	# ---- class constants
	
	allowedUrlSchemes	= ['', 'http', 'https']
	
	# ---- instance variables
	
	source				= None
	
	container			= None	# should be a containerType
	action				= None	# should be a actionType
	
	# holding tank for input
	
	sourceLocation		= None
	checksumValue		= None
	checksumType		= None
	kwargs				= None
	
	# validated input
	
	# ---- class methods
	
	@classmethod
	def findItemForParentClass(myClass, parentClass, inputItem, **kwargs):
		'''Evaluate this path for each of the subclasses, and instantiate one that gives back the highest value'''
		
		# -- validate parentClass
		
		if type(parentClass) is not type or not hasattr(parentClass, 'scoreItemMatch'): # not a class that impliments the protocol
			raise ValueError('parentClass must be a class, and must have a method named "scoreItemMatch", got: %s (%s)' % (parentClass, type(parentClass)))
		
		# --
		
		topScorer			= None
		topScore			= 0
		
		processInformation	= { 'instanceKeys':{} }
			# information to be passed along between scoreItemMatch methods and finally the init
		
		for thisClass in parentClass.getSubclasses():
			if thisClass in [parentClass, object]:
				continue
			
			# if this class does not impliment its own scoreItemMatch method, fail
			if thisClass.scoreItemMatch == thisClass.__mro__[1].scoreItemMatch:
				raise NotImplementedError('The % class does not impliment its own scoreItemMatch function as required' % thisClass.__name__)
			
			thisScore = 0
			try:
				thisScore = thisClass.scoreItemMatch(inputItem, processInformation, **kwargs)
			except Exception, e:
				# ToDo: log this
				# print thisClass, e, traceback.print_exc()
				continue
			
			if thisScore > topScore:
				topScore = thisScore
				topScorer = thisClass
			
		if topScorer is None:
			sourcePath = inputItem
			if hasattr(inputItem, 'getStoragePath'):
				sourcePath = inputItem.getStoragePath()
			
			raise ValueError('There are no "%s" subclasses that match this item: %s, subclasses: %s' % (parentClass.getType(), sourcePath, parentClass.getSubclasses()))
		
		return topScorer(inputItem, processInformation, **kwargs)	
	
	# ---- instance methods
	
	# -- setup
	
	def __init__(self, source, checksumString=None, processItem=False, **kwargs):
		'''Parse the input to make sure that it looks right, optionally finding and differntiating the item'''
		
		# -- parse and store input
		
		# sourceLocation
		
		if source is None:
			raise ValueError('source can not be None')
		
		if hasattr(source, 'capitalize'):
			# string, so assume that this is the sourceLocation
			if source.lower().startswith('file://'):
				source = source[len('file://'):]
			
			parsedSourceLocation = urlparse.urlparse(source)
			if parsedSourceLocation.scheme not in self.allowedUrlSchemes:
				raise ValueError('The sourceLocation must be one of the allowed schemes (%s), got: %s' % (str(self.allowedUrlSchemes), parsedSourceLocation.scheme))
			
			self.sourceLocation = source
		
			# checksumString
		
			if checksumString is None and parsedSourceLocation.scheme in ['', None]: # local file
				pass
			
			elif checksumString is None:
				raise ValueError('When using a remote url (not a local file) a checksum must be provided')
			
			elif hasattr(checksumString, 'capitalize'):
				if not checksumString.count(':'):
					raise ValueError('checksumString must have exactly one colon (":") in it, had: %i (%s)' % (checksumString.count(':'), checksumString))
				# ToDo: check the checksum type if we can
				# note: pass on if not
			
			else:
				raise ValueError('checksumString must be a string, got: %s (%s)' % (str(checksumString), type(checksumString)))
			
			if checksumString is not None:
				self.checksumType, self.checksumValue = checksumString.split(':')
				self.checksumValue = self.checksumValue.strip()
				self.checksumType = self.checksumType.lower().strip()
		
			if hasattr(hashlib, 'algorithms'): # true in 2.7
				if self.checksumType not in hashlib.algorithms:
					raise ValueError('The checksumType given (%s) is not one of the algorithms that hashlib supports (%s)' % (self.checksumType, str(hashlib.algorithms)))
		
		elif isinstance(source, containerBase.containerBase):
			
			if checksumString is not None:
				raise ValueError('When given a container as the source, the checksumString can not be given')
			
			self.container = source
			
		else:
			raise ValueError('source must be a string or a container, got: %s (%s)' % (str(source), type(source)))
		
		# squirrel away kwargs for later
		
		self.kwargs = kwargs
		
		# -- possibly process the item
		
		if processItem is True:
			self.locateFiles()
 	
	def locateFiles(self, cacheFolder=None, additionalSourceLocations=None):
		'''Find the actual files, and figure out what subclass of action is appropriate'''
		
		kwargs = self.kwargs
		
		# -- find the container subtype, and instantiate it
		self.container = self.findItemForParentClass(containerBase.containerBase, self.sourceLocation, **kwargs)
		
		# -- find the action subtype
		self.container.prepareForUse() # open things up so we can work faster
		self.action = self.findItemForParentClass(actionBase.actionBase, self.container, **kwargs)
		self.container.cleanupAfterUse()
		
		# ToDo: a method to figure out when the same item is requested twice
	
	# -- container methods
	
	def foundContainer(self):
		if self.container is not None:
			return True
		return False
	
	def getContainer(self):
		if self.foundContainer() is not True:
			raise RuntimeError('This method can not be called until locateFiles has been called')
		return self.container
	
	def getContainerType(self):
		return self.getContainer().getType()
	
	# -- action methods
	
	def foundAction(self):
		if self.action is not None:
			return True
		return False
	
	def getAction(self):
		if self.foundAction() is not True:
			raise RuntimeError('This method can not be called until locateFiles has been called')
		return self.action
	
	def getActionType(self):
		return self.getAction().getType()
	
	def performAction(self):
		raise NotImplementedError()
