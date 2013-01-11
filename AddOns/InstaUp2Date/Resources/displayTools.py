#!/usr/bin/python

import os, sys, time, math, curses, atexit

try:
	curses.setupterm()
	cursesAvailable = True
	eraseToLineEndChar		= curses.tigetstr('el')
	gotoLineBeginingChar	= curses.tigetstr('cr')
except:
	cursesAvailable = False
tabLength				= 8 # ToDo: figure out how to get this from the terminal

# global list of exitHandlers
# all statusHandler objects in the list will have finishLine called atexit.
exitHandlers = list()

def addAtExit(handler):
	exitHandlers.append(handler)

def removeAtExit(handler):
	exitHandlers.remove(handler)

def finishLinesAtExit():
	for handler in exitHandlers[:]:
		handler.finishLine()

atexit.register(finishLinesAtExit)


class statusHandler:
	'''Display dynamic status messages. A taskMessage is followed by a
	statusMessage or a progress report, generated from a progressTemplate.
	'''
	
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
		if self.useCurses():
			self.outputChannel.write(gotoLineBeginingChar + eraseToLineEndChar)
		
		self.update(taskMessage=taskMessage, statusMessage=statusMessage, progressTemplate=progressTemplate, value=value, expectedLength=expectedLength)
		
		# Add a this object to the atexit handler
		addAtExit(self)
	
	def __exit__(self, type, value, traceback):
		self.finishLine()
	
	def useCurses(self):
		'''Check if we're on a tty with curses setup.'''
		
		if self.outputChannel is not None:
			return self.outputChannel.isatty() and cursesAvailable
		return False
	
	def update(self, taskMessage=None, statusMessage=None, progressTemplate=None, value=None, expectedLength=None, forceUpdate=False):
		
		if (self.throttleUpdateSeconds == 0) or (not self.useCurses()):
			forceUpdate = True
		
		if taskMessage is not None:
			
			# move the cursor back to the start position
			if self.useCurses():
				self.outputChannel.write(gotoLineBeginingChar + eraseToLineEndChar)
				# write out the new taskMessage
				self.outputChannel.write(taskMessage)
			
			# record the new taskMessage
			self.lastTaskMessage = taskMessage
			
			# reset lastStatusMessage, lastProgressMessage, and progressTemplate
			self.lastStatusMessage		= ''
			self.lastProgressMessage	= ''
			self.progressTemplate		= ''
		
		if statusMessage is not None:
			
			# move the cursor back to the start position
			if self.useCurses():
				lengthToErase = len((self.lastTaskMessage + self.lastStatusMessage + self.lastProgressMessage).expandtabs()) - len(self.lastTaskMessage.expandtabs())
				self.outputChannel.write(('\b' * lengthToErase) + eraseToLineEndChar)
				# write out the new statusMessage
				self.outputChannel.write(statusMessage)
			
			# record the new statusMessage
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
			if self.useCurses():
				lengthToErase = len((self.lastTaskMessage + self.lastStatusMessage + self.lastProgressMessage).expandtabs()) - len((self.lastTaskMessage + self.lastStatusMessage).expandtabs())
				self.outputChannel.write('\b' * lengthToErase)
				# write out the new progressMessage
				self.outputChannel.write(newProgressMessage)
			
			# record the new progressMessage
			self.lastProgressMessage = newProgressMessage
			
			# update lastTimeProgressWritten
			self._lastTimeProgressWritten = time.time()
			self._lastValueWritten = self._value
		
		self.outputChannel.flush()

	
	def finishLine(self):
		'''Finish the line... adding a newline'''
		
		# Remove this object from the atexit handler
		removeAtExit(self)
		
		if self._lineFinished is False:
			if not self.useCurses():
				if self.lastTaskMessage:
					self.outputChannel.write(self.lastTaskMessage)
				for s in (self.lastStatusMessage, self.lastProgressMessage):
					if s:
						self.outputChannel.write(s)
						break
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
	myHandler = statusHandler(taskMessage="This is the task ")
	myHandler.update(progressTemplate='and this is progress %(progressPercentage)i%%', expectedLength=10)
	for i in range(11):
		time.sleep(0.1)
		myHandler.update(value=i)
	myHandler.finishLine()
	
	myHandler = statusHandler(taskMessage="This is the task ")
	for s in ("zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten"):
		time.sleep(0.1)
		myHandler.update(statusMessage="and this is status %s" % s)
	myHandler.update(statusMessage="and this is done")
	myHandler.finishLine()
	
	myHandler = statusHandler(taskMessage='This task is in progress')
	time.sleep(0.5)
	myHandler.update(taskMessage='This task is done')
	myHandler.finishLine()
	
	h1 = statusHandler(taskMessage='This is task 1 and it will be aborted, but printed anyway')
	h2 = statusHandler(taskMessage='This is task 2 and it will be aborted, but printed anyway')
	h3 = statusHandler(taskMessage='This is task 3 and it will be aborted, but printed anyway')
	sys.exit()

