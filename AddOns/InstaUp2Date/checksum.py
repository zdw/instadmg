#!/usr/bin/env python

import os, sys, optparse, hashlib
from Resources.checksum import checksum
	
#------------------------------MAIN------------------------------

if __name__ == "__main__":
	
	optionParser = optparse.OptionParser()
	
	if hasattr(hashlib, 'algorithms'):
		optionParser.add_option("-a", "--checksum-algorithm", default="sha1", action="store", dest="checksumAlgorithm", choices=hashlib.algorithms, help="Disable progress notifications") # Python 2.7 and above
	else:
		optionParser.add_option("-a", "--checksum-algorithm", default="sha1", action="store", dest="checksumAlgorithm", help="Disable progress notifications")
	
	optionParser.add_option("-d", "--disable-progress", default=True, action="store_false", dest="reportCheckSum", help="Disable progress notifications")
	optionParser.add_option("-s", "--chunk-size", default=None, action="store", type="int", dest="chunkSize", help="The size in bytes to use as a buffer")
	optionParser.add_option("-t", "--output-folder", default=None, action="store", dest="outputFolder", type="string", help="Write a copy of the file/folder to this folder")
	(options, args) = optionParser.parse_args()
	
	# confirm that hashlib supports the hash type:
	try:
		hashlib.new(options.checksumAlgorithm)
	except ValueError:
		optionParser.error("Hash type: %s is not supported by hashlib" % options.checksumAlgorithm)
	
	# confirm that the output folder exists
	if options.outputFolder is not None and not os.path.isdir(options.outputFolder):
		optionParser.error('The output folder given does not exist, or is not a folder: ' + str(options.outputFolder))
	# and is writable by this user
	
	for location in args:
		data = checksum(
			location,
			checksumType=options.checksumAlgorithm,
			progressReporter=options.reportCheckSum
		)
		print "\t".join(["", os.path.splitext(data['name'])[0], location, data['checksumType'] + ":" + data['checksum']])
	
	sys.exit()
