from collections import defaultdict
from numpy import fft

from activeNote import ActiveNote
from noteProcessors.abstractNoteProcessor import AbstractNoteProcessor
from noteProcessors.discreteNoteProcessor.baseShapeStrategy import BaseShapeStrategy
from noteProcessors.discreteNoteProcessor.shapeStrategies import FilterShapeStrategy
import utils



# An interval property holds information regarding a segment of data samples,
# including the fourier transform and the time it corresponds to.
class IntervalProperty:
	def __init__(self, fourierTransform):
		self.fourierTransform = fourierTransform
		self.startTime = None
		self.endTime = None

	def setTimeRange(self, startTime, endTime):
		self.startTime = startTime
		self.endTime = endTime


# This note processor strategy uses a non-continuous way to find notes.
# The original sound samples are split into numerous time-chunks.
# Frequency is calculated within each time chunk and visualised/analysed using a 2d array.
# The analysis/processing strategy within the 2d array is isolated in class ShapeStrategy

class DiscreteNoteProcessor(AbstractNoteProcessor):
	def __init__(self, waveform, sampleRate, noteParser=None, shapeStrategy=None):
		super(DiscreteNoteProcessor, self).__init__(waveform, sampleRate, noteParser)

		# Number of intervals per second
		# Too high means inaccurate perceived frequencies, too low means inacurate time periods
		# Ideally, this should come from a beat processor because it could improve accuracy.
		self.intervalsPerSecond = 20
		self.offset = 0
		# Idea 2: we can do 2 passes, one with low intervalsPerSecond and one with high intervalsPerSecond and 
		# it could give us better time and frequency precision

		self.samplesPerInterval = int(self.sampleRate / self.intervalsPerSecond)	# Note that intervalsPerSecond is approximate value
		self.shapeStrategy = shapeStrategy(self.sampleRate, self.samplesPerInterval) or FilterShapeStrategy(self.sampleRate, self.samplesPerInterval)





	# Here we want to do some filtering based off the shape list.
	def getActiveNotesFromShapeList(self, shapeList):
		activeNotes = []
		largestMagnitude = max([s.magnitude for s in shapeList])
		for shape in shapeList:
			frequency = shape.centerOfMass * self.sampleRate / self.samplesPerInterval
			closestNote, diffPercent = self.getClosestNote(frequency)

			# Creates a note with start and end times. Loudness is approximated here.
			# TODO: Find the exact relation between loudness & velocity of note (as used by midi files)
			a = ActiveNote(closestNote, 
				shape.timeIndexStart * self.samplesPerInterval / self.sampleRate, 
				shape.timeIndexEnd * self.samplesPerInterval / self.sampleRate, 
				(shape.magnitude ** 0.5 / largestMagnitude ** 0.5) * 100)
			activeNotes.append(a)

		return activeNotes


	def getIntervalProperty(self, interval):
		return IntervalProperty(fft.fft(interval))

	def getIntervalPropertyList(self, waveform):
		# Split entire waveform into several "intervals" by time.
		intervalPropertyList = []
		for i in range(0, int(len(waveform) / self.samplesPerInterval)):
			startIndex = i * self.samplesPerInterval
			endIndex = (i + 1) * self.samplesPerInterval
			intervalProperty = self.getIntervalProperty(waveform[startIndex : endIndex])
			intervalProperty.setTimeRange(startIndex / self.sampleRate, endIndex / self.sampleRate)
			intervalPropertyList.append(intervalProperty)

		return intervalPropertyList


	def getActiveNotesFromIntervalPropertyList(self, intervalPropertyList):
		timeFrequencyArray = []
		for intervalProperty in intervalPropertyList:
			modifiedFourierTransform = [abs(a) for a in intervalProperty.fourierTransform][: self.samplesPerInterval // 2]
			timeFrequencyArray.append(modifiedFourierTransform)

		shapeList = self.shapeStrategy.getShapeList(timeFrequencyArray)

		# Debug plots.
		# values.png will store the 2dArray of the frequency values.
		# shape.png will store the filtered list of "shapes" from the original frequency vales.
		# A shape is a consecutive cluster of 2dArray elements that will be grouped into one note.
		utils.d2Plot(timeFrequencyArray, "out/values.png")
		shapeArray = [[0 for i in range(len(timeFrequencyArray[0]))] for j in range(len(timeFrequencyArray))]
		for shape in shapeList:
			if shape.isBaseCandidate:
				freq = int(round(shape.centerOfMass))
				for i in range(len(shape.magnitudeByTime)):
					if shapeArray[i + shape.timeIndexStart][freq] < shape.magnitudeByTime[i]:
						shapeArray[i + shape.timeIndexStart][freq] = shape.magnitudeByTime[i]
		utils.d2Plot(shapeArray, "out/shape.png")

		activeNotes = self.getActiveNotesFromShapeList(shapeList)
		return activeNotes

	def run(self):
		# Superimpose all channels into one waveform.
		sampleOffset = round(self.sampleRate * self.offset)
		intervalPropertyList = self.getIntervalPropertyList(self.waveform[sampleOffset:])
		return self.getActiveNotesFromIntervalPropertyList(intervalPropertyList)
