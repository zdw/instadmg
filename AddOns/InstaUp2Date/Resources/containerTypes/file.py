#!/usr/bin/python

import os

from container		import container

class file(container):
	'''Class to handle files'''
	
	# ------ instance properties
	
	# ------ class properties
	
	# ------ instance methods
	
	# ------ class methods
	
	@classmethod
	def scoreItemMatch(myClass, itemPath, processInformation):
		
		if os.path.isfile(itemPath):
			return (myClass.getMatchScore(), processInformation)
		
		return (0, processInformation)