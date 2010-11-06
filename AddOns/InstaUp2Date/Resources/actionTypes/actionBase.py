#!/usr/bin/python

class actionBase(object):
	'''An abstract class underlying the classes that install things on target dmgs'''
	
	container		= None

	# -------- class methods
	
	def __init__(self, container, **kwargs):
		
		# ToDo: validate that container is a container
		
		self.container = container
		
		# -- setup the subclass
		self.subclassInit(container, **kwargs)
	
	def __new__(self, container, **kwargs):
		'''Evaluate this path for each of the subclasses, and instantiate one that gives back the highest value'''
		
		topScorer	= None
		topScore	= 0
		
		for thisClass in self.listSubclasses():
			thisScore = thisClass.scoreItemMatch(itemPath)
			if thisScore > topScore:
				topScore = thisScore
				topScorer = thisClass
		
		if topScorer is None:
			raise ValueError('There are no subclasses that match this item: ' + itemPath)
		
		return thisClass(itemPath, kwargs)
	
	@classmethod
	def getSubclasses(myClass):
		return myClass.__subclasses__()
	
	@classmethod
	def scoreItemMatch(myClass, pathToTarget):
		'''All classes should impliment this method to help figure out which type should be used for each item'''
		raise NotImplementedError('This method is virtual, and should be implimented in the subclasses')
	
	@classmethod
	def getType(myClass):
		return myClass.__name__
	
	# -------- instance methods
	
	def subclassInit(self, itemPath, **kwargs):
		'''Any subclasses that need to set themselves up should impliment this'''
		raise NotImplementedError('This method is virtual, and should be implimented byt the appropriate subclass')
	
	# ---- container methods
	
	# ---- install methods
	
	def install(self):
		raise NotImplementedError('This method is virtual, and should be implimented byt the appropriate subclass')		