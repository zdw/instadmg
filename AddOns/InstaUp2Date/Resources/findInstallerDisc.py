#!/usr/bin/python

'''Find the BaseOS to use based on path, version, or the default location'''

__version__ = '$Revision: 266 $'.split()[1]

import os, re, sys

from container				import container
import pathHelpers, commonConfiguration, commonExceptions, macOSXVersionParser

legacyOSDiscNames 		= ['Mac OS X Install Disc 1.dmg', 'Mac OS X Install DVD.dmg']

def findInstallerDisc(allowedBuilds=None, searchItems=None, systemType='MacOS X Client'):
	
	# -- validate input
	
	if systemType != 'MacOS X Client':
		raise NotImplementedError('At this time only MacOS X Client is supported')
	
	# allowedBuilds
	parsedAllowedBuilds = []
	if hasattr(allowedBuilds, 'capitalize'):
		for thisItem in allowedBuilds.split(','):
			try:
				parsedAllowedBuilds.append(macOSXVersionParser.macOSXVersion(thisItem.strip()))
			except:
				raise ValueError('The allowedBuild item is not in the correct form: ' + thisItem)
	
	elif hasattr(allowedBuilds, '__iter__'):
		if len(allowedBuilds) == 0:
			raise ValueError('There were no allowBuilds provided')
		
		for thisValue in allowedBuilds:
		
			try:
				parsedAllowedBuilds.append(macOSXVersionParser.macOSXVersion(thisValue))
			except:
				raise ValueError('The allowedBuild item is not in the correct form: ' + thisValue)
	
	elif allowedBuilds is not None:
		raise ValueError('Unable to understand the allowedBuild provided: ' + str(allowedBuilds))
	
	# -- confirm or setup search folders
	
	if hasattr(searchItems, 'capitalize'):
		# the path to a single item
		searchItems = [searchItems]
	
	elif hasattr(searchItems, '__iter__'):
		# array of paths to search items, so nothing to do
		pass
	
	elif searchItems is None:
		searchItems = []
		
		if allowedBuilds is not None:
			# non-legacy mode
			if not os.path.isdir(commonConfiguration.standardOSDiscFolder): # worry-warting
				raise ValueError('The legacy OS installer disc folder does not exist or was not a directory: ' + str(commonConfiguration.standardOSDiscFolder))
			searchItems.append(commonConfiguration.standardOSDiscFolder)
		
		if not os.path.isdir(commonConfiguration.legacyOSDiscFolder): # worry-warting
			raise ValueError('The legacy OS installer disc folder does not exist or was not a directory: ' + str(commonConfiguration.legacyOSDiscFolder))
		searchItems.append(commonConfiguration.legacyOSDiscFolder)

	else:
		raise ValueError('Did not understand the searchItems input: ' + str(searchItems))
	
	# confirm that the item in the list are valid
	searchContainers = []
	for thisItem in searchItems:
		thisContainer = None
		try:
			thisContainer = container(thisItem)
		except:
			raise ValueError('Unable to understand the search item: ' + str(thisItem))
		
		if not thisContainer.isContainerType('folder'): # note: dmg's are "folders"
			raise ValueError('The search item "%s" was a %s, which is not useable .Must be dmg, volume, or folder' % (thisItem, thisContainer.getType(()))
		
		searchContainers.append(thisContainer)
	
	# -- search through the folders
	
	# legacy search mode
	if allowedBuilds is None:
		for thisContainer in searchContainers:
		
			results = {
				'InstallerDisc':None,
				'SupportingDiscs':[]
			}
			
			innerSearchItems = None
			
			if thisContainer.isContainerType('dmg'):
				innerSearchItems = [thisContainer]
			else:
				innerSearchItems = [os.path.join(thisContainer.getWorkingPath(), internalItem) for internalItem in os.listdir(thisContainer.getWorkingPath())]
			
			for thisItem in innerSearchItems:
				
				if hasattr(thisItem, 'isContainerType'):
					results['InstallerDisc'] = thisItem
				else:
					candidateConainter	= None
					try:
						candidateConainter = container(thisItem)
					except:
						pass
					
					# we are in legacy mode, so fail if the name matches one of our preset names
					if os.path.basename(candidateConainter.getStoragePath()) in legacyOSDiscNames:
						if candidateConainter is None or not candidateConainter.isContainerType('dmg'): # note: volume would work here as well but needs InstaDMG support
							raise ValueError('In legacy mode the item "%s" was named like an installer disc, but was not a dmg' % thisItem)
						results['InstallerDisc'] = candidateConainter
					
					elif candidateConainter is not None and candidateConainter.isContainerType('dmg'): # note: volume would work here as well but needs InstaDMG support
						results['SupportingDiscs'].append(candidateConainter)
			
			if results['InstallerDisc'] is not None:
			
				macOSInformation = results['InstallerDisc'].getMacOSInformation()
				
				if macOSInformation is not None and macOSInformation['macOSInstallerDisc'] is True:
					return results
				
				else:
					raise ValueError('In legacy mode the item "%s" was named like an installer disc, but was not' % results['InstallerDisc'].getWorkingPath())
	
	# search by build information, note: this will never record any supporting discs
	else:
		
		# resort parsedAllowedBuilds so that higher versions are first
		parsedAllowedBuilds.sort(reverse=True)
		
		bestCandidate			= None
		bestCandidateVersion	= None
		
		for thisContainer in searchContainers:
			
			innerSearchItems = None
			
			if thisContainer.isContainerType('dmg'):
				innerSearchItems = [thisContainer]
			else:
				innerSearchItems = [os.path.join(thisContainer.getWorkingPath(), internalItem) for internalItem in os.listdir(thisContainer.getWorkingPath())]

			# ToDo: try to find the exact items by name first

			# find the item that matches the frontmost allowedBuilds item
			for thisItem in innerSearchItems:
				baseImageCandidate = None
				
				if hasattr(thisItem, 'isContainerType'):
					baseImageCandidate = thisItem
				else:
					try:
						baseImageCandidate = container(thisItem)
					except:
						continue
				
				if not baseImageCandidate.isContainerType('dmg'):
					continue
				
				macOSInformation = baseImageCandidate.getMacOSInformation()
				
				if macOSInformation['macOSInstallerDisc'] is not True:
					continue
				
				if macOSInformation['macOSType'] != 'MacOS X Client':
					continue
				
				# see if one of the patterns in allowedBuilds matches
				for thisAllowedBuild in parsedAllowedBuilds:
					if thisAllowedBuild == baseImageCandidate:
						if bestCandidateVersion is None:
							bestCandidate = baseImageCandidate
							bestCandidateVersion = macOSXVersionParser.macOSXVersion(macOSInformation['macOSBuild'])
						elif bestCandidateVersion > baseImageCandidate:
							bestCandidate = baseImageCandidate
							bestCandidateVersion = macOSXVersionParser.macOSXVersion(macOSInformation['macOSBuild'])
		
		if bestCandidate is not None:
			return {
				'InstallerDisc':bestCandidate,
				'SupportingDiscs':[]
			}
	
	raise commonExceptions.FileNotFoundException('Unable to find OS Installer disc in any provided folder: ' + str(searchItems))

def main():
	
	import optparse
	
	# ---- parse options
	
	def print_version(option, opt, value, optionsParser):
		optionsParser.print_version()
		sys.exit(0)
	
	optionParser = optparse.OptionParser(usage="%prog [options]", version="%prog rev" + __version__)
	optionParser.remove_option('--version')
	optionParser.add_option("-v", "--version", action="callback", callback=print_version, help="Print the version number and quit")
	
	optionParser.add_option("-b", "--allowed-builds", dest="allowedBuilds", type="string", default=None, help="Build number or comma-seperated list of build numbers to use")
	optionParser.add_option("-s", "--add-search-item", dest="searchItems", default=None, action="append", help="Add this to the list of items to search. If none are given default options are used.")
	optionParser.add_option("-t", "--system-type", dest="systemType", default='MacOS X Client', choices=['MacOS X Client'], help="Type of MacOS X system to process, currenly accepts only 'MacOS X Client'")
	
	optionParser.add_option("", "--supress-return", dest='suppressReturn', action="store_true", default=False, help="Format the output without labels or an end return for scripts")
	
	(options, args) = optionParser.parse_args()
	
	if len(args) > 0:
		optionParser.error('%prog does not accept any arguments. Was given: ' + str(args))
	
	# ---- get result
	
	# note: we are letting python errors bubble out to record in bash
	
	result = findInstallerDisc(allowedBuilds=options.allowedBuilds, searchItems=options.searchItems, systemType=options.systemType)
	
	if options.suppressReturn is True:
		supportingDiscPaths = []
		for thisSupportingDisc in result['SupportingDiscs']:
			supportingDiscPaths.append(thisSupportingDisc.getStoragePath())
		
		sys.stdout.write("\n".join([result['InstallerDisc'].getStoragePath()] + supportingDiscPaths))
		
	else:
		print('Installer Disc: ' + result['InstallerDisc'].getStoragePath())
		for thisSupportDisc in result['SupportingDiscs']:
			print('Support Disc: ' + thisSupportDisc.getStoragePath())
	
	sys.exit(0)

if __name__ == '__main__':
	main()
