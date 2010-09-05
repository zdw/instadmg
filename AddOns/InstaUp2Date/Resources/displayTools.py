#!/usr/bin/env python

import os, sys, time, math, curses

curses.setupterm()
eraseToLineEndChar		= curses.tigetstr('el')
gotoLineBeginingChar	= curses.tigetstr('cr')
tabLength				= 8 # ToDo: figure out how to get this from the terminal

class statusHandler:
	
	throttleUpdateSeconds		= .125			# limit updates to once every this many seconds, 0 is constant updates
	
	outputChannel				= sys.stdout	
	
	lastTaskMessage				= ''			# contents of last taskMessage written
	lastStatusMessage			= ''			# ditto for statusMessage
	lastProgressMessage			= ''			# ditto for lastProgressMessage
	
	progressTemplate			= ''
	# A template used to mark progress - always written on change
	#	can use values: 
	#		value (i or f)
	#		valueInBytes (s)
	#		expectedLength (i or f)
	#		expectedLengthInBytes (s)
	#		progressPercentage (i or f)
	#		recentRateInBytes (s) - 
	#	
	#	examples:
	#		' %(value)i of %(expectedLength)i'
	#		' %(percentage)i%% (%(recentRateInBytes)s)'
	
	_lastWrittenProgress		= ''			# what was last written, so we can unwrite it
	_lastTimeProgressWritten	= None			# timestamp when last written
	_lastValueWritten			= None			# value when we last wrote
	
	# values for progress message
	_value						= None			# the central value
	_expectedLength				= None			# used in caculating percentage done
	
	# so we don't double-tap the end
	_lineFinished				= False
	
	# --- progress helper methods ---
	
	def _expectedLengthInBytes(self):
		if self._expectedLength is None:
			return ''
		# ToDo: more paranoia
		
		return bytesToRedableSize(self._expectedLength)
	
	def _recentRateInBytes(self):
		'''Get a fomatted string with the rate since we last reported'''
		
		# ToDo: paranoid checks
		
		currentTime = time.time()
		
		if None in [self._lastTimeProgressWritten, self._value, self._lastValueWritten] or currentTime <= self._lastTimeProgressWritten:
			return 'N/A'
		
		return bytesToRedableSize((self._value - self._lastValueWritten)/(currentTime - self._lastTimeProgressWritten)) + "/sec"
	
	def _progressPercentage(self):
		'''Return the progress as a percentage of the total'''
		
		if self._expectedLength is None or self._expectedLength is 0:
			return 0
		
		if self._value is None:
			return 0
		
		return (float(self._value)/float(self._expectedLength)) * 100
	
	# ------ instance methods -------
	
	def __enter__(self):
		return self
	
	def __init__(self, outputChannel=None, taskMessage='', statusMessage='', progressTemplate='', value=0, expectedLength=None, throttleUpdateSeconds=None):
		
		if outputChannel is not None:
			self.outputChannel = outputChannel
		
		if throttleUpdateSeconds is not None:
			self.throttleUpdateSeconds = float(throttleUpdateSeconds)
		
		# if the outputChannel is the terminal, go to the start of the line and erase everything
		if self.outputChannel.isatty():
			self.outputChannel.write(gotoLineBeginingChar + eraseToLineEndChar)
		
		self.update(taskMessage=taskMessage, statusMessage=statusMessage, progressTemplate=progressTemplate, value=value, expectedLength=expectedLength)
	
	def __exit__(self, type, value, traceback):
		self.finishLine()
	
	def update(self, taskMessage=None, statusMessage=None, progressTemplate=None, value=None, expectedLength=None, forceUpdate=False):
		
		if self.throttleUpdateSeconds == 0:
			forceUpdate = True
		
		if taskMessage is not None:
			
			# move the cursor back to the start position
			if self.outputChannel.isatty():
				self.outputChannel.write(gotoLineBeginingChar + eraseToLineEndChar)
			else:
				self.outputChannel.seek(-1 * (len(self.lastTaskMessage) + len(self.lastStatusMessage) + len(self.lastProgressMessage)), 1)
			
			# write out the new taskMessage, and record it
			self.outputChannel.write(taskMessage)
			self.lastTaskMessage = taskMessage
			
			# reset lastStatusMessage, lastProgressMessage, and progressTemplate
			self.lastStatusMessage		= ''
			self.lastProgressMessage	= ''
			self.progressTemplate		= ''
		
		if statusMessage is not None:
			
			# move the cursor back to the start position
			if self.outputChannel.isatty():
				lengthToErase = len((self.lastTaskMessage + self.lastStatusMessage + self.lastProgressMessage).expandtabs()) - len(self.lastTaskMessage.expandtabs())
				self.outputChannel.write(('\b' * lengthToErase) + eraseToLineEndChar)
			else:
				self.outputChannel.seek(-1 * (len(self.lastStatusMessage) + len(self.lastProgressMessage)), 1)
			
			# write out the new taskMessage and record it
			self.outputChannel.write(statusMessage)
			self.lastStatusMessage = statusMessage
			
			# reset lastProgressMessage and progressTemplate
			self.lastProgressMessage	= ''
			self.progressTemplate		= ''
		
		# set the value variable
		if value is True:
			pass # keep the value we already had
		elif value is not None:
			self._value = float(value)
		elif taskMessage is not None or statusMessage is not None:
			self._value = 0 # reset for a new phase
		
		# set the expectedLength variable
		if expectedLength is True:
			pass # keep the value we already had
		elif expectedLength is not None:
			self._expectedLength = float(expectedLength)
			forceUpdate = True
		elif (taskMessage is not None) or (statusMessage is not None):
			self._expectedLength = 0 # reset for a new phase
		
		if progressTemplate is not None:
			self.progressTemplate = progressTemplate
			forceUpdate = True
		
		if self._lastTimeProgressWritten is None:
			forceUpdate = True
		elif time.time() - self._lastTimeProgressWritten > self.throttleUpdateSeconds:
			forceUpdate = True
		
		# write out the progressMessage
		if self.progressTemplate is not None and forceUpdate is True:
			
			# ToDo: optimize for progressTemplate being empty
			
			newProgressMessage = self.progressTemplate % {
				'value' : self._value,
				'valueInBytes' : bytesToRedableSize(self._value),
				'expectedLength' : self._expectedLength,
				'expectedLengthInBytes' : self._expectedLengthInBytes(),
				'progressPercentage' : self._progressPercentage(),
				'recentRateInBytes' : self._recentRateInBytes()
			}
			
			# move the cursor back and adjust the lengthToOverwrite
			if self.outputChannel.isatty():
				lengthToErase = len((self.lastTaskMessage + self.lastStatusMessage + self.lastProgressMessage).expandtabs()) - len((self.lastTaskMessage + self.lastStatusMessage).expandtabs())
				self.outputChannel.write('\b' * lengthToErase)
			else:
				self.outputChannel.seek(-1 * len(self.lastProgressMessage), 1)
			
			# write out the new progressMessage and record it
			self.outputChannel.write(newProgressMessage)
			self.lastProgressMessage = newProgressMessage
			
			# update lastTimeProgressWritten
			self._lastTimeProgressWritten = time.time()
			self._lastValueWritten = self._value
		
		if not self.outputChannel.isatty():
			self.outputChannel.truncate()
		
		self.outputChannel.flush()
	
	def finishLine(self):
		'''Finish the line... adding a newline'''
		
		if self._lineFinished is False:
			self.outputChannel.write('\n')
			self.outputChannel.flush()
		
		self._lineFinished = True

def secondsToReadableTime(seconds):

	seconds = int(math.fabs(seconds))
	responce = ""
	
	hours = int(math.floor(float(seconds)/(60*60)))
	if hours > 0:
		if hours > 1:
			responce += "%i hours " % hours
		else:
			responce += "%i hour " % hours
		seconds -= hours * 60*60
	
	minutes = int(math.floor(float(seconds)/60))
	if minutes > 0:
		if minutes > 1:
			responce += "%i minutes " % minutes
		else:
			responce += "%i minute " % minutes
		seconds -= minutes * 60
	
	if seconds > 0:
		if seconds > 1:
			responce += "%i seconds" % seconds
		else:
			responce += "%i second" % seconds
	
	if responce == "":
		responce = "less than one second"
	
	return responce.strip()

def bytesToRedableSize(bytes):
	
	if bytes is None:
		return 'None'
	
	bytes = int(bytes)
	
	if bytes >= 1024*1024*1024*1024:
		return "%.1f Terabytes" % (float(bytes)/(1024*1024*1024*1024))
	elif bytes >= 1024*1024*1024:
		return "%.1f Gigabytes" % (float(bytes)/(1024*1024*1024))
	elif bytes >= 1024*1024:
		return "%.1f Megabytes" % (float(bytes)/(1024*1024))
	elif bytes >= 1024:
		return "%.1f Kilobytes" % (float(bytes)/1024)
	else:
		return "%i Bytes" % bytes

if __name__ == '__main__':
	myHandler = statusHandler(taskMessage='AAAA')
	myHandler.update(taskMessage='a')
	myHandler.finishLine()
	
	myHandler = statusHandler(statusMessage='BBBB')
	myHandler.update(statusMessage='b')
	myHandler.finishLine()
	
	myHandler = statusHandler(progressTemplate='CCCC')
	myHandler.update(progressTemplate='c')
	myHandler.finishLine()
	

