#!/usr/bin/python

import subprocess, time

import Resources.pathHelpers			as pathHelpers
import Resources.commonConfiguration	as commonConfiguration
import Resources.containerController	as containerController

from Resources.tempFolderManager		import tempFolderManager
from Resources.managedSubprocess		import managedSubprocess
from Resources.displayTools				import secondsToReadableTime, bytesToRedableSize

if __name__ == "__main__":
	import optparse, sys, os, re, tempfile, shutil
	
	if os.geteuid() != 0:
		sys.stderr.write("Error: in order to restore volumes this command must be run with root permissions (sudo works)\n")
		sys.exit(1)
	
	optionParser = optparse.OptionParser(usage="usage: %prog --restore-volume=VOLUME [options] [test1.dmg [test2.dmg [...]]]")
	optionParser.add_option("-r", "--restore-volume", dest="restoreVolume", type="string", action="store", default=None, help="Restore over this volume. WARNING: all data on this volume will be lost!", metavar="Volume")
	(options, arguments) = optionParser.parse_args()
	
	restorePoint = None
	restorePointName = None
	restorePointSizeInBytes = None
		
	if options.restoreVolume == None:
		optionParser.error('A target volume to restore to is required.')
	
	# check the volume that we are going to restore to, and make sure we have the /dev entry for it
	else:
		diskutilCommand = ["/usr/sbin/diskutil", "info", "-plist", options.restoreVolume]
		try:
			process = managedSubprocess(diskutilCommand, processAsPlist=True)
			diskutilOutput = process.getPlistObject()
		except RuntimeError:
			optionParser.error('Unable to find the restore target volume: ' + str(options.restoreVolume))
				
		if diskutilOutput['DeviceIdentifier'] == diskutilOutput['ParentWholeDisk']:
			optionParser.error('The restore target volume must be a partition, not a whole disk.')
		
		if diskutilOutput['MountPoint'] == '/':
			optionParser.error('The root volume can not be the restore target volume.')
		
		if diskutilOutput['WritableMedia'] is not True:
			optionParser.error('The restore target volume must be on writeable media.')
		
		if "VolumeName" in diskutilOutput:
			restorePointName = diskutilOutput["VolumeName"]
		
		restorePointSizeInBytes = diskutilOutput["TotalSize"]
		restorePoint = diskutilOutput['DeviceNode']
	
	if len(arguments) == 0:
		arguments.append(os.path.join(pathToInstaDMGFolder, "OutputFiles"))
	
	sourceFiles = []
	
	# check the arguments as valid sources
	for thisArgument in arguments:
				
		if os.path.isdir(thisArgument): # see if it is a folder of dmg's
			# Possible ToDo: recurse into directories
			foundFiles = []
			for thisFile in os.listdir(thisArgument):
				
				thisItem = containerController.newItemForPath(os.path.join(thisArgument, thisFile))
				
				if thisItem.isContainerType('dmg'):
					sourceFiles.append(thisItem)
				else:
					optionParser.error("A given file is not a valid dmg: %s\n" % resolvedPath)
		
		elif os.path.isfile(thisArgument):
			
			thisItem = containerController.newItemForPath(thisArgument)
			if thisItem.isContainerType('dmg'):
				sourceFiles.append(thisItem)
			else:
				optionParser.error("A given file is not a valid dmg: %s\n" % resolvedPath)
		
		else:
			optionParser.error("Argument given was neither a dmg file, nor a folder of dmgs: %s\n" % thisArgument)
	
	if not len(sourceFiles) > 0:
		optionParser.error("There were no valid source files")
	
	# confirm that all of the images are restoreable onto the target volume
	for thisImage in sourceFiles:
		diskutilCommand = ["/usr/bin/hdiutil", "imageinfo", "-plist", thisImage.getStoragePath()]
		process = managedSubprocess(diskutilCommand, processAsPlist=True)
		plistData = process.getPlistObject()
		
		if int(plistData["Size Information"]["Total Non-Empty Bytes"]) > restorePointSizeInBytes:
			sys.stderr.write('Error: image %s takes more space than is avalible on the target volume (%s vs. %s)\n' % (thisImage, bytesToRedableSize(plistData["Size Information"]["Total Non-Empty Bytes"]), bytesToRedableSize(restorePointSizeInBytes)))
			sys.exit(1)
	
	# tell the user what we will be processing	
	pluralEnding = ""
	if len(sourceFiles) > 1:
		pluralEnding = "s"
	targetVolumeDisplay = restorePoint
	if restorePointName != None:
		targetVolumeDisplay = "'%s' (%s)" % (restorePointName, restorePoint)
	
	listOfDMGFiles = []
	for thisDMG in sourceFiles:
		listOfDMGFiles.append(thisDMG.getStoragePath())
	
	print("Profiling will be done by restoring to %s using the following dmg%s:\n\t%s\n" % (targetVolumeDisplay, pluralEnding, "\n\t".join(listOfDMGFiles)))
	
	# warn the user
	choice = raw_input('WARNING: All data on the volume %s will be ERASED! Are you sure you want to continue? (Y/N):' % targetVolumeDisplay)
	if not( choice.lower() == "y" or choice.lower() == "yes" ):
		print("Canceling")
		sys.exit()
	
	print("\nTesting will now start. This will probably take many hours.\n\n==================Start testing data==================")
	
	# grab the relevent data from system_profiler
	systemProfilerCommand = ["/usr/sbin/system_profiler", "-xml", "SPHardwareDataType"]
	process = managedSubprocess(systemProfilerCommand, processAsPlist=True)
	plistData = process.getPlistObject()
	
	print("Computer Type:\t%(machineName)s (%(machineModel)s)" % {"machineName":plistData[0]["_items"][0]["machine_name"], "machineModel":plistData[0]["_items"][0]["machine_model"]})
	print("Processor:\t%(processorSpeed)s %(processorType)s" % {"processorSpeed":plistData[0]["_items"][0]["current_processor_speed"], "processorType":plistData[0]["_items"][0]["cpu_type"]})
	print("Memory:\t\t%(memorySize)s" % {"memorySize":plistData[0]["_items"][0]["physical_memory"]})
	
	
	# ToDo: print out the information about the disk the restore volume is on
		
	# create a tempfile location for asr to write onto
	
	# create the tempMountPoint to mount the image to
	tempMountPoint = tempFolderManager.getNewTempFolder(prefix="sourceMountPoint.")
	
	# create a tempfile for hdiutil to write onto
	hdiutilOutfilePath = tempFolderManager.getNewTempFile(prefix="outputFile.", suffix=".dmg")
	
	# process things
	for thisDMG in sourceFiles:
		
		thisDMGWithShadow = thisDMG.getVersionWithShadowFile(thisDMG.getStoragePath(), shadowFile=True)
		
		# the source options to use
		sourceOptions = [
			{"message":"Creating image from volume", "command":["/usr/bin/hdiutil", "create", "-nocrossdev", "-ov", "-srcfolder", tempMountPoint, hdiutilOutfilePath], "mountImage":True},
			{"message":"Converting dmg image directly", "command":["/usr/bin/hdiutil", "convert", thisDMG.getStoragePath(), "-o", hdiutilOutfilePath, "-ov"]}
		]
		
		# output options to use		
		outputOptions = [
			{"message":" using no compression ", "command":["-format", "UDRO"]}, # read-only (uncompressed) image
			{"message":" using ADC compression ", "command":["-format", "UDCO"]}, # ADC-compressed image
			{"message":" using zlib compression level 1 (fast) ", "command":["-format", "UDZO", "-imagekey", "zlib-level=1"]}, # zlib-compressed image - fast
			{"message":" using zlib compression level 6 (default) ", "command":["-format", "UDZO", "-imagekey", "zlib-level=6"]}, # zlib-compressed image - default
			{"message":" using zlib compression level 9 (smallest) ", "command":["-format", "UDZO", "-imagekey", "zlib-level=9"]}, # zlib-compressed image - fast
			{"message":" using bzip2 compression ", "command":["-format", "UDBZ"]} # bzip2-compressed image
		]
		
		# asr scanning options
		asrImagescanOptions = [
			{"message":"without file checksums ", "command":[]},
			{"message":"with file checksums ", "command":["--filechecksum"]}
			# ToDo: play with buffers
		]
		
		# ToDo: play with buffers 
		
		for thisSourceOption in sourceOptions:
			print("\n" + thisSourceOption["message"] + "\n------------------")
			
			if "mountImage" in thisSourceOption and thisSourceOption["mountImage"] == True:
				
				print('	Mounting: %s at %s' % (thisDMG.getStoragePath(), tempMountPoint))
				if thisDMGWithShadow.getShadowFile() is not None and os.path.exists(thisDMGWithShadow.getShadowFile()):
					os.unlink(thisDMGWithShadow.getShadowFile())
				thisDMGWithShadow.mount(mountPoint=tempMountPoint)
				
				# fsck the file to rebuild the file catalog
				#command = ['/sbin/fsck_hfs', '-r', tempMountPoint]
				#print("\tfsck'ing command: " + " ".join(command))
				#process = subprocess.Popen(command)
				#if process.wait() != 0:
				#	raise Exception('Processes: %s\nReturned: %i with output:\n%s\nAnd error: %s' % (' '.join(command), process.returncode, process.stdout.read(), process.stderr.read()))	
			
			for thisOutputOption in outputOptions:
				
				# make sure that there is something at the output location
				open(hdiutilOutfilePath, "w").close()
				
				command = thisSourceOption["command"] + thisOutputOption["command"]
				print("\t" + thisSourceOption["message"] + thisOutputOption["message"] + ": " + " ".join(command))
				
				startTime = time.time()
				managedSubprocess(command)
				print("\t\tConversion took: %s\n" % secondsToReadableTime(time.time() - startTime))
				
				asrTargetFile = None
				
				if thisOutputOption == outputOptions[len(outputOptions) - 1]:
					# since this is the last one we can just use the raw file
					asrTargetFile = hdiutilOutfilePath
					
				else:
					# because there are others that want to use this file, we need to make a copy
					
					asrTargetFile = tempFolderManager.getNewTempFile(prefix="targetFile.", suffix=".dmg")
					print('\t\tCopying: %s to %s' % (hdiutilOutfilePath, asrTargetFile))
					shutil.copyfile(hdiutilOutfilePath, asrTargetFile)
				
				# asr scan the image
				for scanOption in asrImagescanOptions:
				
					# copy the image if this is not the last item
					asrInnerTargetFile = None
					if scanOption == asrImagescanOptions[len(asrImagescanOptions) - 1]:
						# if it is the last round in this one, no need to copy things
						asrInnerTargetFile = asrTargetFile
					else:
						asrInnerTargetFile = tempFolderManager.getNewTempFile(prefix="innerTargetFile.", suffix=".dmg")
						shutil.copyfile(asrTargetFile, asrInnerTargetFile)
					
					command = ['/usr/sbin/asr', 'imagescan'] + scanOption['command'] + ['--source', asrInnerTargetFile]
					print('\t\tASR scanning image %s: %s' % (scanOption['message'], ' '.join(command)))
					
					startTime = time.time()
					process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
					if process.wait() != 0:
						print('\t\t\tASR scan failed, trying with the --allowfragmentedcatalog flag')
						command.append('--allowfragmentedcatalog')
						startTime = time.time()
						process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
						
						if process.wait() != 0:
							raise Exception('Processes: %s\nReturned: %i with output:\n%s\nAnd error: %s' % (' '.join(command), process.returncode, process.stdout.read(), process.stderr.read()))
					
					print("\t\t\tScan took: %s\n" % secondsToReadableTime(time.time() - startTime))
					
					# restore the image
					# ToDo: play with asr options more
					startTime = time.time()
					command = ['/usr/sbin/asr', 'restore', '--erase', '--noprompt', '--source', asrInnerTargetFile, '--target', restorePoint]
					print('\t\t\tASR restoring image: %s' % ' '.join(command))
					process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
					if process.wait() != 0:
						print('\t\t\t\tASR restore failed, trying with the --allowfragmentedcatalog flag')
						command.append('--allowfragmentedcatalog')
						startTime = time.time()
						process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
						
						if process.wait() != 0:
							raise Exception('Processes: %s\nReturned: %i with output:\n%s\nAnd error: %s' % (' '.join(command), process.returncode, process.stdout.read(), process.stderr.read()))
					print("\t\t\t\tRestore took: %s\n" % secondsToReadableTime(time.time() - startTime))
					
					# cleanup
					os.unlink(asrInnerTargetFile) # cleanup the innerTargetFile
					
				if os.path.exists(asrTargetFile):
					os.unlink(asrTargetFile) # cleanup the targetFile
			
			if "mountImage" in thisSourceOption and thisSourceOption["mountImage"] == True:
				thisDMGWithShadow.unmount()
				
	sys.exit(0)


