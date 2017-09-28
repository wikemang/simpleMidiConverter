from numpy import fft
import copy
from collections import deque
from collections import defaultdict
import time
import gc

from activeNote import ActiveNote
from noteProcessors.abstractNoteProcessor import AbstractNoteProcessor
import utils
from noteParser import Note

class MessageType:
	NO_EVENT = 0
	NEW_NOTE = 1
	NEW_FRAME = 2

class Message:
	def __init__(self, messageType):
		self.messageType = messageType

# This message should tell that a new note be created with the parameters
class NewNoteMessage(Message):
	def __init__(self, startIndex, endIndex, note, loudness, centerFrequencyIndex):
		self.startIndex = startIndex
		self.endIndex = endIndex
		self.note = note
		self.loudness = loudness
		self.centerFrequencyIndex = centerFrequencyIndex
		super(NewNoteMessage, self).__init__(MessageType.NEW_NOTE)

# This message tells the manager that the same note may have repeated in the same frame, but is unsure
class NewFrameMessage(Message):
	def __init__(self):
		super(NewFrameMessage, self).__init__(MessageType.NEW_FRAME)

# Constants for note processing
class ProcessConstants:
	MAX_BUFFER_SIZE = 250	# Should only be about a few seconds (ie the length of really long note)
	CUTOFF_SHARPNESS = 4
	COLUMN_PROCESSOR_DATA_WIDTH = 5


class ColumnProcessor:
	data = deque([], ProcessConstants.MAX_BUFFER_SIZE)
	runningMaximum = 0

	@classmethod
	def updateRunningMaximum(cls, maximum):
		diff = utils.percentDiff(maximum, cls.runningMaximum)
		existingWeight = 4
		if diff > 1:
			existingWeight = 4 / diff
		cls.runningMaximum = cls.runningMaximum * existingWeight / 5 + maximum * (5 - existingWeight) / 5

	def __init__(self, note, sampleRate, samplesPerFrame, modifiedFrequency, maxHarmonic, manager):
		self.note = note
		self.maxHarmonic = maxHarmonic

		self.centerIndex = int(round(modifiedFrequency * samplesPerFrame / sampleRate))
		self.firstIndex = self.centerIndex - int(ProcessConstants.COLUMN_PROCESSOR_DATA_WIDTH / 2)
		self.lastIndex = self.centerIndex + int(ProcessConstants.COLUMN_PROCESSOR_DATA_WIDTH / 2)

		self.preNoteOffset = 0
		self.peakIndex = 0
		self.peakValue = 0
		self.maxValue = 0
		self.preNoteValue = 0
		self.offTuneIndex = 0
		self.manager = manager
		self.previousLoudness = 0
		self.processingIndex = 0
		self.maxFrequencyIndex = len(ColumnProcessor.data[0])

	def resetPeak(self):
		self.firstIndex -= self.offTuneIndex
		self.lastIndex -= self.offTuneIndex
		if self.offTuneIndex != 0:
			if self.offTuneIndex < 0:
				for i in range(self.lastIndex + self.offTuneIndex + 1, self.lastIndex + 1):
					self.propagateUpColumn(i)
			else:
				for i in range(self.firstIndex, self.firstIndex + self.offTuneIndex):
					self.propagateUpColumn(i)

		self.preNoteOffset = 0
		self.peakIndex = 0
		self.peakValue = 0
		self.maxValue = 0
		self.preNoteValue = 0
		self.offTuneIndex = 0

	# This function is vaguely based on Jenks Natural Breaks Optimization.
	# We make many simplifications here:
	# 1. There are always 3 classes, the pre-note class, the note class, and the post-note class.
	# 2. The pre-note end index will be one of the first 3 values, since having arrived at this stage in the
	# code implies that the peak is within the first 3 values.
	# 3. An exhaustive search will then be made to find the start index of the post-note class.
	# arr is input array
	# Indices is start index of each class/group
	def getNaturalBreaks(self, arr):
		minVariance = -1
		preNoteIndex = 0
		middleIndex = max(4, int(len(arr) / 2))
		for i in range(0, 3):
			var1 = utils.getVariance(arr[0 : i + 1])
			var2 = utils.getVariance(arr[i + 1: middleIndex])
			if var2 + var1 < minVariance or minVariance < 0:
				minVariance = var1 + var2
				preNoteIndex = i + 1

		minVariance = -1
		postNoteIndex = 0
		for i in range(preNoteIndex, len(arr) - 1):
			var1 = utils.getVariance(arr[preNoteIndex : i + 1])
			var2 = utils.getVariance(arr[i + 1: len(arr)])
			if var2 + var1 < minVariance or minVariance < 0:
				minVariance = var1 + var2
				postNoteIndex = i + 1
		return preNoteIndex, postNoteIndex


	# This is very expensive but is acceptable since it processes on each real note.
	def getMoreAccurateIndices(self, startIndex, endIndex):
		sums = []
		for i in range(startIndex - 1, endIndex + 2):
			sums.append(sum(ColumnProcessor.data[i][self.firstIndex: self.lastIndex + 1]))
		# if self.note.name == "A4":
		# 	import pdb;pdb.set_trace()
		indices = self.getNaturalBreaks(sums)
		return indices[0] + startIndex - 1, indices[1] + startIndex - 1

	def getNoteMessage(self, startIndex, endIndex):
		# if self.note.name=="D5":
		# 	#if self.manager.globalIndex > 400:
		# 	print(self.manager.globalIndex)
		# 		#import pdb;pdb.set_trace()
		# TODO: make this check for short times instead
		if endIndex - startIndex < 5:	# Too short note implies anomoly.
			self.resetPeak()
			return Message(MessageType.NO_EVENT)
		else:
			startIndex, endIndex = self.getMoreAccurateIndices(startIndex, endIndex)
			if endIndex - startIndex < 5:	# Seems redudant but doing this saves a lot of time
				self.resetPeak()
				return Message(MessageType.NO_EVENT)
			absoluteLoudness = sum([
				sum(
					[ColumnProcessor.data[r][c] for c in range(self.firstIndex, self.lastIndex + 1)]
				) for r in range(startIndex, endIndex)
			]) / (endIndex - startIndex)
			# Add in magnitudes from harmonics
			originalCenter = (self.firstIndex + self.lastIndex) / 2
			for h in range(2, self.maxHarmonic + 1):
				centerIndex = int(originalCenter * h)
				if centerIndex >= self.maxFrequencyIndex:
					break
				firstIndex = centerIndex - int(ProcessConstants.COLUMN_PROCESSOR_DATA_WIDTH / 2)
				lastIndex = centerIndex + int(ProcessConstants.COLUMN_PROCESSOR_DATA_WIDTH / 2)
				for i in range(firstIndex, lastIndex + 1):
					self.propagateUpColumn(i)
				harmonicLoudness = sum([
					sum(
						[ColumnProcessor.data[r][c] for c in range(firstIndex, lastIndex + 1)]
					) for r in range(startIndex, endIndex)
				]) / (endIndex - startIndex)
				absoluteLoudness += harmonicLoudness
			self.resetPeak()
			if absoluteLoudness > self.previousLoudness or utils.percentDiff(absoluteLoudness, self.previousLoudness) < 0.3:
				self.previousLoudness = absoluteLoudness
			return NewNoteMessage(startIndex, endIndex, self.note, absoluteLoudness, self.centerIndex + self.offTuneIndex)

	def getColumnSum(self, columnIndex, propagateColumn=False):
		if propagateColumn:
			self.propagateUpColumn(columnIndex)
		return sum([ColumnProcessor.data[i][columnIndex] for i in range(self.peakIndex, self.processingIndex + 1)])

	def getSideColumnSums(self):
		leftColumnSum = sum([ColumnProcessor.data[i][self.firstIndex] for i in range(self.peakIndex, self.processingIndex + 1)])
		rightColumnSum = sum([ColumnProcessor.data[i][self.lastIndex] for i in range(self.peakIndex, self.processingIndex + 1)])
		return leftColumnSum, rightColumnSum

	def interpolateColumn(self, columnIndex):
		index = self.peakIndex
		for index in range(self.peakIndex, self.processingIndex):
			ColumnProcessor.data[index][columnIndex] = (ColumnProcessor.data[index][columnIndex - 1] + ColumnProcessor.data[index][columnIndex + 1]) / 2

		# We search down here
		index = self.processingIndex
		while index != ProcessConstants.MAX_BUFFER_SIZE:
			if ColumnProcessor.data[index][columnIndex] == 0:
				if ColumnProcessor.data[index][columnIndex - 1] > 0 and ColumnProcessor.data[index][columnIndex - 1] > 0:
					ColumnProcessor.data[index][columnIndex] = (ColumnProcessor.data[index][columnIndex - 1] + ColumnProcessor.data[index][columnIndex + 1]) / 2
				else:
					break
			else:
				break
			index += 1



	# This function currently vaguely checks the column sum.
	# However, if there was a shift, we should also see a triangle-like pattern. More consise check in theory.
	def tryOfftuneShift(self):
		shiftIndex = 0
		# Try left shift first
		rightColumnSum = self.getColumnSum(self.lastIndex)
		leftOverColumnSum = self.getColumnSum(self.firstIndex - 1, True)
		while leftOverColumnSum > rightColumnSum or leftOverColumnSum == 0:
			if leftOverColumnSum == 0:
				self.interpolateColumn(self.firstIndex - 1)
				leftOverColumnSum = self.getColumnSum(self.firstIndex - 1)
			if leftOverColumnSum - rightColumnSum > 0:
				shiftIndex -= 1
				self.firstIndex -= 1
				self.lastIndex -= 1
			else:
				break
			leftOverColumnSum = self.getColumnSum(self.firstIndex - 1, True)
			rightColumnSum = self.getColumnSum(self.lastIndex)
		if shiftIndex != 0:
			self.offTuneIndex += shiftIndex
			return True
		# Try right shift if not left shift
		leftColumnSum = self.getColumnSum(self.firstIndex)
		rightOverColumnSum = self.getColumnSum(self.lastIndex + 1, True)
		while rightOverColumnSum > leftColumnSum or rightOverColumnSum == 0:
			if rightOverColumnSum == 0:
				self.interpolateColumn(self.lastIndex + 1)
				rightOverColumnSum = self.getColumnSum(self.lastIndex + 1)
			if rightOverColumnSum - leftColumnSum > 0:
				shiftIndex += 1
				self.firstIndex += 1
				self.lastIndex += 1
			else:
				break
			rightOverColumnSum = self.getColumnSum(self.lastIndex + 1, True)
			leftColumnSum = self.getColumnSum(self.firstIndex)
		if shiftIndex != 0:
			self.offTuneIndex += shiftIndex
			return True
		return False

	# Checks if offtune shift is now too far from ideal frequency
	def checkNoteShift(self):
		if utils.percentDiff((self.firstIndex + self.lastIndex) / 2, self.centerIndex) > 0.02:
			return True
		return False


	def checkPeak(self, currentSum, referenceSum):
		if currentSum - referenceSum > ColumnProcessor.runningMaximum / 10 * ProcessConstants.COLUMN_PROCESSOR_DATA_WIDTH:
			if utils.percentDiff(currentSum, referenceSum) > 3:
				return True
		return False

	def checkEndPeak(self, currentIndex, currentSum):
		prevSum = sum([ColumnProcessor.data[currentIndex - 1][j] for j in range(self.firstIndex, self.lastIndex + 1)])
		if prevSum > currentSum and utils.percentDiff(prevSum, currentSum) > 1:
			prev1Sum = sum([ColumnProcessor.data[currentIndex - 2][j] for j in range(self.firstIndex, self.lastIndex + 1)])
			if utils.percentDiff(prevSum, prev1Sum) < 0.2:
				futureSum = sum([ColumnProcessor.data[currentIndex + 1][j] for j in range(self.firstIndex, self.lastIndex + 1)])
				if utils.percentDiff(currentSum, futureSum) < 0.2:
					return True

		return False



	def propagateUpNegativeRow(self):

		for j in range(self.firstIndex, self.lastIndex + 1):
			if ColumnProcessor.data[self.processingIndex][j] < 0:	# Propagate negative number up
				rIndex = self.processingIndex
				while rIndex > 0:
					rIndex -= 1
					if ColumnProcessor.data[rIndex][j] > -ColumnProcessor.data[self.processingIndex][j]:
						ColumnProcessor.data[rIndex][j] += ColumnProcessor.data[self.processingIndex][j]
						ColumnProcessor.data[self.processingIndex][j] = 0
						break
					else:
						ColumnProcessor.data[self.processingIndex][j] += ColumnProcessor.data[rIndex][j]
						ColumnProcessor.data[rIndex][j] = 0
				ColumnProcessor.data[self.processingIndex][j] = 0

	def propagateUpColumn(self, columnIndex):
		dataIndex = ProcessConstants.MAX_BUFFER_SIZE
		negativeCollector = 0
		while dataIndex >= self.peakIndex - 3 - self.preNoteOffset:
			dataIndex -= 1
			if ColumnProcessor.data[dataIndex][columnIndex] < 0:	# Propagate negative number up
				negativeCollector += ColumnProcessor.data[dataIndex][columnIndex]
				ColumnProcessor.data[dataIndex][columnIndex] = 0
			else:
				if negativeCollector < 0:
					if ColumnProcessor.data[dataIndex][columnIndex] > -negativeCollector:
						ColumnProcessor.data[dataIndex][columnIndex] += negativeCollector
						negativeCollector = 0
					else:
						negativeCollector += ColumnProcessor.data[dataIndex][columnIndex]
						ColumnProcessor.data[dataIndex][columnIndex] = 0

	# def getPreNoteValue(self):
	# 	a = sum(ColumnProcessor.data[self.peakIndex - 2 - self.preNoteOffset][self.firstIndex: self.lastIndex])
	# 	b = sum(ColumnProcessor.data[self.peakIndex - 1 - self.preNoteOffset][self.firstIndex: self.lastIndex])
	# 	c = sum(ColumnProcessor.data[self.peakIndex - self.preNoteOffset][self.firstIndex: self.lastIndex])
	# 	diffAB = b - a
	# 	diffBC = c - b
	# 	if diffAB < 0 or diffBC < 0:
	# 		return 9 * a / 10 + c / 10
	# 	if diff
	def checkPossibleMissedPeak(self, currentSum, currentIndex):
		if self.checkPeak(currentSum, self.peakValue):
			if self.checkPeak(currentSum, sum(ColumnProcessor.data[currentIndex - 8][self.firstIndex: self.lastIndex + 1])):
				return True
		return False


	# TODO: Really need to do more for these "eclipsed" shapes.
	# 1. Not really accounting for their harmonics. ie if some enough pixels are filled, harmonics are doubled.
	# 2. I dont really know if this approximation method is sufficient
	def fillComb(self):

		for j in range(self.firstIndex, self.lastIndex + 1):
			if ColumnProcessor.data[self.processingIndex][j] == 0:
				if ColumnProcessor.data[self.processingIndex][j - 1] > 0 and ColumnProcessor.data[self.processingIndex][j + 1] > 0:
					ColumnProcessor.data[self.processingIndex][j] = (ColumnProcessor.data[self.processingIndex][j - 1] + ColumnProcessor.data[self.processingIndex][j + 1]) / 2


	def processNewDataRow(self):
		# Manager class appends new data to deque so all relative indices are shifted down 1
		self.peakIndex -= 1
		# Buffer overflow. We would ideally have a longer buffer to account for longer notes. Currently we would have to discard this potential note.
		if self.peakIndex - self.preNoteOffset - 2 < 0:
			self.resetPeak()
			self.peakIndex -= 1
		self.processingIndex = ProcessConstants.MAX_BUFFER_SIZE - 1
		self.propagateUpNegativeRow()
		self.processingIndex = int(ProcessConstants.MAX_BUFFER_SIZE / 2)
		self.fillComb()

		row = ColumnProcessor.data[self.processingIndex][self.firstIndex: self.lastIndex + 1]
		initialSum = sum(row)
		referenceSum = sum(ColumnProcessor.data[self.processingIndex - 2][self.firstIndex: self.lastIndex + 1])
		if self.peakIndex < 0:
			# Look for new peak
			if self.checkPeak(initialSum, referenceSum):
				self.preNoteValue = referenceSum
				self.peakIndex = self.processingIndex
				self.peakValue = initialSum
				self.maxValue = self.peakValue
		else:
			if initialSum > self.maxValue:
				self.maxValue = initialSum
			# Look for possible new peak, and end of peak.
			# Criteria would be different than looking for fresh peak

			# TODO: This logic is very unstable because a fake peak could override a real one
			if initialSum > self.peakValue and utils.percentDiff(initialSum, self.peakValue) > 2:
				if self.checkPeak(initialSum, referenceSum):
					indexFromLastPeak = self.processingIndex - self.peakIndex
					if indexFromLastPeak <= 2:
						self.preNoteOffset += indexFromLastPeak
					else:
						self.preNoteValue = referenceSum
					self.peakIndex = self.processingIndex
					self.peakValue = initialSum
			temp = self.maxValue / 10 + 9 * self.preNoteValue / 10
			# if self.note.name=="A4":
			# 	import pdb;pdb.set_trace()
			if initialSum < temp or utils.percentDiff(initialSum, temp) < 0.2:
				# Possible it can still qualify as a peak if this is not true
				if self.tryOfftuneShift():
					if self.checkNoteShift():
						self.resetPeak()
						return Message(MessageType.NO_EVENT)
					self.peakValue = sum(ColumnProcessor.data[self.peakIndex][self.firstIndex: self.lastIndex + 1])
					self.preNoteValue = sum(ColumnProcessor.data[self.peakIndex - 2 - self.preNoteOffset][self.firstIndex: self.lastIndex + 1])	# TODO: Negative?
					# Check if it also satisfies note end after shift:
					temp = self.maxValue / 10 + 9 * self.preNoteValue / 10
					initialSum = sum(ColumnProcessor.data[self.processingIndex][self.firstIndex: self.lastIndex + 1])
					if initialSum < temp or utils.percentDiff(initialSum, temp) < 0.2:
						return self.getNoteMessage(self.peakIndex - self.preNoteOffset, self.processingIndex)
				else:
					return self.getNoteMessage(self.peakIndex - self.preNoteOffset, self.processingIndex)


		# if self.checkPossibleMissedPeak(referenceSum, self.processingIndex - 2):
		# 	if self.note.name == "F#5/Gb5":
		# 		if self.manager.globalIndex >= 330:
		# 			print (self.manager.globalIndex)
		# 	baseIndex = self.processingIndex
		# 	prevSum = initialSum
		# 	firstDerivatives = []
		# 	# In the case of a missed peak, we expect that there is a strictly non-decreasing climb from the base of the peak.
		# 	while baseIndex > 0:
		# 		baseIndex -= 1
		# 		currentSum = sum(ColumnProcessor.data[baseIndex][self.firstIndex: self.lastIndex])
		# 		if currentSum > prevSum:
		# 			break
		# 		firstDerivatives.append(prevSum - currentSum)
		# 		prevSum = currentSum
		# 	if self.checkPeak(initialSum, prevSum):
		# 		# If there is a big enough height for this "gradual peak", we decide where the base is 
		# 		# by looking for the biggest first derivative. Ofcourse, we give more weight to the elements
		# 		# closer to the base of the peak.
		# 		modifiedFD = [firstDerivatives[i] * i for i in range(len(firstDerivatives))]
		# 		trueBaseIndex = modifiedFD.index(max(modifiedFD))

		# 		self.preNoteValue = sum(ColumnProcessor.data[self.processingIndex - trueBaseIndex - 2][self.firstIndex: self.lastIndex])
		# 		self.peakIndex = self.processingIndex - trueBaseIndex
		# 		self.peakValue = initialSum
		# 		self.maxValue = self.peakValue

		# 		if self.note.name == "F#5/Gb5":
		# 			if self.manager.globalIndex >= 330:
		# 				print (self.manager.globalIndex)

		# 		#print (self.note.name)


		return Message(MessageType.NO_EVENT)





class ColumnManager:
	# Consider Moving these constants to more genric constants file
	NOTES_PER_OCTAVE = 12
	NEXT_NOTE_FREQUENCY = 1.05946309	# 12th root of 2

	def __init__(self, outOfTune, noteParser, sampleRate, samplesPerFrame, samplesPerInterval, maxHarmonic=6):
		self.globalIndex = 0 	# Index relative to start of global sample
		self.outOfTune = outOfTune
		self.sampleRate = sampleRate
		self.samplesPerInterval = samplesPerInterval
		self.columnProcessors = []
		self.activeNotes = []
		ColumnProcessor.data.extend([[0 for i in range(int(samplesPerFrame / 2))] for i in range(ProcessConstants.MAX_BUFFER_SIZE)])
		for note in noteParser.parseNotes():
			self.columnProcessors.append(
				ColumnProcessor(note, sampleRate, samplesPerFrame, note.frequency * outOfTune, maxHarmonic,  self)
			)

	def processNewDataRow(self, row):
		ColumnProcessor.data.append(row)
		ColumnProcessor.updateRunningMaximum(max(row))
		for i in range(len(self.columnProcessors)):
			message = self.columnProcessors[i].processNewDataRow()
			if message.messageType == MessageType.NEW_NOTE:
				globalIndexOffset = self.globalIndex - ProcessConstants.MAX_BUFFER_SIZE - 1
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

		# loudness filter
		self.activeNotes = [an for an in self.activeNotes if an.loudness > ActiveNote.MAX_LOUDNESS / 8]
		return self.activeNotes



class ContinuousNoteProcessor(AbstractNoteProcessor):
	def __init__(self, waveform, sampleRate, noteParser=None, shapeStrategy=None):
		super(ContinuousNoteProcessor, self).__init__(waveform, sampleRate, noteParser)

	def getOutOfTune(self):
		def getLocalMax(arr):
			localMax = []
			for i in range(1, len(arr) - 1):
				if arr[i] > arr[i - 1] and arr[i] > arr[i + 1]:
					localMax.append(i)
			return localMax

		referenceNoteCount = 6
		referenceDuration = self.sampleRate * 5
		referenceStartIndex = 10000
		referenceFFT = fft.fft(self.waveform[referenceStartIndex: referenceStartIndex + referenceDuration])
		referenceFFT = [abs(f) for f in referenceFFT][:int(len(referenceFFT) / 2)]

		localMax = getLocalMax(referenceFFT)
		localMax.sort(key=lambda x: -referenceFFT[x])

		i = 0
		existingNotes = []
		percentDiffs = []
		while len(existingNotes) <= referenceNoteCount * 2:
			index = localMax[i]
			i += 1
			frequency = index * self.sampleRate / referenceDuration
			closestNote, percentDiff = self.getClosestNote(frequency)
			if closestNote in existingNotes:
				continue
			existingNotes.append(closestNote)

			percentDiffs.append(percentDiff)

		iterations = len(existingNotes) - referenceNoteCount
		for i in range(referenceNoteCount):
			avg = sum(percentDiffs) / len(percentDiffs)
			percentDiffs.sort(key=lambda x: abs(x - avg))
			percentDiffs = percentDiffs[:-1]

		outOfTune = sum(percentDiffs) / len(percentDiffs)
		return outOfTune


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
			value = loudness / ProcessConstants.COLUMN_PROCESSOR_DATA_WIDTH
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
		# Superimpose all channels into one waveform.

		samplesPerInterval = 512
		intervalsPerFrame = 128

		trimFrames = 5

		d2Array = []
		samplesPerFrame = samplesPerInterval * intervalsPerFrame

		sampleIndex = 0
		# TODO: since waveform is the max space, this effectively almost doubles space requirement for this program
		# We can re-write paddedWaveform as wrapper around waveform if this becomes a problem
		# You know I just wish python ints didnt take 28 bytes
		paddedWaveform = [0 for i in range(samplesPerFrame - samplesPerInterval)]
		paddedWaveform.extend(self.waveform)

		outOfTune = self.getOutOfTune()
		columnManager = ColumnManager(outOfTune, self.noteParser, self.sampleRate, samplesPerFrame, samplesPerInterval)

		d2Array = []
		maxSample = len(paddedWaveform) - (2 * samplesPerFrame)
		counter = 0
		while sampleIndex <= maxSample:
			counter += 1
			print(counter)
			gc.collect()


			currentFFT = []
			prevFFT = [0 for i in range(int(samplesPerFrame / 2))]

			frameArray = []
			startingSampleIndex = sampleIndex
			for i in range(intervalsPerFrame):
				currentFFT = fft.fft(paddedWaveform[sampleIndex: sampleIndex + samplesPerFrame])[:int(samplesPerFrame / 2)]
				d2Row = [abs(currentFFT[j]) - abs(prevFFT[j]) for j in range(len(currentFFT))]
				#self.meldRow(d2Row, notesFoundInFrame)
				prevFFT = currentFFT
				sampleIndex += samplesPerInterval

				if i >= trimFrames and i < intervalsPerFrame - trimFrames:
					#d2Array.append(d2Row[:2000])
					columnManager.processNewDataRow(d2Row)
			sampleIndex -= samplesPerInterval * trimFrames * 2
			for i in range(max(sampleIndex, startingSampleIndex + samplesPerFrame - samplesPerInterval) , sampleIndex + samplesPerFrame - samplesPerInterval):
				paddedWaveform[i] = 0

		for i in range(ProcessConstants.MAX_BUFFER_SIZE):
			columnManager.processNewDataRow([0 for i in range(len(currentFFT))])

		# for columnIndex in range(len(d2Array[0])):
		# 	dataIndex = len(d2Array)
		# 	negativeCollector = 0
		# 	while dataIndex > 0:
		# 		dataIndex -= 1
		# 		if d2Array[dataIndex][columnIndex] < 0:	# Propagate negative number up
		# 			negativeCollector += d2Array[dataIndex][columnIndex]
		# 			d2Array[dataIndex][columnIndex] = 0
		# 		else:
		# 			if negativeCollector < 0:
		# 				if d2Array[dataIndex][columnIndex] > -negativeCollector:
		# 					d2Array[dataIndex][columnIndex] += negativeCollector
		# 					negativeCollector = 0
		# 				else:
		# 					negativeCollector += d2Array[dataIndex][columnIndex]
		# 					d2Array[dataIndex][columnIndex] = 0
		# utils.d2Plot(d2Array, "out/continous2.png", widthCompression=100, heightCompression=10)

		return columnManager.getActiveNotes()
