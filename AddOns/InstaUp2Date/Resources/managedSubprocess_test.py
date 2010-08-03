#!/usr/bin/python

import os, sys, unittest, subprocess

from managedSubprocess import managedSubprocess
from tempFolderManager import tempFolderManager

class simpleTests(unittest.TestCase):
	'''Some simple tests'''
	
	def test_stdout(self):
		'''Make sure that stdout is being properly returned'''
		
		# setup a folder to then test on (so things are predictable)
		outerFolder = tempFolderManager.getNewTempFolder()
		testFile = open(os.path.join(outerFolder, "testItem"), "w")
		testFile.close()
		
		command = ["/bin/ls", outerFolder]
		process = managedSubprocess(command)
		
		self.assertTrue(hasattr(process, 'stdout') and process.stdout is not None, 'managedSubprocess did not have a stdout item when it should have')
		result = process.stdout.read()
		expectedResult = "testItem\n"
		self.assertTrue(isinstance(process.stdoutLen, int), 'managedSubprocess should have had an integer value for stdoutLen, rather it had: ' + str(process.stdoutLen))
		self.assertEqual(len(expectedResult), process.stdoutLen, 'managedSubprocess should have had a length of %i for stdoutLen, rather it had a length of %i: %s' % (len(expectedResult), process.stdoutLen, result))
		self.assertEqual(result, expectedResult, 'managedSubprocess did not return the correct stdout for process "%s". Got "%s" rather than "%s"' % (" ".join(command), result, expectedResult))
	
	def test_stderr(self):
		'''Make sure that stderr is being properly returned'''
		
		# setup a folder to then test on (so things are predictable)
		outerFolder = tempFolderManager.getNewTempFolder()
		testFile = open(os.path.join(outerFolder, "testItem"), "w")
		testFile.close()
		
		command = ["/bin/ls " + outerFolder + " 1>&2"]
		process = managedSubprocess(command, shell=True)
		
		self.assertTrue(hasattr(process, 'stderr') and process.stderr is not None, 'managedSubprocess did not have a stderr item when it should have')
		result = process.stderr.read()
		expectedResult = "testItem\n"
		self.assertTrue(isinstance(process.stderrLen, int), 'managedSubprocess should have had an integer value for stdoutLen, rather it had: ' + str(process.stderrLen))
		self.assertEqual(len(expectedResult), process.stderrLen, 'managedSubprocess should have had a length of %i for stdoutLen, rather it had a length of %i: %s' % (len(expectedResult), process.stderrLen, result))
		self.assertEqual(result, expectedResult, 'managedSubprocess did not return the correct stderr for process "%s". Got "%s" rather than "%s"' % (" ".join(command), result, expectedResult))
	
	def test_processAsPlist(self):
		'''Make sure that correct plists get returned properly'''
		
		command = ['/usr/bin/hdiutil', 'info', '-plist']
		process = managedSubprocess(command, processAsPlist=True)
		
		self.assertTrue(not hasattr(process, 'stdout') or process.stdout is None, 'When called with processAsPlist=True managedSubprocess should not have a useable stdout attribute')
		self.assertTrue(not hasattr(process, 'stderr') or process.stderr is None, 'When called with processAsPlist=True managedSubprocess should not have a useable stderr attribute')
		
		plistData = process.getPlistObject()
		self.assertTrue(hasattr(plistData, 'has_key') and plistData.has_key('images'), 'The plist data returned form the command "%s" was not a hash with a "images" key as expected' % " ".join(command))
		

class simpleTests_negative(unittest.TestCase):
	'''Test to make sure things fail when they should'''
	
	def test_failsOnStderrStdout(self):
		'''Untill I work out how stderr and stdout should work, fail when they are used'''
		
		command = ["/bin/ls"]
		self.assertRaises(NotImplementedError, managedSubprocess, command, stderr=subprocess.PIPE)
		self.assertRaises(NotImplementedError, managedSubprocess, command, stdout=subprocess.PIPE)
	
	def test_failsWhenMissingCommand(self):
		'''Make sure that we get through on the underlying failure when command is missing'''
		
		self.assertRaises(TypeError, managedSubprocess, None)
	
	def test_missingCommand(self):
		'''A call to an executable that does not exist should throw a OSError'''
		
		self.assertRaises(OSError, managedSubprocess, ['/this-should-not-exist'])
	
	def test_failingCommand(self):
		'''Calling a command that results in a failing return code should throw a RuntimeError'''
		
		command = ['/bin/ls', '/this-should-not-exist']
		self.assertRaises(RuntimeError, managedSubprocess, command)
		
		# again, but this time catch the output
		try:
			managedSubprocess(command)
		except RuntimeError, e:
			expectedString = 'The process "/bin/ls /this-should-not-exist" failed with error: 1\nStderr: ls: /this-should-not-exist: No such file or directory'
			self.assertEqual(str(e), expectedString, 'Calling a failing command (%s) and expected:\n%s\nBut got:\n%s' % (" ".join(command), expectedString, str(e)))
	
	def test_badPlist(self):
		'''Calling %s with processAsPlist=True on a command that does not give plist data should fail''' % self.__class__.__name__
		
		command = ['/bin/ls']
		self.assertRaises(RuntimeError, managedSubprocess, command, processAsPlist=True)
	
	def test_getPlistObjectWithoutAPlist(self):
		'''Confirm that a RuntimeError is called if getPlistObject is called on a non-plist object'''
		
		command = ['/bin/ls']
		process = managedSubprocess(command)
		self.assertRaises(RuntimeError, process.getPlistObject)
		

if __name__ == "__main__":
	unittest.main()