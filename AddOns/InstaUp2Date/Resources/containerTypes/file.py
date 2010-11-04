#!/usr/bin/python

import os

from containerBase		import containerBase

class file(containerBase):
	'''Class to handle files'''
	
	# ------ instance properties
	
	# ------ class properties
	
	# ------ instance methods
	
	def getTopLevelItems(self):
		'''Since this is only a single file, return the file path'''
		
		return [self.filePath]
	
	# ------ class methods
	
	@classmethod
	def scoreItemMatch(myClass, itemPath, processInformation, **kwargs):
		
		if os.path.isfile(itemPath):
			return myClass.getMatchScore()
		
		return 0