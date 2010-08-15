#!/usr/bin/env python

import os, sys, time, math

class statusHandler:
	
	throttleUpdateSeconds	= .125			# limit updates to once every this many seconds, 0 is constant updates
	
	outputChannel			= sys.stdout	
	
	taskMessage				= ''			# The overall task - always written on change, wipes out status and progress sections
	statusMessage			= ''			# The phase in the task - always written on change, wipes out progress section
	progressTemplate		= ''			# A template used to mark progress - always written on change
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
							    			#		' %%(percentage)i (%(recentRateInBytes)s)'
	
	_lastWrittenProgress	= ''			# what was last written, so we can unwrite it
	_lastTimeWritten		= None			# timestamp when last written
	_lastValueWritten		= None			# value when we last wrote
	
	# values for progress message
	_value					= None			# the central value
	_expectedLength			= None			# used in caculating percentage done
	
	# so we don't double-tap the end
	_lineFinished			= False
	
	# --- progress helper methods ---
	
	def _expectedLengthInBytes(self):
		if self._expectedLength is None:
			return ''
		# ToDo: more paranoia
		
		return translateBytes(self._expectedLength)
	
	def _recentRateInBytes(self):
		'''Get a fomatted string with the rate since we last reported'''
		
		# ToDo: paranoid checks
		
		currentTime = time.time()
		
		if None in [self._lastTimeWritten, self._value, self._lastValueWritten] or currentTime <= self._lastTimeWritten:
			return 'N/A'
		
		return translateBytes((self._value - self._lastValueWritten)/(currentTime - self._lastTimeWritten)) + "/sec"
	
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
				
		self.update(taskMessage=taskMessage, statusMessage=statusMessage, progressTemplate=progressTemplate, value=value, expectedLength=expectedLength)
	
	def __exit__(self, type, value, traceback):
		self.finishLine()
	
	def update(self, taskMessage=None, statusMessage=None, progressTemplate=None, value=None, expectedLength=None, forceUpdate=False):
		
		if self.throttleUpdateSeconds == 0:
			forceUpdate = True
		
		lengthToOverwrite = 0	# numbers of characters that need to be overwritten by spaces at the end of the line
		
		if taskMessage is not None:
			
			# delete everything written to this point
			lengthToOverwrite = len(self.taskMessage) + len(self.statusMessage) + len(self._lastWrittenProgress)
			
			if self.outputChannel.isatty():
				self.outputChannel.write('\b' * lengthToOverwrite)
				self.outputChannel.write(' ' * lengthToOverwrite)
				self.outputChannel.flush()
				self.outputChannel.write('\b' * lengthToOverwrite)
			else:
				self.outputChannel.seek(lengthToOverwrite * -1, 1)
			
			# clean things out
			self.statusMessage = ''
			self._lastWrittenProgress = ''
			self._value = None
			self._expectedLength = None
			
			# write out the new value
			self.outputChannel.write(taskMessage)
			lengthToOverwrite -= len(taskMessage)
			if lengthToOverwrite < 0:
				lengthToOverwrite = 0
			self.taskMessage = taskMessage
			
			# make sure we write out everything
			forceUpdate = True
			self._lastTimeWritten = time.time()
		
		if statusMessage is not None:
			# delete what we have written for taskMessage and progress
			lengthToOverwrite += len(self.statusMessage) + len(self._lastWrittenProgress)
			
			if self.outputChannel.isatty():
				self.outputChannel.write('\b' * (len(self.statusMessage) + len(self._lastWrittenProgress)))
				self.outputChannel.write(' ' * (len(self.statusMessage) + len(self._lastWrittenProgress)))
				self.outputChannel.flush()
				self.outputChannel.write('\b' * (len(self.statusMessage) + len(self._lastWrittenProgress)))
			else:
				self.outputChannel.seek(lengthToOverwrite * -1, 1)
			
			# cleanup progress
			self._lastWrittenProgress = ''
			self._value = None
			self._expectedLength = None
			
			# write out the new value
			self.outputChannel.write(statusMessage)
			lengthToOverwrite -= len(statusMessage)
			if lengthToOverwrite < 0:
				lengthToOverwrite = 0
			
			self.statusMessage = statusMessage
			self._lastTimeWritten = time.time()
		
		if value is not None:
			self._value = float(value) # ToDo: what if None is the desired value?
		
		if expectedLength is not None:
			self._expectedLength = float(expectedLength)
			forceUpdate = True
		
		if progressTemplate is not None or value is not None:
			
			if self._lastTimeWritten is None:
				forceUpdate = True
			
			if progressTemplate is not None:
				self.progressTemplate = progressTemplate
				forceUpdate = True
			
			if forceUpdate is True or (time.time() - self._lastTimeWritten) > self.throttleUpdateSeconds:
				
				# ToDo: optimize for progressTemplate being empty
				
				# delete what we have written for progress
				lengthToOverwrite += len(self._lastWrittenProgress)
				if self.outputChannel.isatty():
					self.outputChannel.write('\b' * len(self._lastWrittenProgress))
					self.outputChannel.write(' ' * len(self._lastWrittenProgress))
					self.outputChannel.flush()
					self.outputChannel.write('\b' * len(self._lastWrittenProgress))
				else:
					self.outputChannel.seek(lengthToOverwrite * -1, 1)
				
				if self.progressTemplate is not '':
					# write out the new value
					self._lastWrittenProgress = self.progressTemplate % {
						'value' : self._value,
						'valueInBytes' : translateBytes(self._value),
						'expectedLength' : self._expectedLength,
						'expectedLengthInBytes' : self._expectedLengthInBytes(),
						'progressPercentage' : self._progressPercentage(),
						'recentRateInBytes' : self._recentRateInBytes()
					}
					self.outputChannel.write(self._lastWrittenProgress)
					lengthToOverwrite -= len(self._lastWrittenProgress)
					if lengthToOverwrite < 0:
						lengthToOverwrite = 0
					
				# update internal watchers
				self._lastValueWritten = self._value
				self._lastTimeWritten = time.time()
		
		if lengthToOverwrite > 0:
			if self.outputChannel.isatty():
				self.outputChannel.write(' ' * lengthToOverwrite)
				self.outputChannel.flush()
				self.outputChannel.write('\b' * lengthToOverwrite)
			else:
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

def translateBytes(bytes):
	
	if bytes is None:
		return 'None'
	
	if int(bytes) >= 1024*1024*1024*1024:
		return "%.1f Terabytes" % (float(bytes)/(1024*1024*1024*1024))
	elif int(bytes) >= 1024*1024*1024:
		return "%.1f Gigabytes" % (float(bytes)/(1024*1024*1024))
	elif int(bytes) >= 1024*1024:
		return "%.1f Megabytes" % (float(bytes)/(1024*1024))
	elif int(bytes) >= 1024:
		return "%.1f Kilobytes" % (float(bytes)/1024)
	else:
		return "%i Bytes" % bytes

