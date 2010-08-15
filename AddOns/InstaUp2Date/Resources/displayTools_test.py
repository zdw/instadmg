#!/usr/bin/env python

import os, unittest, stat, subprocess

from displayTools import statusHandler
from tempFolderManager import tempFolderManager

class test_statusHandler(unittest.TestCase):
	
	def test_taskMessage(self):
		
		# create a file to write to
		outerFolder = tempFolderManager.getNewTempFolder()
		outputFile = open(os.path.join(outerFolder, "outputFile"), "w")
		
		outputHandler = statusHandler(outputChannel=outputFile)
		
		firstTest = "this is some test output" # length: 24
		secondTest = "this test is a bit longer by nececisty" # length: 38
		thirdTest = "a shorter one" # length: 13
		
		self.assertEqual(0, os.lstat(outputFile.name)[stat.ST_SIZE], 'The newly opended file should have no length')
		
		# test by progressively writing the three strings as taskMessages
		outputHandler.update(taskMessage=firstTest)
		self.assertEqual(len(firstTest), int(os.lstat(outputFile.name)[stat.ST_SIZE]), 'After the first message the output file should have had length %i, but had length %i' % (len(firstTest), os.lstat(outputFile.name)[stat.ST_SIZE]))
		outputHandler.update(taskMessage=secondTest)
		self.assertEqual(len(secondTest), int(os.lstat(outputFile.name)[stat.ST_SIZE]), 'After the second message the output file should have had length %i, but had length %i' % (len(secondTest), os.lstat(outputFile.name)[stat.ST_SIZE]))
		outputHandler.update(taskMessage=thirdTest)
		self.assertEqual(len(thirdTest), int(os.lstat(outputFile.name)[stat.ST_SIZE]), 'After the third message the output file should have had length %i, but had length %i' % (len(thirdTest), os.lstat(outputFile.name)[stat.ST_SIZE]))
		
		# test that status messages get wiped out by a new taskMessage
		outputHandler.update(taskMessage=firstTest, statusMessage=secondTest)
		self.assertEqual(len(firstTest) + len(secondTest), int(os.lstat(outputFile.name)[stat.ST_SIZE]), 'With a taskMessage and a statusMessage the output file should have had length %i, but had length %i' % (len(firstTest) + len(secondTest), os.lstat(outputFile.name)[stat.ST_SIZE]))
		outputHandler.update(taskMessage=thirdTest)
		self.assertEqual(len(thirdTest), int(os.lstat(outputFile.name)[stat.ST_SIZE]), 'After replacing a taskMessage and a statusMessage with just a taskMessage the output file should have had length %i, but had length %i' % (len(thirdTest), os.lstat(outputFile.name)[stat.ST_SIZE]))
		
		# test that progress messages get wiped out by a new taskMessage
		outputHandler.update(taskMessage=firstTest, progressTemplate=secondTest)
		self.assertEqual(len(firstTest) + len(secondTest), int(os.lstat(outputFile.name)[stat.ST_SIZE]), 'With a taskMessage and a progressMessage the output file should have had length %i, but had length %i' % (len(firstTest) + len(secondTest), os.lstat(outputFile.name)[stat.ST_SIZE]))
		outputHandler.update(taskMessage=thirdTest)
		self.assertEqual(len(thirdTest), int(os.lstat(outputFile.name)[stat.ST_SIZE]), 'After replacing a taskMessage and a progressMessage with just a taskMessage the output file should have had length %i, but had length %i' % (len(thirdTest), os.lstat(outputFile.name)[stat.ST_SIZE]))