#!/usr/bin/python

import os

def normalizePath(inputPath):
	
	inputPath = str(inputPath)
	
	if inputPath == "/":
		return "/"
	
	# expand tildes
	inputPath = os.path.expanduser(inputPath)
	
	# remove trailing slashes
	while inputPath.endswith(os.sep) and not inputPath.endswith('\\' + os.sep):
		inputPath = inputPath[:-1]
	
	return os.path.join(os.path.realpath(os.path.dirname(inputPath)), os.path.basename(inputPath))


def pathInsideFolder(testPath, testFolder):
	
	# short circut for root
	if testFolder == "/":
		return True
	
	# make sure that testFolder is not a link
	if os.path.islink(testFolder) or not os.path.isdir(testFolder):
		raise ValueError('The testFolder given to pathInsideFolder must be a folder (can not be a soft-link):' + testFolder)
	
	# normalize them
	testPath	= normalizePath(testPath)
	testFolder	= normalizePath(testFolder)
	
	# at this point there should be no trailing slashes
	
	# ToDo: handle the case where capitalization messes us up
	
	if testPath.startswith(testFolder + os.sep):
		return True
	else:
		return False
