#!/usr/bin/python

'''Code used to help testing objects'''

def generateSomeContent(containerFolder, maxFilesInFolders=10, maxSizeofFiles=1000, maxSubFolders=5, maxSubFolderDepth=3):
	'''A convienience method to generate some contents for testing purposes'''
	
	import os, random, string, tempfile
	
	if containerFolder is None or not os.path.isdir(containerFolder):
		raise ValueError('generateSomeContent was given a bad targePath (should be a directory): ' + str(containerFolder))
	
	if (not isinstance(maxFilesInFolders, int) and maxFilesInFolders >= 0):
		raise ValueError('maxFilesInFolders must be a positive integer, got: ' + str(maxFilesInFolders))
	if (not isinstance(maxSizeofFiles, int) and maxSizeofFiles >= 0):
		raise ValueError('maxSizeofFiles must be a positive integer, got: ' + str(maxSizeofFiles))
	if (not isinstance(maxSubFolders, int) and maxSubFolders >= 0):
		raise ValueError('maxSubFolders must be a positive integer, got: ' + str(maxSubFolders))
	if (not isinstance(maxSubFolderDepth, int) and maxSubFolderDepth >= 0):
		raise ValueError('maxSubFolderDepth must be a positive integer, got: ' + str(maxSubFolderDepth))
	
	# build some files (at least one)
	if maxFilesInFolders > 0:
		for i in range(random.randint(1, maxFilesInFolders)):
			(tempFile, tempFileName) = tempfile.mkstemp(dir=containerFolder)
			tempFileObject = os.fdopen(tempFile, "w+b")
			
			for i in range(random.randint(1, maxSizeofFiles)):
				tempFileObject.write(random.choice(string.printable))
			
			tempFileObject.close()
	
	# build some sub-folders
	if maxSubFolderDepth > 0 and maxSubFolders > 0:
		for i in range(random.randint(1, maxSubFolders)):
			generateSomeContent(tempfile.mkdtemp(dir=containerFolder, prefix='tmpdir-'), maxFilesInFolders=maxFilesInFolders, maxSizeofFiles=maxSizeofFiles, maxSubFolders=maxSubFolders, maxSubFolderDepth=maxSubFolderDepth - 1)
