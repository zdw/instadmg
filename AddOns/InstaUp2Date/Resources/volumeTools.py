#!/usr/bin/python

import os, subprocess

import pathHelpers
from managedSubprocess	import managedSubprocess

def unmountVolume(targetPath):
	'''Unmount a volume or dmg mounted at the path given'''
	
	if not os.path.ismount(targetPath):
		raise ValueError('unmountVolume valled on a path that was not a mount point: ' + targetPath)
	
	targetPath = pathHelpers.normalizePath(targetPath)
	
	# check to see if this is a disk image
	isMountedDMG = False
	command = ['/usr/bin/hdiutil', 'info', '-plist']
	process = managedSubprocess(command, processAsPlist=True)
	plistData = process.getPlistObject()
	
	if not hasattr(plistData, 'has_key') or not plistData.has_key('images') or not hasattr(plistData['images'], '__iter__'):
		raise RuntimeError('The "%s" output does not have an "images" array as expected. Output was:\n%s' % (' '.join(command), output))
	
	for thisImage in plistData['images']:
	
		if not hasattr(thisImage, '__iter__') or not thisImage.has_key('system-entities') or not hasattr(thisImage['system-entities'], '__iter__'):
			raise RuntimeError('The "%s" output had an image entry that was not formed as expected. Output was:\n%s' % (' '.join(command), output))
		
		for thisEntry in thisImage['system-entities']:
			if thisEntry.has_key('mount-point') and os.path.samefile(thisEntry['mount-point'], targetPath):
				isMountedDMG = True
				break
		if isMountedDMG is True: break
	
	if isMountedDMG is True:
		# ToDo: log this
		command = ['/usr/bin/hdiutil', 'eject', targetPath]
		process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		
		if process.wait() != 0 and os.path.ismount(targetPath):
			# try again with a bit more force
			# ToDo: log this
			
			command = ['/usr/bin/hdiutil', 'eject', '-force', targetPath]
			managedSubprocess(command)
	
	else:
		# a non dmg mount point
		# ToDo: log this
		command = ['/usr/sbin/diskutil', 'unmount', targetPath]
		process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		
		if process.wait() != 0 and os.path.ismount(targetPath):
			# try again with a bit more force
			# ToDo: log this
			
			command = ['/usr/sbin/diskutil', 'unmount', 'force', targetPath]
			managedSubprocess(command)
