
from collections import deque
import utils

from activeNote import ActiveNote
from noteProcessors.continuousNoteProcessor.columnProcessor import ColumnProcessor
from noteProcessors.continuousNoteProcessor.constants import Constants
from noteProcessors.continuousNoteProcessor.message import MessageType

class ColumnManager:

	def __init__(self, outOfTune, noteParser, sampleRate, samplesPerFrame, samplesPerInterval, maxHarmonic=6):
		self.globalIndex = 0 	# Index relative to start of global sample
		self.outOfTune = outOfTune
		self.sampleRate = sampleRate
		self.samplesPerInterval = samplesPerInterval
		self.columnProcessors = []
		self.activeNotes = []
		self.data = deque([], Constants.MAX_BUFFER_SIZE)
		self.data.extend([[0 for i in range(int(samplesPerFrame / 2))] for i in range(Constants.MAX_BUFFER_SIZE)])
		for note in noteParser.parseNotes():
			self.columnProcessors.append(
				ColumnProcessor(note, sampleRate, samplesPerFrame, note.frequency * outOfTune, maxHarmonic,  self)
			)
		self.runningMaximum = 0

	# Approximate value for maximum, used for filtering out low-valued data
	def updateRunningMaximum(self, maximum):
		diff = utils.percentDiff(maximum, self.runningMaximum)
		existingWeight = 4
		if diff > 1:
			existingWeight = 4 / diff
		self.runningMaximum = self.runningMaximum * existingWeight / 5 + maximum * (5 - existingWeight) / 5

	def processNewDataRow(self, row):
		self.data.append(row)
		self.updateRunningMaximum(max(row))
		# Each column processor will process the new row and potentially return a note.
		for i in range(len(self.columnProcessors)):
			message = self.columnProcessors[i].processNewDataRow()
			# If a new note is returned by a processor, we append it to the total list.
			if message.messageType == MessageType.NEW_NOTE:
				globalIndexOffset = self.globalIndex - Constants.MAX_BUFFER_SIZE - 1
				self.activeNotes.append(
					ActiveNote(message.note,
						(message.startIndex  + globalIndexOffset) * self.samplesPerInterval / self.sampleRate,
						(message.endIndex + globalIndexOffset) * self.samplesPerInterval / self.sampleRate,
						message.loudness
					)
				)

			if message.messageType == MessageType.NEW_FRAME:
				pass

		self.globalIndex += 1


	def getActiveNotes(self):
		# Normalise loudness of notes
		loudest = max([a.loudness for a in self.activeNotes])
		if loudest > ActiveNote.MAX_LOUDNESS:
			for a in self.activeNotes:
				a.loudness = a.loudness / loudest * ActiveNote.MAX_LOUDNESS

		# loudness filter. Ideally, this is filtered before this step to reduce memory.
		# However, loudness is a relative amount and makes sense to do this during post-processing.
		self.activeNotes = [an for an in self.activeNotes if an.loudness > ActiveNote.MAX_LOUDNESS / 8]
		return self.activeNotes

