#!/usr/bin/python

import os, stat, subprocess, tempfile

class managedSubprocess(subprocess.Popen):
	'''Subprocess wrapper'''
	
	_plistObject		= None
	
	stdoutLen			= None
	stderrLen			= None
	
	def __init__(self, command, processAsPlist=False, **kwargs):
		
		if 'stdout' in kwargs or 'stderr' in kwargs:
			self._child_created = False # make the __del__ of out superclass happy
			raise NotImplementedError(self.__class__.__name__ + ' does not yet support stdout or stderr settings')
		
		stdout = tempfile.TemporaryFile()
		stderr = tempfile.TemporaryFile()
		
		# Note: this always absorbs stdout and stderr in case there is a problem
		super(self.__class__, self).__init__(command, stdout=stdout.fileno(), stderr=stderr.fileno(), **kwargs)
		
		self.wait()
		
		self.stdoutLen = os.fstat(stdout.fileno()).st_size
		self.stderrLen = os.fstat(stderr.fileno()).st_size
		stderr.seek(0) # the fstats seeks to the end
		stdout.seek(0)
		
		if self.returncode != 0:
			errorString = 'The process "%s" failed with error: %s' % (' '.join(command), self.returncode)
			
			# add the stdout, if any
			if self.stdoutLen > 0:
				errorString += '\nStdout: ' + stdout.read().strip()
				stderr.seek(0)
			
			# add the stderr, if any
			if self.stderrLen > 0:
				errorString += '\nStderr: ' + stderr.read().strip()
				stderr.seek(0)
			
			raise RuntimeError(errorString)
		
		if processAsPlist is True:
			output = stdout.read()
			import Foundation
			
			plistNSData = Foundation.NSString.stringWithString_(output).dataUsingEncoding_(Foundation.NSUTF8StringEncoding)
			plistData, format, error = Foundation.NSPropertyListSerialization.propertyListFromData_mutabilityOption_format_errorDescription_(plistNSData, Foundation.NSPropertyListMutableContainersAndLeaves, None, None)
			
			if error is not None or plistData is None:
				raise RuntimeError('Unable to convert the "%s" output into a plist, got error: %s\nOutput was:\n%s\n' % (' '.join(command), error, output))
			
			self._plistObject = plistData # ToDo: evaluate converting this all to python objects
			return
		
		self.stdout = stdout
		self.stderr = stderr
		
	def getPlistObject(self):
		if self._plistObject is None:
			raise RuntimeError('This %s object does not have a deserialized plist to return')
		
		return self._plistObject
