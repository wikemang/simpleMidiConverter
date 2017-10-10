from noteProcessors.continuousNoteProcessor.constants import Constants
from noteProcessors.continuousNoteProcessor.message import Message, MessageType, NewNoteMessage
import utils


# ColumnProcessor operates on the data of its manager.
# A few columns would be selected to process based on the frequency of the note assigned to this processor.

# Having access to the manager's buffer of data, this class operates on the data buffer sort of like an assembly line.
# At certain buffer indices, data is being processed and prepped for future operations.
class ColumnProcessor:
	def __init__(self, note, sampleRate, samplesPerFrame, modifiedFrequency, maxHarmonic, manager):
		self.note = note # Note this processor is associated with
		self.maxHarmonic = maxHarmonic # Maximum harmonic processor will look for

		self.centerIndex = int(round(modifiedFrequency * samplesPerFrame / sampleRate)) # Index frequency is centered on
		self.firstIndex = self.centerIndex - int(Constants.COLUMN_PROCESSOR_DATA_WIDTH / 2)	# First and last frequency index the processor operates on
		self.lastIndex = self.centerIndex + int(Constants.COLUMN_PROCESSOR_DATA_WIDTH / 2)
 
		self.peakIndex = 0 # row index a peak was detected at
		self.preNoteOffset = 0 # index offset of the start of the note from peak
		self.peakValue = 0 # Value of peak
		self.maxValue = 0 # maximum value detected since the first peak
		self.preNoteValue = 0 # value before the note is detected
		self.offTuneIndex = 0 # If the note is offtune, this is the shift from the origina firstIndex and lastIndex
		self.manager = manager # The manager where data comes from
		self.previousLoudness = 0 # loudness of the previous note detected using this processor
		self.processingIndex = 0 # Current row index that is being processed.
		self.maxFrequencyIndex = len(self.manager.data[0])

	# Resets all data relating to the peak value.
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
	# 1. There are always 3 classes: the pre-note class, the note class, and the post-note class.
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
			sums.append(sum(self.manager.data[i][self.firstIndex: self.lastIndex + 1]))
		indices = self.getNaturalBreaks(sums)
		return indices[0] + startIndex - 1, indices[1] + startIndex - 1

	def getNoteMessage(self, startIndex, endIndex):
		if endIndex - startIndex < Constants.MINIMAL_NOTE_LENGTH:	# Too short note implies anomoly.
			self.resetPeak()
			return Message(MessageType.NO_EVENT)
		else:
			startIndex, endIndex = self.getMoreAccurateIndices(startIndex, endIndex)
			if endIndex - startIndex < Constants.MINIMAL_NOTE_LENGTH:	# Seems redudant but doing this saves a lot of time
				self.resetPeak()
				return Message(MessageType.NO_EVENT)

			# Absolute loudness is the sum of all values in the current rectangle described by startIndex, endIndex,
			# firstIndex, and lastIndex, divided by the number of rows.
			absoluteLoudness = sum([
				sum(
					[self.manager.data[r][c] for c in range(self.firstIndex, self.lastIndex + 1)]
				) for r in range(startIndex, endIndex)
			]) / (endIndex - startIndex)

			# Add in magnitudes from harmonics
			originalCenter = (self.firstIndex + self.lastIndex) / 2
			for h in range(2, self.maxHarmonic + 1):
				centerIndex = int(originalCenter * h)
				if centerIndex >= self.maxFrequencyIndex:
					break
				firstIndex = centerIndex - int(Constants.COLUMN_PROCESSOR_DATA_WIDTH / 2)
				lastIndex = centerIndex + int(Constants.COLUMN_PROCESSOR_DATA_WIDTH / 2)
				for i in range(firstIndex, lastIndex + 1):
					self.propagateUpColumn(i)
				harmonicLoudness = sum([
					sum(
						[self.manager.data[r][c] for c in range(firstIndex, lastIndex + 1)]
					) for r in range(startIndex, endIndex)
				]) / (endIndex - startIndex)
				absoluteLoudness += harmonicLoudness
			self.resetPeak()
			# Update the preciousLoudness if this loudness is greater or similar in value
			if absoluteLoudness > self.previousLoudness or utils.percentDiff(absoluteLoudness, self.previousLoudness) < 0.3:
				self.previousLoudness = absoluteLoudness
			return NewNoteMessage(startIndex, endIndex, self.note, absoluteLoudness, self.centerIndex + self.offTuneIndex)

	# Sum a column
	def getColumnSum(self, columnIndex, propagateColumn=False):
		if propagateColumn:
			self.propagateUpColumn(columnIndex)
		return sum([self.manager.data[i][columnIndex] for i in range(self.peakIndex, self.processingIndex + 1)])

	# get the column sums at firstIndex and lastIndex
	def getSideColumnSums(self):
		leftColumnSum = self.getColumnSum(self.firstIndex)
		rightColumnSum = self.getColumnSum(self.lastIndex)
		return leftColumnSum, rightColumnSum

	# This function is called on a column if we want to erase the column's value and use interpolated values instead.
	# Should only be callued if the column is full of 0's
	def interpolateColumn(self, columnIndex):
		index = self.peakIndex
		for index in range(self.peakIndex, self.processingIndex):
			self.manager.data[index][columnIndex] = (self.manager.data[index][columnIndex - 1] + self.manager.data[index][columnIndex + 1]) / 2

		# We search down here
		index = self.processingIndex
		while index != Constants.MAX_BUFFER_SIZE:
			# We interpolate past the current processingIndex until the values become non-zero, indicating the values have 
			# become normal again
			if self.manager.data[index][columnIndex] == 0:
				if self.manager.data[index][columnIndex - 1] > 0 and self.manager.data[index][columnIndex - 1] > 0:
					self.manager.data[index][columnIndex] = (self.manager.data[index][columnIndex - 1] + self.manager.data[index][columnIndex + 1]) / 2
				else:
					break
			else:
				break
			index += 1



	# Attempts to detect a note's offtune amount and shift the firstIndex and lastIndex accordingly.
	# The function will check the column left of firstIndex and compare with column at lastIndex.
	# A swap is made if it is greater, indicating the center of the note is likely to the left.
	# Logic repeated with lastIndex
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

	# Checks if the currentSum dominates referenceSum
	def checkPeak(self, currentSum, referenceSum):
		if currentSum - referenceSum > self.manager.runningMaximum / 10 * Constants.COLUMN_PROCESSOR_DATA_WIDTH:
			if utils.percentDiff(currentSum, referenceSum) > 3:
				return True
		return False

	# Propagates negative values in the current row up the columns
	# The negative number will be pushed up, neutralising (sum to 0) values until it becomes 0.
	def propagateUpNegativeRow(self):

		for j in range(self.firstIndex, self.lastIndex + 1):
			if self.manager.data[self.processingIndex][j] < 0:	# Propagate negative number up
				rIndex = self.processingIndex
				while rIndex > 0:
					rIndex -= 1
					if self.manager.data[rIndex][j] > -self.manager.data[self.processingIndex][j]:
						self.manager.data[rIndex][j] += self.manager.data[self.processingIndex][j]
						self.manager.data[self.processingIndex][j] = 0
						break
					else:
						self.manager.data[self.processingIndex][j] += self.manager.data[rIndex][j]
						self.manager.data[rIndex][j] = 0
				self.manager.data[self.processingIndex][j] = 0

	# Similar to propageUpNegativeRow, but column based. 
	# Function will propagate up all negative values in the column
	def propagateUpColumn(self, columnIndex):
		dataIndex = Constants.MAX_BUFFER_SIZE
		negativeCollector = 0
		while dataIndex >= self.peakIndex - 3 - self.preNoteOffset:
			dataIndex -= 1
			if self.manager.data[dataIndex][columnIndex] < 0:	# Propagate negative number up
				negativeCollector += self.manager.data[dataIndex][columnIndex]
				self.manager.data[dataIndex][columnIndex] = 0
			else:
				if negativeCollector < 0:
					if self.manager.data[dataIndex][columnIndex] > -negativeCollector:
						self.manager.data[dataIndex][columnIndex] += negativeCollector
						negativeCollector = 0
					else:
						negativeCollector += self.manager.data[dataIndex][columnIndex]
						self.manager.data[dataIndex][columnIndex] = 0

	# Logic for detecting missed peaks. Under revision...
	def checkPossibleMissedPeak(self, currentSum, currentIndex):
		if self.checkPeak(currentSum, self.peakValue):
			if self.checkPeak(currentSum, sum(self.manager.data[currentIndex - 8][self.firstIndex: self.lastIndex + 1])):
				return True
		return False


	# This function accounts for the comb-like shapes that occur when two identical notes are present in the same frame
	# TODO: Really need to do more for these "eclipsed" shapes.
	# 1. Not really accounting for their harmonics. ie if some enough pixels are filled, harmonics are doubled.
	# 2. I dont really know if this approximation method is sufficient
	def fillComb(self):
		for j in range(self.firstIndex, self.lastIndex + 1):
			if self.manager.data[self.processingIndex][j] == 0:
				if self.manager.data[self.processingIndex][j - 1] > 0 and self.manager.data[self.processingIndex][j + 1] > 0:
					self.manager.data[self.processingIndex][j] = (self.manager.data[self.processingIndex][j - 1] + self.manager.data[self.processingIndex][j + 1]) / 2


	def processNewDataRow(self):
		# Manager class appends new data to deque so all relative indices are shifted down 1
		self.peakIndex -= 1
		# Buffer overflow. We would ideally have a longer buffer to account for longer notes. Currently we would have to discard this potential note.
		if self.peakIndex - self.preNoteOffset - 2 < 0:
			self.resetPeak()
			self.peakIndex -= 1
		# Propagate up the row upon data entry into buffer
		self.processingIndex = Constants.MAX_BUFFER_SIZE - 1
		self.propagateUpNegativeRow()
		# Further up the buffer, perform other processes...
		self.processingIndex = int(Constants.MAX_BUFFER_SIZE / 2)
		self.fillComb()

		row = self.manager.data[self.processingIndex][self.firstIndex: self.lastIndex + 1]
		initialSum = sum(row)
		referenceSum = sum(self.manager.data[self.processingIndex - 2][self.firstIndex: self.lastIndex + 1])
		# If there is no peak, look for a peak. Else look for the end of the peak.
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

			# TODO: This logic is somewhat unstable because a fake peak could override a real one
			if initialSum > self.peakValue and utils.percentDiff(initialSum, self.peakValue) > 2:
				if self.checkPeak(initialSum, referenceSum):
					indexFromLastPeak = self.processingIndex - self.peakIndex
					# If the 2 peaks are close, we shift the peakIndex only.
					if indexFromLastPeak <= 2:
						self.preNoteOffset += indexFromLastPeak
					else:
						self.preNoteValue = referenceSum
					self.peakIndex = self.processingIndex
					self.peakValue = initialSum
			cutOff = self.maxValue / 10 + 9 * self.preNoteValue / 10
			# Being lower than cutOff suggests a potential end of note
			if initialSum < cutOff or utils.percentDiff(initialSum, cutOff) < 0.2:
				# Check if note is offtune, which implies a possible longer duration
				if self.tryOfftuneShift():
					# If the note is offTune by a noticeable amount, it is discarded.
					# It should have been caught by another processor in this case.
					if self.checkNoteShift():
						self.resetPeak()
						return Message(MessageType.NO_EVENT)
					self.peakValue = sum(self.manager.data[self.peakIndex][self.firstIndex: self.lastIndex + 1])
					self.preNoteValue = sum(self.manager.data[self.peakIndex - 2 - self.preNoteOffset][self.firstIndex: self.lastIndex + 1])	# TODO: Negative?
					# Check if it also satisfies note end after shift:
					cutOff = self.maxValue / 10 + 9 * self.preNoteValue / 10
					initialSum = sum(self.manager.data[self.processingIndex][self.firstIndex: self.lastIndex + 1])
					if initialSum < cutOff or utils.percentDiff(initialSum, cutOff) < 0.2:
						return self.getNoteMessage(self.peakIndex - self.preNoteOffset, self.processingIndex)
				else:
					return self.getNoteMessage(self.peakIndex - self.preNoteOffset, self.processingIndex)

		# Im currently revising this logic, but something similar to it is greatly beneficial.
		# Essentially, current logic to check for peak may miss them.

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
		# 		currentSum = sum(self.manager.data[baseIndex][self.firstIndex: self.lastIndex])
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

		# 		self.preNoteValue = sum(self.manager.data[self.processingIndex - trueBaseIndex - 2][self.firstIndex: self.lastIndex])
		# 		self.peakIndex = self.processingIndex - trueBaseIndex
		# 		self.peakValue = initialSum
		# 		self.maxValue = self.peakValue


		return Message(MessageType.NO_EVENT)



