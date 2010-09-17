#!/usr/bin/python

__version__ = "$Revision$".split()[1]

import os, sys

def normalizePath(inputPath, followSymlink=False):
	
	if inputPath is None:
		return None
	
	inputPath = str(inputPath)
	
	if inputPath == "/":
		return "/"
	
	# expand tildes
	inputPath = os.path.expanduser(inputPath)
	
	# remove trailing slashes
	while inputPath.endswith(os.sep) and not inputPath.endswith('\\' + os.sep):
		inputPath = inputPath[:-1]
	
	inputPath = os.path.expanduser(inputPath)
	
	if followSymlink is True:
		return os.path.realpath(inputPath)
	else:
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


if __name__ == '__main__':
	import optparse
	
	# -- parse the input
	
	def print_version(option, opt, value, optionsParser):
		optionsParser.print_version()
		sys.exit(0)
	
	optionsParser = optparse.OptionParser("%prog -n/--normalize-path [-f/--follow-symlinks] target_path | -p/--path-inside-folder target_path test_folder", version="%%prog %s" % __version__)
	optionsParser.remove_option('--version')
	optionsParser.add_option("-v", "--version", action="callback", callback=print_version, help="Print the version number and quit")
	
	optionsParser.add_option("-n", "--normalize-path", action="store_const", const='normalizePath', dest='mode', help="Use the normalize path mode")
	optionsParser.add_option("-f", "--follow-symlinks", action="store_true", dest='followSymlinks', default=False, help="Follow symlinks in the normalize path mode")
	
	optionsParser.add_option("-p", "--path-inside-folder", action="store_const", const='pathInsideFolder', dest='mode', help="Use the path inside folder mode")
	
	optionsParser.add_option("", "--supress-return", action="store_const", const='', dest='lineEnding', default='\n', help="Don't end the line with a return, for bash scripts")
	
	options, arguments = optionsParser.parse_args()
	
	# -- police options
	
	if options.mode is None:
		optionsParser.error('One of either the -n/--normalize-path or the -p/--path-inside-folder options must be selected.')
	
	elif options.mode == 'normalizePath':
		if len(arguments) != 1:
			optionsParser.error('When using the -n/--normalize-path option a single (and only a single) path must be provided.')
		
		targetPath = arguments[0]
		
		if not os.path.exists(targetPath):
			optionsParser.error('The targetPath supplied does not exist: ' + targetPath)
		
		sys.stdout.write(normalizePath(targetPath, followSymlink=options.followSymlinks) + options.lineEnding)
	
	elif options.mode == 'pathInsideFolder':
		if len(arguments) != 2:
			optionsParser.error('When using the -p/--path-inside-folder option exactly two options (the targetPath and the testFolder) must be provided.')
		
		targetPath = arguments[0]
		testFolder = arguments[1]
		
		if not os.path.isdir(testFolder):
			optionsParser.error('The test_folder must be a folder, but the suplpied path was not one: ' + testFolder)
		
		sys.stdout.write(str(pathInsideFolder(targetPath, testFolder)) + options.lineEnding)
	
	else:
		optionsParser.error('Unrecognized input.')
		
		