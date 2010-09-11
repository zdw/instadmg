#!/usr/bin/python

import os, unittest, pwd

if __name__ == "__main__":
	
	# import all of the modules that end in _test.py
	containingDir = os.path.dirname(__file__)
	for root, folders, files in os.walk(containingDir):
		importPath = []
		importPath += root[len(containingDir):].split(os.sep)
		
		if '' in importPath:
			importPath.remove('')
		
		for thisDir in folders:
			if thisDir == '.svn':
				folders.remove(thisDir)
		
		for thisFile in files:
			if thisFile.endswith('_test.py'):
				exec("from " + '.'.join(importPath + [os.path.splitext(thisFile)[0]])+ " import *")

#	if os.getuid() == 0:
#		# run as both root, and a user
#		unittest.main(exit=False)
#		os.setuid(pwd.getpwnam(os.getlogin()).pw_uid)
	
	unittest.main()