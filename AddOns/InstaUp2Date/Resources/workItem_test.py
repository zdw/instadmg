import os, unittest

from workItem import workItem

class workItemTest(unittest.TestCase):
	'''Test that the workItem class works to setup items'''
	
	validLookingChecksumString = 'sha1:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
	
	# note: the action and container subclasses should take care of tesing the individual contents, this is only about the setup
	
	def parseTestHelper(self, testName, targetSource, targetSourceLocation, checksumString=validLookingChecksumString, kwargs={}):
		
		checksumType, checksumValue = checksumString.split(':')
		
		testItem = workItem(targetSource, checksum=checksumString, **kwargs)
		self.assertEqual(testItem.sourceLocation, targetSourceLocation, 'Using a %s (%s) to create an item but sourceLocation was: %s' % (testName, targetSource, testItem.sourceLocation))
		self.assertEqual(checksumType, testItem.checksumType, 'Using a %s (%s) to create an item but checksumType was: % rather than the expected: %s' % (testName, targetSource, testItem.checksumType, checksumType))
		self.assertEqual(checksumValue, testItem.checksumValue, 'Using a %s (%s) to create an item but checksumValue was: %s rather than the expected: %s' % (testName, targetSource, testItem.checksumValue, checksumValue))
		
	def test_parseOnly(self):
		'''Test that input gets parsed and stored correctly'''
		
		kwargs = {'smith':45, 'red':'blue'}
		
		# normal file path
		self.parseTestHelper(testName='file path', targetSource='/Applications/Mail.app', targetSourceLocation='/Applications/Mail.app', kwargs=kwargs)
		
		# file url
		self.parseTestHelper(testName='file url', targetSource='file:///Applications/Mail.app', targetSourceLocation='/Applications/Mail.app')
		
		# http path
		self.parseTestHelper(testName='http url', targetSource='http://nowhere.nowhere/someFile.dmg', targetSourceLocation='http://nowhere.nowhere/someFile.dmg')
		
		# test kwargs
		
		# container
		# 	ToDo: work here
		
	
class workItemTest_negative(unittest.TestCase):
	'''Confirm that workItem fails when it should'''
	
	# def __init__(self, source, checksumString=None, processItem=False, **kwargs):
	
	validLookingSource		= 'http://nowhere.nowhere/someFile.dmg'
	validLookingChecksum	= 'sha1:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
	
	def test_badSource(self):
		'''Confirm that workItem fails with bad source locations'''
		
		# no container
		self.assertRaises(ValueError, workItem, None, checksumString=self.validLookingChecksum)
		
		# bad scheme on container
		self.assertRaises(ValueError, workItem, 'invalid://nowhere.nowhere/someFile.dmg', checksumString=self.validLookingChecksum)
	
	def test_badChecksumString(self):
		'''Confirm that workItem fails with bad checksum strings'''
		
		self.assertRaises(ValueError, workItem, self.validLookingSource, checksumString='no colon')
		self.assertRaises(ValueError, workItem, self.validLookingSource, checksumString='two:colons:here')
	
	def test_containerPlusChecksum(self):
		'''Confirm that workItem fails when supplied a container and a checksum'''
		
		# ToDo: work here