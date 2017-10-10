
import copy
from collections import deque
from collections import defaultdict
from numpy import fft
import time

from activeNote import ActiveNote
from noteParser import Note
from noteProcessors.abstractNoteProcessor import AbstractNoteProcessor
from noteProcessors.continuousNoteProcessor.columnManager import ColumnManager
from noteProcessors.continuousNoteProcessor.constants import Constants
from noteProcessors.continuousNoteProcessor.message import Message, MessageType, NewNoteMessage
from noteProcessors.continuousNoteProcessor.rowGenerators import ContinuousGenerator, RecursiveGenerator
import utils


class ContinuousNoteProcessor(AbstractNoteProcessor):
	def __init__(self, waveform, sampleRate, noteParser=None, shapeStrategy=None):
		super(ContinuousNoteProcessor, self).__init__(waveform, sampleRate, noteParser)

	# Estimates how much the whole song is offtune by. This will increase search capabilities.
	# The assumption here is that all notes of a song are offtune by a similar amount.
	# TODO: Change this so each section of the song has its own set of approximation.
	def getOutOfTune(self):
		def getLocalMax(arr):
			localMax = []
			for i in range(1, len(arr) - 1):
				if arr[i] > arr[i - 1] and arr[i] > arr[i + 1]:
					localMax.append(i)
			return localMax

		# Number of notes to take when calculating the offset.
		referenceNoteCount = 6
		# Duration of time to take as samples when calculating offset
		referenceDuration = self.sampleRate * 5
		# Arbitrary start index of offset
		referenceStartIndex = 10000
		referenceFFT = fft.fft(self.waveform[referenceStartIndex: referenceStartIndex + referenceDuration])
		referenceFFT = [abs(f) for f in referenceFFT][:int(len(referenceFFT) / 2)]

		localMax = getLocalMax(referenceFFT)
		localMax.sort(key=lambda x: -referenceFFT[x])

		i = 0
		existingNotes = []
		percentDiffs = []

		# Get double the reference note count
		while len(existingNotes) <= referenceNoteCount * 2:
			index = localMax[i]
			i += 1
			frequency = index * self.sampleRate / referenceDuration
			closestNote, percentDiff = self.getClosestNote(frequency)
			if closestNote in existingNotes:
				continue
			existingNotes.append(closestNote)
			percentDiffs.append(percentDiff)

		# Remove the notes that increase deviation within the set the most
		iterations = len(existingNotes) - referenceNoteCount
		for i in range(referenceNoteCount):
			avg = sum(percentDiffs) / len(percentDiffs)
			percentDiffs.sort(key=lambda x: abs(x - avg))
			percentDiffs = percentDiffs[:-1]

		outOfTune = sum(percentDiffs) / len(percentDiffs)
		return outOfTune

	# The purpose of this function is to meld the instances where a row is 0x0x0x0... where x is a positive number.
	# In these cases, it is likely a case of interference from a previous note in the same frame.
	# Temporarily deprecated
	def meldRow(self, row, notesFoundInFrame):
		def isLowValue(value, referenceValue):
			if value < 0:
				return True
			if value < referenceValue and utils.percentDiff(value, referenceValue) > 4:
				return True
			return False

		def isHighValue(value, referenceValue):
			if referenceValue < 0:
				referenceValue = 0
			if utils.percentDiff(value, value - referenceValue) < 0.1:
				return True
			return False

		interpolateIndices = []
		for index, loudness in notesFoundInFrame.items():
			elements3 = [row[i] for i in range(index - 3, index + 4)]
			referenceValue = max(elements3)
			value = loudness / Constants.COLUMN_PROCESSOR_DATA_WIDTH
			if utils.percentDiff(referenceValue, value) > 1 and value < referenceValue:
				return
			referenceIndex = index - 1 + elements3.index(referenceValue)
			for direction in [-1, 1]:
				searchIndex = referenceIndex
				while abs(searchIndex - referenceIndex) < 8:
					searchIndex += direction
					if isLowValue(row[searchIndex], referenceValue):
						if isHighValue(row[searchIndex + 1], row[searchIndex]) and isHighValue(row[searchIndex - 1], row[searchIndex]):
							if isLowValue(row[searchIndex - 2], referenceValue) or isLowValue(row[searchIndex + 2], referenceValue):
								interpolateIndices.append(searchIndex)
								print(loudness)

		for index in interpolateIndices:
			row[index] = (row[index - 1] + row[index + 1]) / 2


	def run(self):
		samplesPerInterval = 512
		intervalsPerFrame = 128
		samplesPerFrame = samplesPerInterval * intervalsPerFrame
		rowGenerator = ContinuousGenerator(samplesPerInterval, intervalsPerFrame, self.waveform)
		rows = rowGenerator.generate()
		outOfTune = self.getOutOfTune()
		columnManager = ColumnManager(outOfTune, self.noteParser, self.sampleRate, samplesPerFrame, samplesPerInterval)

		visualise = False
		for row in rows:
			if visualise:
				d2Array.append(d2Row[:2000])
			columnManager.processNewDataRow(row)

		if visualise:
			for columnIndex in range(len(d2Array[0])):
				dataIndex = len(d2Array)
				negativeCollector = 0
				while dataIndex > 0:
					dataIndex -= 1
					if d2Array[dataIndex][columnIndex] < 0:	# Propagate negative number up
						negativeCollector += d2Array[dataIndex][columnIndex]
						d2Array[dataIndex][columnIndex] = 0
					else:
						if negativeCollector < 0:
							if d2Array[dataIndex][columnIndex] > -negativeCollector:
								d2Array[dataIndex][columnIndex] += negativeCollector
								negativeCollector = 0
							else:
								negativeCollector += d2Array[dataIndex][columnIndex]
								d2Array[dataIndex][columnIndex] = 0
			utils.d2Plot(d2Array, "out/continous2.png", widthCompression=100, heightCompression=10)

		return columnManager.getActiveNotes()
