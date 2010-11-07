#!/usr/bin/python

import os, shutil

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
	
	# ---- instance methods
	
	def performActionOnVolume(self, targetVolume):
		'''Copy the .apps into the /Applications folder on the target volume'''
		
		# -- validate input
		
		targetVolumePath = None
		
		if hasattr(targetVolume, 'getWorkingPath'):
			targetVolumePath = targetVolume.getWorkingPath()
		
		elif hasattr(targetVolume, 'capitalize'):
			targetVolumePath = str(targetVolume)
		
		else:
			raise ValueError('The item given as the targetVolume could not be understood: %s (%s)' % (str(targetVolume), type(targetVolume)))
		
		if not os.path.exists(targetVolumePath):
			raise ValueError('The given targetVolume (%s) does not exist: ' + targetVolumePath)
		
		targetFolder = os.path.join(targetVolumePath, 'Applications')
		if not os.path.isdir(targetFolder):
			raise ValueError('The given targetVolume (%s) does not have an Applications folder' % targetVolumePath)
		
		# --
		
		self.container.prepareForUse()
		
		for itemPath in self.container.getTopLevelItems():
			
			# filter out non .app items
			if not itemPath.lower().endswith('.app'):
				continue
			
			# copy the item in
			shutil.copytree(itemPath, os.path.join(targetVolumePath, 'Applications', os.path.basename(itemPath)), symlinks=True)
			# ToDo: log this
		
		self.container.cleanupAfterUse()
				
