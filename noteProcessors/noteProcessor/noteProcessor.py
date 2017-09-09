from numpy import fft
from noteParser import NoteParser
from activeNote import ActiveNote
from collections import defaultdict
from noteProcessors.noteProcessor.shapeStrategies import ShapeStrategy1, ShapeStrategy2

import random

class IntervalProperty:
	def __init__(self, fourierTransform, dataPoints):
		self.fourierTransform = fourierTransform
		self.dataPoints = dataPoints
		self.startTime = None
		self.endTime = None

	def setTimeRange(self, startTime, endTime):
		self.startTime = startTime
		self.endTime = endTime




class FourierDataPoint:

	def __init__(self, strength, frequency, index, noteList):
		self.strength = strength
		self.frequency = frequency
		self.index = index
		self.noteList = noteList
		self.closestNote = None
		self.diffPercent = None

	def getNote(self):
		if not (self.closestNote == None):
			return self.closestNote
		for i in range(1, len(self.noteList)):
			if self.frequency < self.noteList[i].frequency:
				break
		lowerNotePercent = self.frequency / self.noteList[i - 1].frequency
		higherNotePercent = self.noteList[i].frequency / self.frequency
		if lowerNotePercent < higherNotePercent:
			self.closestNote = self.noteList[i - 1]
			self.diffPercent = lowerNotePercent
		else:
			self.closestNote = self.noteList[i]
			self.diffPercent = higherNotePercent
		return self.closestNote

	def print(self):
		closestNote = self.getNote()
		print("Str: %f \tFreq: %f \t Index: %f \tNote: %s \t FreqDiff: %f" % (self.strength, self.frequency, self.index, closestNote.name, self.diffPercent))



class NoteProcessor:
	def __init__(self, waveforms, sampleRate, noteParser=None, shapeStrategy=None):
		self.waveforms = waveforms
		self.sampleRate = sampleRate
		noteParser = noteParser or NoteParser()
		self.noteList = noteParser.parseNotes()
		# Consider interval of some fundamental frequency of all notes, although this may not be integer
		self.intervalSize = 18.328	# Number of intervals per second
		self.samplesPerInterval = int(self.sampleRate / self.intervalSize)
		self.shapeStrategy = shapeStrategy or ShapeStrategy2(self.sampleRate, self.samplesPerInterval)
		# This should come from a beat processor, and then mutiply by integer until it is between 20 and 30.
		# Too high means inaccurate perceived frequencies, too low means inacurate time periods
		self.offset = 0.0188

	def getActiveNotesFromIntervalPropertyList(self, intervalPropertyList):
		activeNotes = []
		currentNotes = defaultdict(lambda: None)
		for intervalProperty in intervalPropertyList:
			removedKeys = []
			for key, currentNote in currentNotes.items():
				if key not in [p.getNote() for p in intervalProperty.dataPoints]:
					removedKeys.append(key)
					if currentNote["endTime"] - currentNote["startTime"] >= 0.01:
						a = ActiveNote(key, currentNote["startTime"], currentNote["endTime"], 50)
						activeNotes.append(a)
			for k in removedKeys:
				del currentNotes[k]


			for fourierDataPoint in intervalProperty.dataPoints:
				note = fourierDataPoint.getNote()
				if currentNotes[note] == None:
					if abs(1 - fourierDataPoint.diffPercent) <= 0.01:
						noteItem = {
							"startTime": intervalProperty.startTime,
							"endTime": intervalProperty.endTime
						}
						currentNotes[note] = noteItem
					else:
						del currentNotes[note]
				else:
					currentNotes[note]["endTime"] = intervalProperty.endTime
		return activeNotes #TODO move this once we do mutiple channels


	def d2Plot(self, d2Array, filename):
		import numpy as np
		import matplotlib.pyplot as plt

		d2Array = [a for a in d2Array]

		fig = plt.figure(figsize=(len(d2Array[0]) / 20, len(d2Array) / 20))

		ax = fig.add_subplot(111)
		ax.set_title('colorMap')
		plt.imshow(d2Array)
		ax.set_aspect('equal')

		cax = fig.add_axes([0.12, 0.1, 0.78, 0.8])
		cax.get_xaxis().set_visible(False)
		cax.get_yaxis().set_visible(False)
		cax.patch.set_alpha(0)
		cax.set_frame_on(False)
		plt.colorbar(orientation='vertical')
		plt.savefig(filename)
		#plt.show()


	def getClosestNote(self, frequency):
		closestNote = None
		diffPercent = None
		for i in range(1, len(self.noteList)):
			if frequency < self.noteList[i].frequency:
				break
		lowerNotePercent = frequency / self.noteList[i - 1].frequency
		higherNotePercent = self.noteList[i].frequency / frequency
		if lowerNotePercent < higherNotePercent:
			closestNote = self.noteList[i - 1]
			diffPercent = lowerNotePercent
		else:
			closestNote = self.noteList[i]
			diffPercent = higherNotePercent
		return closestNote, diffPercent

	# Here we want to do some filtering based off the shape list.
	def getActiveNotesFromShapeList(self, shapeList):
		activeNotes = []
		largestMagnitude = max([s.magnitude for s in shapeList])
		for shape in shapeList:
			frequency = shape.centerOfMass * self.sampleRate / self.samplesPerInterval

			closestNote, diffPercent = self.getClosestNote(frequency)
			#TODO: the following is the same as getNote()

			import math
			if math.isnan((shape.magnitude ** 0.5 / largestMagnitude ** 0.5) * 100):
				import pdb;pdb.set_trace()
			a = ActiveNote(closestNote, 
				shape.timeIndexStart * self.samplesPerInterval / self.sampleRate, 
				shape.timeIndexEnd * self.samplesPerInterval / self.sampleRate, 
				(shape.magnitude ** 0.5 / largestMagnitude ** 0.5) * 100)
			activeNotes.append(a)


		return activeNotes #TODO move this once we do mutiple channels



	def getActiveNotesFromIntervalPropertyList2(self, intervalPropertyList):
		timePerUnit = intervalPropertyList[0].endTime - intervalPropertyList[0].startTime
		timeFrequencyArray = []
		for intervalProperty in intervalPropertyList:
			modifiedFourierTransform = [abs(a) for a in intervalProperty.fourierTransform][: self.samplesPerInterval // 2]
			timeFrequencyArray.append(modifiedFourierTransform)

		shapeList = self.shapeStrategy.getShapeList(timeFrequencyArray)
		self.d2Plot(timeFrequencyArray, "test/value.png")


		shapeArray3 = [[0 for i in range(len(timeFrequencyArray[0]))] for j in range(len(timeFrequencyArray))]
		for shape in shapeList:
			if shape.isBaseCandidate:
				freq = int(round(shape.centerOfMass))
				for i in range(len(shape.magnitudeByTime)):
					if shapeArray3[i + shape.timeIndexStart][freq] < shape.magnitudeByTime[i]:
						shapeArray3[i + shape.timeIndexStart][freq] = shape.magnitudeByTime[i]
		self.d2Plot(shapeArray3, "test/shape.png")

		# rowAverage = [sum(timeFrequencyArray[i]) / len(timeFrequencyArray[i]) for i in range(len(timeFrequencyArray))]
		# average = sum(rowAverage) / len(rowAverage)
		# averageArray = [[0 if timeFrequencyArray[i][j] > average else 100 for j in range(len(timeFrequencyArray[0]))] for i in range(len(timeFrequencyArray))]
		# self.d2Plot(averageArray, "avg.png")

		activeNotes = self.getActiveNotesFromShapeList(shapeList)


		return activeNotes #TODO move this once we do mutiple channels


	def run(self):
		for waveform in self.waveforms:
			sampleOffset = round(self.sampleRate * self.offset)
			intervalPropertyList = self.getIntervalPropertyList(waveform[sampleOffset:])
			return self.getActiveNotesFromIntervalPropertyList2(intervalPropertyList)

			# import pdb;pdb.set_trace()
			# [a.print() for a in intervalPropertyList[100].dataPoints]
			# visualiseArray(intervalPropertyList[100].fourierTransform, True)

	def getIntervalProperty(self, interval):
		def checkNeighbouringPoint(index, dataPoints):
			for data in dataPoints:
				if abs(index - data.index) <= 2:
					return False
			return True

		originalFourierTransform = fft.fft(interval)
		fourierTransform = [abs(float(a)) for a in originalFourierTransform][:len(interval) // 2]
		#visualiseArray(fourierTransform, True)
		dataPoints = []
		while(len(dataPoints) < 10):
			strength = max(fourierTransform)
			index = fourierTransform.index(strength)
			fourierTransform[index] = 0
			if index == 0:	# Zeroth index is not valid data points
				continue
			if checkNeighbouringPoint(index, dataPoints):
				dataPoints.append(FourierDataPoint(strength, index * self.sampleRate / len(interval), index, self.noteList))
			else:
				pass # TODO: we can strengthen the existing signal or something

		return IntervalProperty(originalFourierTransform, dataPoints)



	def getIntervalPropertyList(self, waveform):
		# Best intervalSize in Hz
		intervalPropertyList = []
		for i in range(0, int(len(waveform) / self.samplesPerInterval)):
			startIndex = i * self.samplesPerInterval
			endIndex = (i + 1) * self.samplesPerInterval
			intervalProperty = self.getIntervalProperty(waveform[startIndex : endIndex])
			intervalProperty.setTimeRange(startIndex / self.sampleRate, endIndex / self.sampleRate)
			intervalPropertyList.append(intervalProperty)

		return intervalPropertyList
