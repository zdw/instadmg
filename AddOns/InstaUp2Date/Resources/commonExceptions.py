#!/usr/bin/python

class FileNotFoundException(Exception):
	pass

class CatalogNotFoundException(FileNotFoundException):
	pass

class InstallerChoicesFileException(Exception):
	choicesFile	= None
	lineNumber	= None
	
	def __init__(self, message, choicesFile=None, lineNumber=None):
		
		super(self.__class__, self).__init__(message)
		
		if choicesFile is not None:
			self.choicesFile = choicesFile
		
		if lineNumber is not None:
			self.lineNumber = lineNumber
