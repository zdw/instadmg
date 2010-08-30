#!/usr/bin/env python

import sys, os, time

#import threading

import Resources.commonConfiguration	as commonConfiguration
import Resources.displayTools			as displayTools
from Resources.managedSubprocess		import managedSubprocess
from Resources.volumeManager			import volumeManager

#class puppetStringsMonitor(threading.Thread):
#	inputItem	= None
#	process		= None
#	
#	daemon		= True # automatically make these daemon threads
#	
#	def __init__(self, process):
#		threading.Thread.__init__(self)
#		self.inputItem	= inputItem
#		self.process	= inputItem.stdout
#		
#		self.start()
#	
#	def __enter__(self):
#		return self
#			
#	def run(self):
#		
#		lastReport = 0;
#		
#		while self.process.poll() == None:
#			thisLine = self.inputItem.readline()
#			if thisLine:
#				sys.stdout.write(thisLine)
#
#		for thisLine in self.inputItem:			
#			fixed = unicodedata.normalize('NFKD', unicode(thisLine.strip(), "utf-8")).encode('ASCII', 'replace')
#			if fixed:
#				logging.log(self.logLevel, thisLine)
#	
#	def __exit__(self, exc_type, exc_value, traceback):
#		pass


def main():
	import optparse
	
	startTime = time.time()
	
	compressionChoices = ['zlib', 'bzip2']
	
	optionParser = optparse.OptionParser()
	optionParser.add_option("-a", "--automatic", default=False, action="store_true", dest="automaticRun", help="Run automaically, will fail if there are any questions")
	
	# ToDo: convert these to actions vaildating the input
	optionParser.add_option("-c", "--compression-type", default="zlib", choices=compressionChoices, action="store", dest="compressionType", help="Choose the compression type from: %s" % ", ".join(compressionChoices))
	optionParser.add_option("-f", "--output-folder", default=None, action="store", dest="outputFolder", help="Override the output folder")
	optionParser.add_option("-l", "--legacy", default=False, action="store_true", dest="legacyMode", help="Use legacy name and location")
	optionParser.add_option("-n", "--output-name", default=None, action="store", dest="outputFileName", help="Override the output name")
	optionParser.add_option("-o", "--overwrite-existing-file", default=False, action="store_true", dest="overwriteExisting", help="Overwite existing output file without asking")	
	(options, args) = optionParser.parse_args()
	
	chosenMountPoint	= None
	chosenOSVersion		= None
	chosenOSBuild		= None
	
	if len(args) == 0:
		
		mountPoints = {}
		# remove the non-installer options
		for thisMountPoint in volumeManager.getMountedVolumes():
			try:
				installerType = volumeManager.getInstallerDiskType(thisMountPoint)
				mountPoints[thisMountPoint] = installerType
			except ValueError:
				continue
		
		if len(mountPoints) == 0:
			sys.stderr.write('Error: There were no possible disks to image\n')
			sys.exit(4)
		
		elif len(mountPoints) == 1 and options.automaticRun == True:
			chosenMountPoint = mountPoints[mountPoints.keys()[0]]
		
		elif len(mountPoints) == 1:
			choice = raw_input('Only one mount point found: "%s". Create image? (Y/N):' % mountPoints.keys()[0])
			if choice.lower() == "y" or choice.lower() == "yes":
				chosenMountPoint = mountPoints.keys()[0]
			else:
				print("Canceling")
				sys.exit()
			
		elif options.automaticRun == True:
			sys.stderr.write('Error: There was more than one avalible disk in an automatic run. Can only run in automatic mode when there is only one option.\n')
			sys.exit(18)
		
		else:
			print('The following mounts are avalible: ')
			i = 1
			mountPointsList = mountPoints.keys()
			for thisMountPoint in mountPointsList:
				(version, build) = volumeManager.getMacOSVersionAndBuildOfVolume(thisMountPoint)
				print('  %s%s %s (%s)\t%s' % ((str(i) + ")").ljust(4, " "), mountPoints[thisMountPoint], version, build, thisMountPoint))
				i += 1
			choice = raw_input('Please select a volume by typeing in the number that precedes it: ')
			try:
				choice = int(choice)
			except:
				sys.stderr.write('Error: Input "%s" is not an integer\n' % choice)
				sys.exit(13)
			if choice > len(mountPoints) or choice <= 0:
				sys.stderr.write('Error: Input "%s" was not a valid option\n' % choice)
				sys.exit(14)
			
			chosenMountPoint = mountPointsList[choice - 1]
	
	elif len(args) == 1:
		# user has supplied the mount point to use
		inputPath = args[0]
		
		if not os.path.ismount(inputPath):
			sys.stderr.write('Error: The path "%s" is not a mount point\n' % inputPath)
			sys.exit(15)
		
		if volumeManager.getInstallerDiskType(inputPath) == None:
			sys.stderr.write('Error: The path "%s" is not an installer disk\n' % inputPath)
			sys.exit(16)
		
		chosenMountPoint = inputPath
	
	else:
		sys.stderr.write('Error: Can only process a single disk at a time\n' % choice)
		sys.exit(17)
	
	chosenOSVersion, chosenOSBuild = volumeManager.getMacOSVersionAndBuildOfVolume(chosenMountPoint)
	chosenOSType = volumeManager.getInstallerDiskType(chosenMountPoint)
	
	chosenFileName = options.outputFileName
	if chosenFileName == None and options.legacyMode == False:
		chosenFileName = "%s %s %s.dmg" % (chosenOSType, chosenOSVersion, chosenOSBuild)
	elif options.legacyMode == True:
		chosenFileName = "Mac OS X Install DVD.dmg"
	
	# append .dmg if it is not already there
	if not (os.path.splitext(chosenFileName)[1].lower() == ".dmg"):
		chosenFileName = chosenFileName + ".dmg"
	
	# Search for an image that already has this OS Build
	# ToDo: get the setup for this from a central place
	outputFolder = options.outputFolder
	if outputFolder == None and options.legacyMode == False:
		outputFolder = commonConfiguration.standardOSDiscFolder
	elif options.legacyMode == True:
		outputFolder = commonConfiguration.legacyOSDiscFolder
	
	if not os.path.isdir(outputFolder):
		sys.stderr.write('Error: The chosen output folder does not exist or is not a folder: %s\n' % outputFolder)
		sys.exit(20)
	
	targetPath = os.path.join(outputFolder, chosenFileName)
	
	if os.path.exists(targetPath):
		
		# ToDo: mount this file and make sure it looks right
		
		if options.overwriteExisting == False and options.automaticRun == True:
			sys.stderr.write('Error: Automatic mode was enabled, but a file already exists for this OS build and file overwiting (-o) is not enabled:\n%s\n' % targetPath)
			sys.exit(19)
		
		elif options.overwriteExisting == False:
			choice = raw_input('File already exists: %s\nOverwrite this file? (Y/N):' % targetPath)
			if not (choice.lower() == "y" or choice.lower() == "yes"):
				print("Canceling")
				sys.exit()
				
	# Note: at this point it is all-right to overwrite the file if it exists
	
	if options.automaticRun == False:
		choice = raw_input('Ready to produce "%s" from the volume "%s".\n\tContinue? (Y/N):' % (chosenFileName, chosenMountPoint))
		if not (choice.lower() == "y" or choice.lower() == "yes"):
			print("Canceling")
			sys.exit()
	
	myStatusHandler = displayTools.statusHandler(taskMessage='Creating image from disc at: %s' % chosenMountPoint)
	
	diskFormat = 'UDZO' # default to zlib
	if options.compressionType == "bzip2":
		diskFormat = 'UDBZ'
	
	diskutilArguments = ['/usr/bin/hdiutil', 'create', '-ov', '-srcowners', 'on', '-srcfolder', chosenMountPoint, '-format', diskFormat]
	if options.compressionType == "zlib":
		# go for more compression
		diskutilArguments.append('-imagekey')
		diskutilArguments.append('zlib-level=6')
	diskutilArguments.append(targetPath)
	diskutilProcess = managedSubprocess(diskutilArguments)
	
	myStatusHandler.update(taskMessage='Image "%s" created in %s' % (chosenFileName, displayTools.secondsToReadableTime(time.time() - startTime)))
	myStatusHandler.finishLine()
	sys.exit(0)

if __name__ == "__main__":
	main()