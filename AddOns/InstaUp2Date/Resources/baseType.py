#!/usr/bin/python

class baseType(object):
	
	baseClass = None
	
	def __new__(myClass, itemPath, **kwargs):
		'''Evaluate this path for each of the subclasses, and instantiate one that gives back the highest value'''
		
		topScorer			= None
		topScore			= 0
		
		processInformation	= { 'instanceKeys':{} }
			# information to be passed along between scoreItemMatch methods and finally the init
		
		
		
		for thisClass in myClass.baseClass.getSubclasses():
			if thisClass in [myClass.baseClass, object]:
				continue
			
			# if this class does not impliment its own scoreItemMatch method, fail
			if thisClass.scoreItemMatch == thisClass.__mro__[1].scoreItemMatch:
				raise NotImplementedError('The % class does not impliment its own scoreItemMatch function as required' % thisClass.__name__)
			
			thisScore = 0
			try:
				thisScore = thisClass.scoreItemMatch(itemPath, processInformation, **kwargs)
			except Exception, e:
				# ToDo: log this
				continue
			
			if thisScore > topScore:
				topScore = thisScore
				topScorer = thisClass
			
		if topScorer is None:
			raise ValueError('There are no subclasses that match this item: ' + itemPath)
		
		return topScorer(itemPath, processInformation, **kwargs)		
	
	@classmethod
	def typeSetup(myClass, itemPath, processInformation, **kwargs):
		'''Perform any type-level setup on this item, such as container setup'''
	
	def __init__(myClass, itemPath, **kwargs):
		raise NotImplementedError('This should have been implimented by an appropriate subclass')
