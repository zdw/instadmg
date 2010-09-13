#!/usr/bin/python

from containerTypes		import *

def newContainerForPath(itemPath, **kwargs):
	'''Evaluate this path for each of the subclasses, and instantiate one that gives back the highest value'''
	
	topScorer			= None
	topScore			= 0
	
	processInformation	= {}	# information to be passed along between scoreItemMatch methods and finally the init
	
	for thisClass in container.container.getSubclasses():
		if thisClass == container.container:
			continue
		
		# if this class does not impliment its own scoreItemMatch method, fail
		if thisClass.scoreItemMatch == thisClass.__mro__[1].scoreItemMatch:
			raise NotImplementedError('The % class does not impliment its own scoreItemMatch function as required' % thisClass.__name__)
		
		thisScore, processInformation = thisClass.scoreItemMatch(itemPath, processInformation)
		if thisScore > topScore:
			topScore = thisScore
			topScorer = thisClass
		
	if topScorer is None:
		raise ValueError('There are no subclasses that match this item: ' + itemPath)
	
	return topScorer(itemPath, processInformation, *kwargs)