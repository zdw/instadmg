#!/usr/bin/python

import os, re

parseMacOSBuildString	= re.compile('^(?P<macOSBuildMajor>\d+)(?P<macOSBuildMinor>[a-zA-Z])(?P<macOSBuildNumber>\d+)(?P<macOSBuildExtra>[a-zA-Z])?$')
parseVersionString		= re.compile('^(?P<macOSType>MacOS X( (Client|Server))?)?( ?(?P<versionNumber>10\.\S+))?( ?(?P<buildString>\d+[a-zA-Z]\d+[a-zA-Z]?))?(\.dmg)?$')

class macOSXVersion:
	
	@classmethod
	def parseBuildString(myClass, inputItem):
		
		# -- validate input
		
		parsedBuildString = None
		
		if inputItem is None:
			raise ValueError('parseVersionString requires a version string or a volume to evaluate, got None')
		
		elif hasattr(inputItem, 'getMacOSInformation'):
			# this is a disc, replace the object with the version on the disc
			macOSInformation = versionString.getMacOSInformation()
			if macOSInformation is None:
				raise ValueError('The input to parseVersionString was a volume, but not an OS volume: ' + inputItem.getDisplayName())
			
			parsedBuildString = parseMacOSBuildString.search(macOSInformation['macOSBuild'])
		
		elif hasattr(leftBuild, 'capitalize'):
			parsedBuildString = parseMacOSBuildString.search(inputItem)
		
		else:
			raise ValueError('The first input to compareOSVersion not understandable: ' + str(inputItem))
		
		if parsedBuildString is None:
			raise ValueError('The first input to compareOSVersion not a build number that this system can understand: ' + str(inputItem))
		
		return {
			'macOSBuildMajor':parsedBuildString.group('macOSBuildMajor'),
			'macOSBuildMinor':parsedBuildString.group('macOSBuildMinor'),
			'macOSBuildNumber':parsedBuildString.group('macOSBuildNumber'),
			'macOSBuildExtra':parsedBuildString.group('macOSBuildExtra'),
			'guessedMacOSVersion':'10.%i.%i' % (int(parsedBuildString.group('majorVersion')) - 4, ord(parsedBuildString.group('minorVersion').lower()) - 97)
		}
	
	# ------ instance variables
	
	macOSType				= None
	macOSVersion			= None
	
	macOSBuild				= None
	macOSBuildMajor			= None
	macOSBuildMinor			= None
	macOSBuildNumber		= None
	macOSBuildExtra			= None
	
	# ------ instance methods
	
	def __init__(self, inputString, defaultMacOSType='MacOS X Client'):
		
		# -- validate input
		
		if not hasattr(inputString, 'capitalize'):
			raise ValueError('%s requires a string to process, got: %s' % (self.__class__.__name__, str(inputString)))
		
		# -- parse the inputString
		
		parsedInput = parseVersionString.search(inputString)
		if parsedInput is None:
			raise ValueError('The input to %s was not understood: %s' % (self.__class__.__name__, str(inputString)))
		
		if parsedInput.group('macOSType') is not None:
			self.macOSType = parsedInput.group('macOSType')
		else:
			self.macOSType = defaultMacOSType
		
		self.macOSVersion = parsedInput.group('versionNumber')
		self.macOSBuild = parsedInput.group('buildString')
		
		# -- parse the buildString
		
		if self.macOSBuild is None:
			raise ValueError('The input to %s dit not have a version string, this is required: %s' % (self.__class__.__name__, str(inputString)))
		
		parsedBuild = parseMacOSBuildString.search(self.macOSBuild)
		if parsedBuild is None:
			raise Exception('% was unable to parse the build number: %s' % (self.macOSBuild, str(inputString)))
		
		self.macOSBuildMajor	= parsedBuild.group('macOSBuildMajor')
		self.macOSBuildMinor	= parsedBuild.group('macOSBuildMinor')
		self.macOSBuildNumber	= parsedBuild.group('macOSBuildNumber')
		self.macOSBuildExtra	= parsedBuild.group('macOSBuildExtra')
		
		if self.macOSVersion is None:
			# Guess at it from the build number
			self.macOSVersion = '10.%i.%i' % (int(self.macOSBuildMajor) - 4, ord(self.macOSBuildMinor) - 97)
	
	def validateInput(self, other):
	
		if hasattr(other, 'getMacOSInformation'):
			# a volume object
			
			macOSInformation = other.getMacOSInformation()
			if macOSInformation is None:
				raise ValueError('In comparing %s a volume wih no MacOS Information %s' % self.__class__.__name__, str(other))
			
			parsedBuild = parseMacOSBuildString.search(macOSInformation['macOSBuild'])
			
			return {
				'macOSType':macOSInformation['macOSType'],
				'macOSBuildMajor':parsedBuild.group('macOSBuildMajor'),
				'macOSBuildMinor':parsedBuild.group('macOSBuildMinor'),
				'macOSBuildNumber':parsedBuild.group('macOSBuildNumber'),
				'macOSBuildExtra':parsedBuild.group('macOSBuildExtra')
			}
		
		elif hasattr(other, 'parseBuildString'):
			# this is a macOSXVersion object
			
			return {
				'macOSType':other.macOSType,
				'macOSBuildMajor':other.macOSBuildMajor,
				'macOSBuildMinor':other.macOSBuildMinor,
				'macOSBuildNumber':other.macOSBuildNumber,
				'macOSBuildExtra':other.macOSBuildExtra
			}
		
		elif hasattr(other, 'capitalize'):
			
			otherItem = macOSXVersion(other)
			
			return {
				'macOSType':otherItem.macOSType,
				'macOSBuildMajor':otherItem.macOSBuildMajor,
				'macOSBuildMinor':otherItem.macOSBuildMinor,
				'macOSBuildNumber':otherItem.macOSBuildNumber,
				'macOSBuildExtra':otherItem.macOSBuildExtra
			}
			
		else:
			raise ValueError('%s does not know how to compare with %s' % (self.__class__.__name__, str(other)))
	
	def __eq__(self, other):
		
		# -- validate input
		
		parsedInput = self.validateInput(other)
		
		# macOSType
		
		if self.macOSType != parsedInput['macOSType']:
			return False
		
		# macOSBuildMajor
		
		if self.macOSBuildMajor != parsedInput['macOSBuildMajor']:
			return False
		
		# macOSBuildMinor
		
		if self.macOSBuildMinor != parsedInput['macOSBuildMinor']:
			return False
		
		# macOSBuildNumber
		
		if self.macOSBuildNumber != parsedInput['macOSBuildNumber']:
			return False
		
		# macOSBuildExtra
		
		if self.macOSBuildExtra is None and parsedInput['macOSBuildExtra'] is None:
			return True
		elif self.macOSBuildExtra is None and parsedInput['macOSBuildExtra'] is not None:
			return False
		elif self.macOSBuildExtra is not None and parsedInput['macOSBuildExtra'] is None:
			return False
		# both have value
		elif self.macOSBuildExtra == parsedInput['macOSBuildExtra']:
			return True
		else:
			return False
		
	def __ne__(self, other):
		
		return not self.__eq__(other)
	
	def __lt__(self, other):
		
		# -- validate input
		
		parsedInput = self.validateInput(other)
		
		# macOSType
		
		if self.macOSType != parsedInput['macOSType']:
			return ValueError("The version numbers can't be compared between differnt MacOS X Server and MacOS X Client")
		
		# macOSBuildMajor
		
		if int(self.macOSBuildMajor) > int(parsedInput['macOSBuildMajor']):
			return False
		elif int(self.macOSBuildMajor) < int(parsedInput['macOSBuildMajor']):
			return True
		
		# macOSBuildMinor
		
		if ord(self.macOSBuildMinor.lower()) > ord(parsedInput['macOSBuildMinor'].lower()):
			return False
		elif ord(self.macOSBuildMinor.lower()) < ord(parsedInput['macOSBuildMinor'].lower()):
			return True
		
		# macOSBuildNumber
		
		if int(self.macOSBuildNumber) > int(parsedInput['macOSBuildNumber']):
			return False
		elif int(self.macOSBuildNumber) < int(parsedInput['macOSBuildNumber']):
			return True
		
		# macOSBuildExtra
		
		if self.macOSBuildExtra is None and parsedInput['macOSBuildExtra'] is None:
			return False
		# at least one exists
		elif self.macOSBuildExtra is None:
			return True
		
		elif parsedInput['macOSBuildExtra'] is None:
			return False
		# both exist
		elif ord(self.macOSBuildExtra.lower()) < ord(parsedInput['macOSBuildExtra'].lower()):
			return True
		
		return False
		
	def __gt__(self, other):
		
		# -- validate input
		
		parsedInput = self.validateInput(other)
		
		# macOSType
		
		if self.macOSType != parsedInput['macOSType']:
			return ValueError("The version numbers can't be compared between differnt MacOS X Server and MacOS X Client")
		
		# macOSBuildMajor
		
		if int(self.macOSBuildMajor) < int(parsedInput['macOSBuildMajor']):
			return False
		elif int(self.macOSBuildMajor) > int(parsedInput['macOSBuildMajor']):
			return True
		
		# macOSBuildMinor
		
		if ord(self.macOSBuildMinor.lower()) < ord(parsedInput['macOSBuildMinor'].lower()):
			return False
		elif ord(self.macOSBuildMinor.lower()) > ord(parsedInput['macOSBuildMinor'].lower()):
			return True
		
		# macOSBuildNumber
		
		if int(self.macOSBuildNumber) < int(parsedInput['macOSBuildNumber']):
			return False
		elif int(self.macOSBuildNumber) > int(parsedInput['macOSBuildNumber']):
			return True
		
		# macOSBuildExtra
		
		if self.macOSBuildExtra is None and parsedInput['macOSBuildExtra'] is None:
			return False
		# at least one exists
		elif parsedInput['macOSBuildExtra'] is None:
			return True
		
		elif self.macOSBuildExtra is None:
			return False
		# both exist
		elif ord(self.macOSBuildExtra.lower()) > ord(parsedInput['macOSBuildExtra'].lower()):
			return True
		
		return False
