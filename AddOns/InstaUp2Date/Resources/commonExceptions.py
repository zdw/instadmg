#!/usr/bin/python

class FileNotFoundException(Exception):
	pass

class CatalogNotFoundException(FileNotFoundException):
	pass