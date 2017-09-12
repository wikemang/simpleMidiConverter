from collections import defaultdict
import copy

from noteProcessors.noteProcessor.baseShapeStrategy import BaseShapeStrategy, FrequencyTimeShape
from utils import *

# The goal of this shape strategy is to filter down the huge set of shapes to only those which contributes to the main melody.
# To accomplish this, several heuristics are used and the main steps are as follows:
# 1. combination of harmonic frequencies to the base frequency
# 2. Filtering by some fraction of the global magnitude
# 3. combination of shapes in close proximity	(This is somewhat of a cleanup step for #4)
# 4. re-separation of shapes based on internal structure
# 5. Filtering out shapes whose values are bloated by false harmonics
class FilterShapeStrategy(BaseShapeStrategy):
	def getShapeList(self, d2Array):
		shapeList = super(FilterShapeStrategy, self).getShapeList(d2Array)
		shapeList.sort(key=lambda s: s.centerOfMass)
		for shape in shapeList:
			# Completely disregard any shape below the minimal precision. TODO: improve.
			# Ideally , the check should be < 50, which converts to the equivalent of where consecutive note frequencies are
			# 2 cells apart.
			if shape.centerOfMass < 20:
				shape.isBaseCandidate = False
			# The followng chunk looks for possible harmonics given a base shape, and tries to combine them into the base shape.
			if shape.isBaseCandidate:
				baseFrequencyIndex = shape.centerOfMass
				currentHarmonic = 2
				currentIndex = int(baseFrequencyIndex * currentHarmonic)	# Index of where to look for currentHarmonic in usedPointsCache
				while currentIndex < len(d2Array[0]) - 1:
					harmonicSearched = []	# List of harmonic shapes already searched by this shap
					for timeIndex in range(shape.timeIndexStart, shape.timeIndexEnd + 1):
						# We look for the harmonic in 2 adjacent cache locations, to allow for some error.
						for cache in [self.usedPointsCache[timeIndex][currentIndex], self.usedPointsCache[timeIndex][currentIndex + 1]]:
							if cache in harmonicSearched:
								continue
							for cachedShape in cache:
								harmonicSearched.append(cache)

								# Maybe we can make check more precise in frequency precision cases
								# It seems this value is critical so that if too low, harmonic frequencies dont get grouped
								# If too high, false harmonics are detected
								if percentDiff(cachedShape.centerOfMass / currentHarmonic, baseFrequencyIndex) < 0.015:
									# Get the time indices that are shared between the base and harmonic shapes.
									sharedStartIndex = max([shape.timeIndexStart, cachedShape.timeIndexStart])
									sharedEndIndex = min([shape.timeIndexEnd, cachedShape.timeIndexEnd])
									baseFrequencyMagnitude = sum(shape.magnitudeByTime[sharedStartIndex - shape.timeIndexStart : sharedEndIndex - shape.timeIndexStart])
									harmonicFrequencyMagnitude = sum(cachedShape.magnitudeByTime[sharedStartIndex - cachedShape.timeIndexStart : sharedEndIndex - cachedShape.timeIndexStart])
									# The base frequency must be sizable compared to the harmonic to be considered related.
									# TODO: This rule is somewhat unrealiable and requires more thinking
									if baseFrequencyMagnitude * (1 + currentHarmonic * 0.1) < harmonicFrequencyMagnitude:
										continue

									# Re-evaluate the base-candidacy of the harmonic shape
									cachedShape.updateBaseCandidate(sharedStartIndex, sharedEndIndex)
									shape.harmonicCount += 1

									# Combine the magnitudes by time
									for i in range(sharedStartIndex, sharedEndIndex + 1):
										shape.magnitudeByTime[i - shape.timeIndexStart] += cachedShape.magnitudeByTime[i - cachedShape.timeIndexStart]
									break	# One harmonic shape per cache


					currentHarmonic += 1
					currentIndex = int(baseFrequencyIndex * currentHarmonic)

		shapeList = self.consolidateShapeList(shapeList, d2Array)
		return shapeList

	# Filters the shapelist multiple times based on rules
	def consolidateShapeList(self, shapeList, d2Array):
		# Filters out non-candidate notes from shapeList
		newShapeList = []
		for shape in shapeList:
			if shape.isBaseCandidate:
				newShapeList.append(shape)
			else:
				for point in shape.points:
					self.usedPointsCache[point[0]][point[1]].remove(shape)
		shapeList = newShapeList
		print("Filtering Notes: %d " % len(shapeList))

		# Sets some arbitrary global thresholds that dictate what is audible and what is not.
		# In the future, the goal is to use both local and global measurements to determine this.
		maxMagnitudePerShape = [max(shape.magnitudeByTime) for shape in shapeList]
		maxMagnitudePerShape.sort(key=lambda x: -x)
		threshold = sum(maxMagnitudePerShape[50:150]) / 100
		# mag < lowRange: inaudible
		# lowRange < mag < mediumRange: conditionally audible
		lowRange = threshold / 16
		mediumRange = threshold / 4
		highRange = threshold / 2

		# Filters out inaudible notes
		newShapeList = []
		for shape in shapeList:
			if max(shape.magnitudeByTime) > lowRange:
				newShapeList.append(shape)
			else:
				for point in shape.points:
					self.usedPointsCache[point[0]][point[1]].remove(shape)
		shapeList = newShapeList
		print("Filtering Notes: %d " % len(shapeList))


		# Combine existing shapes that are consecutive in time, and share similar frequencies.
		shapeList.sort(key=lambda shape: shape.timeIndexStart)
		newShapeList = []
		for shape in shapeList:
			# Check if a point is in cache. If not, it was removed by earlier iteration of this so we do not add to newShapeList
			# Should be correct since this processes shapes top down
			if shape in self.usedPointsCache[shape.points[0][0]][shape.points[0][1]]:
				lookForConnection = True	# Set to true if a connecting shape is found, indicating that there could be more connecting shapes.
				while lookForConnection:
					possibleConnectingShapes = set([])
					cachePoints = set([])	# Caches containing possibleConnectingShapes
					lookForConnection = False
					# We will check each cache point below the ending points (including diagonals).
					for p in shape.getEndingPoints():
						if p[0] < len(d2Array) - 1:
							if p[1] > 1:
								cachePoints.add((p[0] + 1, p[1] - 1))
							cachePoints.add((p[0] + 1, p[1]))
							if p[1] < len(d2Array[0]) - 1:
								cachePoints.add((p[0] + 1, p[1] + 1))
					for cachePoint in cachePoints:
						possibleConnectingShapes.update(self.usedPointsCache[cachePoint[0]][cachePoint[1]])
					for connectingShape in possibleConnectingShapes:
						# Checks that the 2 shapes are consecutive in time, have similar centerOfMass, and 
						# the connecting magnitudeByTimes are similar
						if (shape.timeIndexEnd + 1 == connectingShape.timeIndexStart and
							percentDiff(connectingShape.centerOfMass, shape.centerOfMass) < 0.01 and
							percentDiff(shape.magnitudeByTime[-1], connectingShape.magnitudeByTime[0] < 0.5)):
						
							# Combine the 2 shapes into 1 shape by emptying connectingShape and unloading to shape
							points = copy.deepcopy(connectingShape.points)
							points.extend(shape.points)
							auxiliaryPoints = copy.deepcopy(connectingShape.auxiliaryPoints)
							auxiliaryPoints.extend(shape.auxiliaryPoints)

							timeIndices = [p[0] for p in points]
							start = min(timeIndices)
							end = max(timeIndices)
							# We transfer magnitudes to the new shape to preserve combined harmonics
							magnitudeToTransfer = shape.magnitudeByTime[start - shape.timeIndexStart :]
							magnitudeToTransfer.extend(connectingShape.magnitudeByTime[: end - connectingShape.timeIndexStart + 1])
							if sum(magnitudeToTransfer) < 0:
								magnitudeToTransfer = [0 for m in magnitudeToTransfer]
							shape = FrequencyTimeShape(points, auxiliaryPoints, d2Array, magnitudeToTransfer)
							# Remove the connecting shape from cache
							for cp in connectingShape.points:
								self.usedPointsCache[cp[0]][cp[1]].remove(connectingShape)
								self.usedPointsCache[cp[0]][cp[1]].append(shape)
							lookForConnection = True
							break
				newShapeList.append(shape)
		shapeList = newShapeList
		print("Filtering Notes: %d " % len(shapeList))

		shapeList.sort(key=lambda shape: shape.magnitude)
		# Evaluate each shape internally and remove all uneeded points
		self.usedPointsCache = [[[] for i in range(len(d2Array[0]))] for i in range(len(d2Array))]
		newShapeList = []
		for shape in shapeList:
			for i in range(len(shape.magnitudeByTime)):
				# LowRange is inaudible
				if shape.magnitudeByTime[i] < lowRange:
					shape.magnitudeByTime[i] = -1
				# Between medium and high range, the note is audible if it is at the end of a shape.
				if shape.magnitudeByTime[i] >= lowRange and shape.magnitudeByTime[i] < mediumRange:
					isPoint = False
					if (i == len(shape.magnitudeByTime) - 1 and
						len(shape.magnitudeByTime) != 1 and
						shape.magnitudeByTime[i - 1] >= mediumRange and 
						percentDiff(shape.magnitudeByTime[i - 1], shape.magnitudeByTime[i]) > 0.2):
						isPoint = True
					if (i == 0 and 
						len(shape.magnitudeByTime) != 1 and
						shape.magnitudeByTime[i + 1] >= mediumRange and 
						percentDiff(shape.magnitudeByTime[i + 1], shape.magnitudeByTime[i]) > 0.2):
						isPoint = True
					if not isPoint:
						shape.magnitudeByTime[i] = -1
			points = []
			auxiliaryPoints = []
			# Separate the shapes based off the "-1"s
			for i in range(len(shape.magnitudeByTime) + 1):
				if i == len(shape.magnitudeByTime) or shape.magnitudeByTime[i] < 0:
					if points:
						timeIndices = [p[0] for p in points]
						start = min(timeIndices)
						end = max(timeIndices)
						s = FrequencyTimeShape(points, auxiliaryPoints, d2Array, shape.magnitudeByTime[start - shape.timeIndexStart : end - shape.timeIndexStart + 1])
						# Im assumming that the shapes that are split and dont satisfy this are irrelevant.
						# Could possibly be that earlier logic didnt group shape properly.
						if s.magnitude > 0:
							newShapeList.append(s)
							for p in s.points:
								self.usedPointsCache[p[0]][p[1]].append(s)
						points = []
						auxiliaryPoints = []
				else:
					points.extend([p for p in shape.points if p[0] == i + shape.timeIndexStart])
					auxiliaryPoints.extend([p for p in shape.auxiliaryPoints if p[0] == i + shape.timeIndexStart])
		shapeList = newShapeList
		print("Filtering Notes: %d " % len(shapeList))


		# Evaluate each shape relative to time-local information.
		newShapeList = []
		for shape in shapeList:			
			# Rule 1:
			# If there is a higher harmonic that is a lot louder than this shape, it is safe to assume
			# that this shape stole some of the higher harmonic's harmonics. The loudness logic is present
			# in the part that combines the harmonics
			coveredByHarmonic = False
			allPossibleHarmonics = set([])
			currentHarmonic = 2
			currentIndex = int(shape.centerOfMass * currentHarmonic)
			while currentIndex < len(d2Array[0]) - 1:
				for timeIndex in range(shape.timeIndexStart, shape.timeIndexEnd + 1):
					for cache in [self.usedPointsCache[timeIndex][currentIndex], self.usedPointsCache[timeIndex][currentIndex + 1]]:
						for cachedShape in cache:
							# The chance of higher harmonics being the victim is lower
							if percentDiff(cachedShape.centerOfMass / currentHarmonic, shape.centerOfMass) < (5 - currentHarmonic) * 0.005 + 0.015:
								allPossibleHarmonics.add(cachedShape)
				currentHarmonic += 1
				currentIndex = int(shape.centerOfMass * currentHarmonic)

			for harmonic in allPossibleHarmonics:
				sharedStartIndex = max([shape.timeIndexStart, harmonic.timeIndexStart])
				sharedEndIndex = min([shape.timeIndexEnd, harmonic.timeIndexEnd])
				# If the sum of the covered portion of the shape is bigger than half the total shape
				if sum(shape.magnitudeByTime[sharedStartIndex - shape.timeIndexStart : sharedEndIndex - shape.timeIndexStart + 1]) * 2 > sum(shape.magnitudeByTime):
					coveredByHarmonic = True
			coveredByNearbyNote = False
			# Rule 2:
			# If nearby note covers this one, we also take it out
			# You are covered if your fundamental frequency is significantly smaller.

			# startIndex = shape.timeIndexStart
			# firstMagnitude = shape.magnitudeByTime[0]
			# if len(shape.magnitudeByTime) > 1 and shape.magnitudeByTime[1] > shape.magnitudeByTime[0]:
			# 	startIndex += 1
			# 	firstMagnitude = shape.magnitudeByTime[1]
			# possibleShapes = set([])
			# for i in range(len(d2Array[0])):
			# 	possibleShapes.update(self.usedPointsCache[startIndex][i])
			# for possibleShape in possibleShapes:
			# 	if possibleShape != shape:
			# 		if possibleShape.magnitudeByTime[startIndex - possibleShape.timeIndexStart] / firstMagnitude > 1.2:
			# 			coveredByNearbyNote = True
			if not (coveredByHarmonic or coveredByNearbyNote):
				newShapeList.append(shape)
			else:
				for p in shape.points:
					self.usedPointsCache[p[0]][p[1]].remove(shape)
		shapeList = newShapeList
		print("Filtering Notes: %d " % len(shapeList))
				
		return shapeList

