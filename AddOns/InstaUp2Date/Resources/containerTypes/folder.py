#!/usr/bin/python

import os

from containerBase		import containerBase

class folder(containerBase):
	'''Class to handle folders'''
	
	# ------ instance properties
	
	# ------ class properties
	
	# ------ instance methods
	
	# ------ class methods
	
	@classmethod
	def scoreItemMatch(myClass, itemPath, processInformation, **kwargs):
		
		if os.path.isdir(itemPath):
			return (myClass.getMatchScore(), processInformation)
		
		return (0, processInformation)
	
		
		