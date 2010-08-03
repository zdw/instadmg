#!/usr/bin/env python

import os, unittest, stat

from displayTools import statusHandler
from tempFolderManager import tempFolderManager

class test_statusHandler(unittest.TestCase):
	
	def test_statusMessage(self):
		
		# create a file to write to
		outerFolder = tempFolderManager.getNewTempFolder()
		outputFile = open(os.path.join(outerFolder, "outputFile"), "w")
		
		outputHandler = statusHandler(outputChannel=outputFile)
		
		firstTest = "this is some test output"
		secondTest = "this test is a bit longer by nececisty"
		thirdTest = "a shorter one"
		
		self.assertEqual(0, os.lstat(outputFile.name)[stat.ST_SIZE], 'The newly opended file should have no length')
		
		outputHandler.update(statusMessage=firstTest, forceOutput=True)
		
		self.assertEqual(len(firstTest), os.lstat(outputFile.name)[stat.ST_SIZE], 'After the first message the output file should have lenghth %i, but had length %i' % (len(firstTest), os.lstat(outputFile.name)[stat.ST_SIZE]))
