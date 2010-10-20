#!/usr/bin/env python

import sys, os, time

#import threading

import Resources.commonConfiguration	as commonConfiguration
import Resources.displayTools			as displayTools
import Resources.volumeTools			as volumeTools
from Resources.containerController		import containerController
from Resources.managedSubprocess		import managedSubprocess

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
	
	chosenMount			= None
	
	if len(args) == 0:
		
		possibleVolumes = []
		
		# get a list of avalible installer disks
		for thisMountPoint in volumeTools.getMountedVolumes():
						
			try:
				thisVolume = containerController.newItemForPath(thisMountPoint)
			except Exception, error:
				continue
			
			if not thisVolume.isContainerType('volume'):
				continue
			
			macOSInformation = thisVolume.getMacOSInformation()
			if macOSInformation is None or macOSInformation['macOSInstallerDisc'] is not True:
				continue
			
			possibleVolumes.append(thisVolume)
		
		if len(possibleVolumes) == 0:
			optionParser.error('Error: There were no possible disks to image')
		
		elif len(possibleVolumes) == 1 and options.automaticRun == True:
			chosenMount = possibleVolumes[0]
		
		elif len(possibleVolumes) == 1:
			chosenMount = possibleVolumes[0]
			
			choice = raw_input('Only one mount point found: "%s" (%s) - %s %s (%s). Create image? (Y/N):' % (chosenMount.getMountPoint(), chosenMount.volumeType, chosenMount.getMacOSInformation()['macOSType'], chosenMount.getMacOSInformation()['macOSVersion'], chosenMount.getMacOSInformation()['macOSBuild']))
			if choice.lower() not in ['y', 'yes']:
				print("Canceling")
				sys.exit()
			
		elif options.automaticRun == True:
			optionParser.error('There was more than one avalible disk in an automatic run. Can only run in automatic mode when there is only one option.')
		
		else:
			print('The following mounts are avalible: ')
			i = 1
			for thisVolume in possibleVolumes:
				print('	%-4.4s"%s" (%s) - %s %s (%s)' % (str(i) + ")", thisVolume.getWorkingPath(), thisVolume.volumeType, thisVolume.getMacOSInformation()['macOSType'], thisVolume.getMacOSInformation()['macOSVersion'], thisVolume.getMacOSInformation()['macOSBuild']))
				i += 1
			choice = raw_input('Please select a volume by typeing in the number that precedes it: ')
			try:
				choice = int(choice)
			except:
				sys.stderr.write('Error: Input "%s" is not an integer\n' % choice)
				sys.exit(13)
			if choice > len(possibleDiscsInfo) or choice <= 0:
				sys.stderr.write('Error: Input "%s" was not a valid option\n' % choice)
				sys.exit(14)
			
			chosenMount = possibleVolumes[choice - 1]
	
	elif len(args) == 1:
		# user has supplied the mount point to use
		try:
			chosenMount = containerController.newItemForPath(args[0])
		except:
			optionParser.error('The path "%s" is not valid' % args[0])
		
		if not chosenMount.isContainerType('volume') or chosenMount.getMacOSInformation()['macOSType'] is None:
			optionParser.error('The path "%s" is not an installer disk' % args[0])
	
	else:
		optionParser.error('Can only process a single disk at a time')
	
	chosenFileName = options.outputFileName
	if chosenFileName is None and options.legacyMode is False:
		chosenFileName = "%s %s %s.dmg" % (chosenMount.getMacOSInformation()['macOSType'], chosenMount.getMacOSInformation()['macOSVersion'], chosenMount.getMacOSInformation()['macOSBuild'])
	elif options.legacyMode is True:
		chosenFileName = "Mac OS X Install DVD.dmg"
	
	# append .dmg if it is not already there
	if not os.path.splitext(chosenFileName)[1].lower() == ".dmg":
		chosenFileName = chosenFileName + ".dmg"
	
	# Search for an image that already has this OS Build
	outputFolder = options.outputFolder
	if outputFolder is None and options.legacyMode is False:
		outputFolder = commonConfiguration.standardOSDiscFolder
	elif options.legacyMode == True:
		outputFolder = commonConfiguration.legacyOSDiscFolder
	
	if not os.path.isdir(outputFolder):
		optionParser.error('The chosen output folder does not exist or is not a folder: %s' % outputFolder)
	
	targetPath = os.path.join(outputFolder, chosenFileName)
	
	if os.path.exists(targetPath):
		
		# ToDo: mount this file and make sure it looks right
		
		if options.overwriteExisting is False and options.automaticRun is True:
			sys.stderr.write('Error: Automatic mode was enabled, but a file already exists for this OS build and file overwiting (-o) is not enabled:\n%s\n' % targetPath)
			sys.exit(1)
		
		elif options.overwriteExisting is False:
			choice = raw_input('File already exists: %s\nOverwrite this file? (Y/N):' % targetPath)
			if not choice.lower() in ['y', 'yes']:
				print("Canceling")
				sys.exit()
				
	# Note: at this point it is all-right to overwrite the file if it exists
	
	if options.automaticRun is False:
		choice = raw_input('Ready to produce "%s" from the volume "%s".\n\tContinue? (Y/N):' % (chosenFileName, chosenMount.getWorkingPath()))
		if not choice.lower() in ['y', 'yes']:
			print("Canceling")
			sys.exit()
	
	myStatusHandler = displayTools.statusHandler(taskMessage='Creating image from disc at: %s' % chosenMount.getWorkingPath())
	
	diskFormat = 'UDZO' # default to zlib
	if options.compressionType == "bzip2":
		diskFormat = 'UDBZ'
	
	diskutilArguments = ['/usr/bin/hdiutil', 'create', '-ov', '-srcowners', 'on', '-srcfolder', chosenMount.getWorkingPath(), '-format', diskFormat]
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