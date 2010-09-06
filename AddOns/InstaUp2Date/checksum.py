#!/usr/bin/env python

import os, sys, optparse, hashlib, urlparse

import Resources.pathHelpers			as pathHelpers
import Resources.commonConfiguration	as commonConfiguration
from Resources.checksum					import checksum
from Resources.displayTools				import statusHandler	

#------------------------------MAIN------------------------------

if __name__ == "__main__":
	
	optionParser = optparse.OptionParser()
	
	if hasattr(hashlib, 'algorithms'):
		optionParser.add_option("-a", "--checksum-algorithm", default="sha1", action="store", dest="checksumAlgorithm", choices=hashlib.algorithms, help="Disable progress notifications") # Python 2.7 and above
	else:
		optionParser.add_option("-a", "--checksum-algorithm", default="sha1", action="store", dest="checksumAlgorithm", help="Disable progress notifications")
	
	optionParser.add_option("-d", "--disable-progress", default=True, action="store_false", dest="reportProgress", help="Disable progress notifications")
	optionParser.add_option("-s", "--chunk-size", default=None, action="store", type="int", dest="chunkSize", help="The size in bytes to use as a buffer")
	
	optionParser.add_option("-t", "--output-folder", default=None, action="store", dest="outputFolder", type="string", help="Write a copy of the remote files to this folder")
	optionParser.add_option("", "--disable-autocache", default=True, action="store_false", dest="autoCacheRemoteFiles", help="Disable automatic caching of remote files")
	optionParser.add_option("", "--disable-chesksum-in-name", default=True, action="store_false", dest="checksumInFileName", help="Disable adding the checksum in the output file name")
	
	(options, args) = optionParser.parse_args()
	
	# confirm that hashlib supports the hash type:
	try:
		hashlib.new(options.checksumAlgorithm)
	except ValueError:
		optionParser.error("Hash type: %s is not supported by hashlib" % options.checksumAlgorithm)
	
	# deafult and check the outputFolder
	if options.outputFolder is None and options.autoCacheRemoteFiles is True:
		options.outputFolder = commonConfiguration.standardCacheFolder
	
	if options.outputFolder is not None and not os.path.isdir(options.outputFolder):
		optionParser.error('The output folder given does not exist, or is not a folder: ' + str(options.outputFolder))
		
	# ToDo: and is writable by this user
	
	if options.checksumInFileName is False and options.outputFolder is None:
		optionParser.error('The --disable-chesksum-in-name option requires that the -t/--output-folder option also be enabled')
	
	for location in args:
		
		if location.startswith('file://'):
			location = location[len('file://'):]
		
		parsedURL = urlparse.urlparse(location)
		
		if parsedURL.scheme not in ['', 'http', 'https']:
			optionParser.error('Item was not a format that this tool supports: ' + location)
		
		if parsedURL.scheme is '' and location[-1] == '/':
			location = location[:-1]
		
		thisOutputLocation = None
		if options.outputFolder is not None and parsedURL.scheme in ['http', 'https']:
			thisOutputLocation = options.outputFolder
			
		progressReporter = None
		if options.reportProgress is True:
			
			if parsedURL.scheme in ['http', 'https']:
				progressReporter = statusHandler(taskMessage=os.path.basename(parsedURL.path) + " ")
					
			else:
				progressReporter = statusHandler(taskMessage=os.path.basename(location) + " ")
			
		data = checksum(location, checksumType=options.checksumAlgorithm, progressReporter=progressReporter, outputFolder=thisOutputLocation, checksumInFileName=options.checksumInFileName)
		
		dataLine = ""
		normalizedPath = pathHelpers.normalizePath(location)
		
		# in the standardCacheFolder
		if parsedURL.scheme is '' and pathHelpers.pathInsideFolder(location, commonConfiguration.standardCacheFolder) and and hasattr(os.path, 'relpath'): # relpath is python 2.6
			dataLine = "\t".join(["", os.path.splitext(data['name'])[0], os.path.relpath(normalizedPath, commonConfiguration.standardCacheFolder), data['checksumType'] + ":" + data['checksum']])
		
		# in the standardUserItemsFolder
		if parsedURL.scheme is '' and pathHelpers.pathInsideFolder(location, commonConfiguration.standardUserItemsFolder) and and hasattr(os.path, 'relpath'): # relpath is python 2.6
			dataLine = "\t".join(["", os.path.splitext(data['name'])[0], os.path.relpath(normalizedPath, commonConfiguration.standardUserItemsFolder), data['checksumType'] + ":" + data['checksum']])
			
		else:
			dataLine = "\t".join(["", os.path.splitext(data['name'])[0], location, data['checksumType'] + ":" + data['checksum']])
		
		if progressReporter is not None:
			progressReporter.update(taskMessage=dataLine)
			progressReporter.finishLine()
		else:
			print("\t" + dataLine)
	
	sys.exit(0)
