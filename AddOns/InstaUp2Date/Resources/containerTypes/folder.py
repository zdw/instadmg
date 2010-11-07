#!/usr/bin/python

import os

from containerBase		import containerBase

class folder(containerBase):
	'''Class to handle folders'''
	
	# ------ instance properties
	
	# ------ class properties
	
	# ------ instance methods
	
	def getTopLevelItems(self):
		'''Return an array of files in this folder'''
		return [os.path.join(self.filePath, itemName) for itemName in os.listdir(self.filePath)]
	
	# ------ class methods
	
	@classmethod
	def scoreItemMatch(myClass, itemPath, processInformation, **kwargs):
		
		if os.path.isdir(itemPath):
			return myClass.getMatchScore()
		
		return 0
