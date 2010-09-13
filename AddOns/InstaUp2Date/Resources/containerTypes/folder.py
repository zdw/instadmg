#!/usr/bin/python

import os

from container		import container

class folder(container):
	'''Class to handle folders'''
	
	# ------ instance properties
	
	# ------ class properties
	
	# ------ instance methods
	
	# ------ class methods
	
	@classmethod
	def scoreItemMatch(myClass, itemPath, processInformation):
		
		if os.path.isdir(itemPath):
			return (myClass.getMatchScore(), processInformation)
		
		return (0, processInformation)
	
		
		