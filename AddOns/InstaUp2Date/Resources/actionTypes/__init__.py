#!/usr/bin/python

import os

def getAllModules():
	'''Get a list of all python modules in this folder'''
	
	returnValue = []
	
	for thisFile in os.listdir(os.path.dirname(__file__)):
		if thisFile.endswith('.py') and not thisFile.endswith('_test.py'):
			returnValue.append(os.path.splitext(thisFile)[0])
	
	return returnValue

__all__ = getAllModules()