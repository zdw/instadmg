#!/usr/bin/python

class FileNotFoundException(Exception):
	pass

class CatalogNotFoundException(FileNotFoundException):
	pass

class InstallerChoicesFileException(Exception):
	pass