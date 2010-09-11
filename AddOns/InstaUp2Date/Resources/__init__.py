#!/usr/bin/python

import os

def getAllModules():
	'''Get a list of all python modules in this folder'''
	
	returnValue = []
	
	for thisFile in os.listdir(os.path.dirname(__file__)):
		if os.path.splitext(thisFile)[1] == '.py':
			returnValue.append(os.path.splitext(thisFile)[0])

__all__ = getAllModules()