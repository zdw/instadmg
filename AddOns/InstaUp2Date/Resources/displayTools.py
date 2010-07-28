#!/usr/bin/env python

import os, sys, time, math

class statusHandler:
	
	linePrefix				= ''
	linePrefixWritten		= True
	
	statusMessage			= ''
	
	updateMessage			= ''
	unwrittenUpdateMessage	= None
	
	outputChannel			= sys.stderr
	
	throttleUpdateSeconds	= .125				# limit updates to once every this many seconds, 0 is constant updates
	lastUpdateTime			= None
	
	def __init__(self, outputChannel=None, linePrefix=None, statusMessage=None, updateMessage=None, throttleUpdateSeconds=None):
		if outputChannel is not None:
			self.outputChannel = outputChannel
		
		if throttleUpdateSeconds is not None:
			self.throttleUpdateSeconds = float(throttleUpdateSeconds)
		
		self.linePrefix = linePrefix	# Note: we are delaying writing anything until we have something other than the prefix to write
		self.linePrefixWritten = False
		
		self.lastUpdateTime = time.time()
		
		self.update(statusMessage, updateMessage)
	
	def update(self, statusMessage=None, updateMessage=None, forceOutput=False):
		
		lengthChange = 0
		
		if self.linePrefixWritten is False and self.linePrefix not in ['', None] and (statusMessage is not None or updateMessage is not None):
			self.outputChannel.write(self.linePrefix)
			self.linePrefixWritten = True
		
		if statusMessage is not None:
			oldLength = len(self.statusMessage) + len(self.updateMessage)
			self.outputChannel.write('\b' * oldLength)
			
			self.statusMessage = str(statusMessage)
			
			if updateMessage is not None:
				self.updateMessage = str(updateMessage)
				self.unwrittenUpdateMessage = None
				
			elif self.unwrittenUpdateMessage is not None:
				self.updateMessage = self.unwrittenUpdateMessage
				self.unwrittenUpdateMessage = None
			
			lengthChange = oldLength - len(self.statusMessage) - len(self.updateMessage)
			self.outputChannel.write(self.statusMessage + self.updateMessage)
		
		elif updateMessage is not None:
			
			if forceOutput is False and self.throttleUpdateSeconds != 0 and (time.time() - self.lastUpdateTime) < self.throttleUpdateSeconds:
				self.unwrittenUpdateMessage = updateMessage
				return # limit writing to the terminal, to keep it from absorbing too much cpu
			
			self.unwrittenUpdateMessage = None
			
			oldLength = len(self.updateMessage)
			self.outputChannel.write('\b' * oldLength)
			
			self.updateMessage = str(updateMessage)
			
			lengthChange = oldLength - len(self.updateMessage)
			self.outputChannel.write(self.updateMessage)
		
		elif forceOutput is True:
			oldLength = len(self.statusMessage) + len(self.updateMessage)
			
			if self.unwrittenUpdateMessage is not None:
				self.updateMessage = self.unwrittenUpdateMessage
				self.unwrittenUpdateMessage = None
			
			self.outputChannel.write('\b' * oldLength)
			self.outputChannel.write(self.statusMessage + self.updateMessage)
		
		if lengthChange > 0:
			self.outputChannel.write('%s%s' % (' ' * lengthChange, '\b' * lengthChange))
		
		self.lastUpdateTime = time.time()
		self.outputChannel.flush()

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
