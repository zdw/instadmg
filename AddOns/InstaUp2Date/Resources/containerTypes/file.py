#!/usr/bin/python

import os

from containerBase		import containerBase

class file(containerBase):
	'''Class to handle files'''
	
	# ------ instance properties
	
	# ------ class properties
	
	# ------ instance methods
	
	# ------ class methods
	
	@classmethod
	def scoreItemMatch(myClass, itemPath, processInformation, **kwargs):
		
		if os.path.isfile(itemPath):
			return myClass.getMatchScore()
		
		return 0