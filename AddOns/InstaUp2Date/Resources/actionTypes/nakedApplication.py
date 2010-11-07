#!/usr/bin/python

import os

import actionBase

class nakedApplication(actionBase.actionBase):
	
	@classmethod
	def scoreItemMatch(myClass, inputItem, processInformation, **kwargs):
		
		# -- validate input
		
		if not hasattr(inputItem, "isContainerType"):
			raise ValueError('inputItem must be a subclass of containerBase, got: %s (%s)' % (str(inputItem), type(inputItem)))
		
		if not hasattr(processInformation, '__iter__'):
			raise ValueError('processInformation must be a dict, got: %s (%s)' % (str(processInformation), type(processInformation)))
		
		# -- score item
		
		# note: we are depending on 'prepareForUse' already having been called on intputItem
		
		foundApps = False
		for thisItem in inputItem.getTopLevelItems():
			
			# bail if there is a .pkg or .mpkg in the folder
			if os.path.splitext(thisItem)[1].lower() in ['.pkg', '.mpkg']:
				return 0
			
			if os.path.splitext(thisItem)[1].lower() == '.app':
				foundApps = True
		
		if foundApps is True:
			return myClass.getMatchScore()
		
		return 0
