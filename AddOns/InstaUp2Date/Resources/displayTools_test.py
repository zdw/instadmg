#!/usr/bin/env python

import os, unittest, subprocess

from displayTools import statusHandler
from tempFolderManager import tempFolderManager

class test_statusHandler(unittest.TestCase):
	
	outputFile = None
	outputHandler = None
	
	def setUp(self):
		# create a file to write to
		self.outputFile = open(tempFolderManager.getNewTempFile(), "w")
		
		# setup an output handler to write to this file
		self.outputHandler = statusHandler(outputChannel=self.outputFile)
	
	def tearDown(self):
		# clean up
		outputFilePath = self.outputFile.name
		self.outputFile.close()
		self.outputFile = None
		
		tempFolderManager.cleanupItem(outputFilePath)
		
		self.outputHandler = None
	
	def getOuptputFileContents(self):
		'''Truncating the files make them unreadable, so this pulls a trick to read out the contents and resets the file'''
		
		# save the state so that we can re-setup it
		currentPosition = self.outputFile.tell()
		outputFilePath = self.outputFile.name
		
		# close the file, re-open it read-only, and get the contents
		self.outputFile.close()
		self.outputFile = open(outputFilePath, "r")
		currentFileContents = self.outputFile.read()
		self.outputFile.close()
		
		# re-open as write, write out the contents, and re-set the system
		self.outputFile = open(outputFilePath, "w")
		self.outputFile.write(currentFileContents)
		self.outputFile.seek(currentPosition, 0)
		self.outputHandler.outputChannel = self.outputFile
		
		return currentFileContents
	
	def compareOutput(self, errorPrefix, staticOuput=None):
		
		output = self.getOuptputFileContents()
		self.assertEqual(staticOuput, output, errorPrefix + ' the output file should be "%s", but was "%s"' % (staticOuput, output))
		self.assertEqual(len(staticOuput), int(os.fstat(self.outputFile.fileno()).st_size), errorPrefix + ' the output file should have had length %i, but had length %i' % (len(staticOuput), os.fstat(self.outputFile.fileno()).st_size))
	
	def test_taskMessage(self):
		'''Test out that the taskMessage options properly work'''
		
		firstTest = "this is some test output" # length: 24
		secondTest = "	this test is a bit longer by nececisty" # length: 39
		thirdTest = "a shorter one" # length: 13
		
		# setup
		self.assertEqual(0, os.fstat(self.outputFile.fileno()).st_size, 'The newly opended file should have no length')
		
		# test by progressively writing the three strings as taskMessages
		self.outputHandler.update(taskMessage=firstTest)
		self.compareOutput('After the first message', firstTest)
		
		self.outputHandler.update(taskMessage=secondTest)
		self.compareOutput('After the second message', secondTest)
		
		self.outputHandler.update(taskMessage=thirdTest)
		self.compareOutput('After the third message', thirdTest)
		
		# test that status messages get wiped out by a new taskMessage
		self.outputHandler.update(taskMessage=firstTest, statusMessage=secondTest)
		self.compareOutput('After setting up with a taskMessage and a taskMessage', firstTest + secondTest)
		
		self.outputHandler.update(taskMessage=thirdTest)
		self.compareOutput('After replacing the taskMessage', thirdTest)
		
		# test that progress messages get wiped out by a new taskMessage
		self.outputHandler.update(taskMessage=firstTest, progressTemplate=secondTest)
		self.compareOutput('After setting up with a taskMessage and a simple progressTemplate', firstTest + secondTest)
		
		self.outputHandler.update(taskMessage=thirdTest)
		self.compareOutput('After replacing a taskMessage and a progressMessage with just a taskMessage', thirdTest)
		
		# put in an empty taskMessage
		self.outputHandler.update(taskMessage='')
		self.compareOutput('After replacing taskMessage with an empty string', '')
		
		# back to the third message, and verify that the contents of the file
		self.outputHandler.update(taskMessage=thirdTest)
		self.compareOutput('After replacing taskMessage with the third test string', thirdTest)
	
	def test_statusMessage(self):
		'''Test the statusMessage options'''
		
		taskMessage = "this is the prefix "
		
		firstTest = "			option with some tabs" # 24
		secondTest = "tabs at the end					" # 20
		thidTest = "just a longer string that either of the other two" # 49
		
		genericProgressTemplate = "whatever I felt like at the moment"
		
		# setup
		self.compareOutput('At initial setup', '')

		self.outputHandler.update(taskMessage=taskMessage)
		self.compareOutput('After setting up with a taskMessage', taskMessage)
		
		# tests to see that changing the statusMessage has the results we thing it should
		self.outputHandler.update(statusMessage=firstTest)
		self.compareOutput('After the first statusMessage', taskMessage + firstTest)
		
		self.outputHandler.update(statusMessage=secondTest)
		self.compareOutput('After the second statusMessage', taskMessage + secondTest)
		
		self.outputHandler.update(statusMessage=thidTest)
		self.compareOutput('After the third statusMessage', taskMessage + thidTest)
		
		# an empty statusMessage
		self.outputHandler.update(statusMessage='')
		self.compareOutput('After an empty statusMessage', taskMessage)
		
		# test that a new statusMessage wipes out a progressMessage
		self.outputHandler.update(statusMessage=thidTest, progressTemplate=genericProgressTemplate)
		self.compareOutput('After adding progressMessage to an empty statusMessage', taskMessage + thidTest + genericProgressTemplate)
		
		self.outputHandler.update(statusMessage=secondTest)
		self.compareOutput('After changeing the statusMessage to wipe out a progressMessage', taskMessage + secondTest)
	
	def test_progressMessage(self):
		'''Test the progressMessage options'''
		
		taskMessage = 'This should be fun - '
		
		firstStatusMessage	= 'some times you feel like a nut: '
		secondStatusMessage	= "some times you don't: "
		
		staticProgressTemplate	= 'just a simple progress message'
		messyProgressTemplate	= 'a progress message with things that look like substitutions %%s %%i %%f'
		messyProgressTemplateExpectedValue = 'a progress message with things that look like substitutions %s %i %f'
		
		valueProgressTemplate					= 'value %(value)i'
		valueInBytesProgressTemplate			= 'valueInBytes %(valueInBytes)s'
		expectedLengthProgressTemplate			= 'expectedLength %(expectedLength)i'
		expectedLengthInBytesProgressTemplate	= 'expectedLengthInBytes %(expectedLengthInBytes)s'
		percentageProgressTemplate				= 'progressPercentage %(progressPercentage)i%%'
		recentRateInBytesProgressTemplate		= 'recentRateInBytes %(recentRateInBytes)s'
		
		# setup
		self.compareOutput('At initial setup', '')
		
		self.outputHandler.update(taskMessage=taskMessage, statusMessage=firstStatusMessage)
		self.compareOutput('After setting up with a taskMessage and the first statusMessage', taskMessage + firstStatusMessage)
		
		# static staticProgressTemplate
		self.outputHandler.update(progressTemplate=staticProgressTemplate)
		self.compareOutput('After setting the staticProgressTemplate', taskMessage + firstStatusMessage + staticProgressTemplate)
		
		self.outputHandler.update(value=45, expectedLength=100, forceUpdate=True)
		self.compareOutput('After changing the value under the staticProgressTemplate', taskMessage + firstStatusMessage + staticProgressTemplate)
		
		# change to the messyProgressTemplate
		self.outputHandler.update(progressTemplate=messyProgressTemplate)
		self.compareOutput('After changing to the messyProgressTemplate', taskMessage + firstStatusMessage + messyProgressTemplateExpectedValue)

		# check that the value and expectedLength values have not been reset
		self.assertEqual(45, self.outputHandler._value, 'After changing to the messyProgressTemplate the value variable should have remained 45, but was: ' + str(self.outputHandler._value))
		self.assertEqual(100, self.outputHandler._expectedLength, 'After changing to the messyProgressTemplate the expectedLength variable should have remained 100, but was: ' + str(self.outputHandler._expectedLength))
		
		# change to the second status message repeated three times, and back to the staticProgressTemplate
		self.outputHandler.update(statusMessage=(secondStatusMessage * 3), progressTemplate=staticProgressTemplate)
		self.compareOutput('After changing to the messyProgressTemplate', taskMessage + (secondStatusMessage * 3) + staticProgressTemplate)
		
		# check that the value and expectedLength values have been reset
		self.assertEqual(0, self.outputHandler._value, 'After changing to the messyProgressTemplate the value variable has not been reset to 0 as expected, but was: ' + str(self.outputHandler._value))
		self.assertEqual(0, self.outputHandler._expectedLength, 'After changing to the messyProgressTemplate the expectedLength variable has not been reset to 0 as expected, but was: ' + str(self.outputHandler._expectedLength))
		
		