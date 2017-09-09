from collections import defaultdict
import copy

from utils import *


class FrequencyTimeShape:
	def __init__(self, points, frequencyTimeArray):
		self.points = points
		self.centerOfMass = None
		self.magnitude = None
		self.timeIndexStart = None 
		self.timeIndexEnd = None
		self.noteCount = 0
		self.calculateProperties(frequencyTimeArray)

	# Center of mass is calculated for the x axis only, and is used to approximate frequency.
	# Magnitude is a somewhat arbitrary quantity used to approximate loudness
	def calculateProperties(self, frequencyTimeArray):
		self.cutTail()

		totalMagnitude = 0
		weightedMagnitude = 0
		for p in self.points:
			weightedMagnitude += p[1] * frequencyTimeArray[p[0]][p[1]]
			totalMagnitude += frequencyTimeArray[p[0]][p[1]]

		self.centerOfMass = weightedMagnitude / totalMagnitude
		self.magnitude = totalMagnitude

	# The purpose of this function is to cut trailing echos of a note
	def cutTail(self):
		timeIndices = [p[0] for p in self.points]
		self.timeIndexStart = min(timeIndices)
		self.timeIndexEnd = max(timeIndices)
		# TODO: cut the tail

	def print(self):
		print("com: %s" % self.centerOfMass)
		print("index: %d - %d" % (self.timeIndexStart, self.timeIndexEnd))
		print(self.magnitudeByTime)

class HarmonicShape(FrequencyTimeShape):
	def __init__(self, points, auxiliaryPoints, frequencyTimeArray, magnitudeByTime=[]):
		self.auxiliaryPoints = auxiliaryPoints
		self.isBaseCandidate = True
		self.usedAsHarmonic = []
		self.harmonicCount = 0
		self.magnitudeByTime = magnitudeByTime
		self.reconsolidatedShape = False
		if self.magnitudeByTime:
			self.reconsolidatedShape = True
		super(HarmonicShape, self).__init__(points, frequencyTimeArray)

	# def calculateProperties(self, frequencyTimeArray):
	# 	self.cutTail()
	# 	if not self.reconsolidatedShape:
	# 		self.magnitudeByTime = [0 for i in range(self.timeIndexStart, self.timeIndexEnd + 1)]
	# 	self.usedAsHarmonic = [False for i in range(self.timeIndexStart, self.timeIndexEnd + 1)]

	# 	totalMagnitude = 0
	# 	weightedMagnitude = 0
	# 	auxMap = None
	# 	if self.auxiliaryPoints[0][1] <= 1 or self.auxiliaryPoints[0][1] >= len(frequencyTimeArray[0]) - 1:
	# 		auxMap = {y : 0 for (y, x) in self.auxiliaryPoints}
	# 	else:
	# 		auxMap = {y : frequencyTimeArray[y][x] for (y, x) in self.auxiliaryPoints}
	# 	for p in self.points:
	# 		# We reduce the magnitude of each column by what we think is the noise
	# 		magnitude = frequencyTimeArray[p[0]][p[1]] - auxMap[p[0]]
	# 		weightedMagnitude += p[1] * magnitude 
	# 		totalMagnitude += magnitude
	# 		if not self.reconsolidatedShape:
	# 			self.magnitudeByTime[p[0] - self.timeIndexStart] += magnitude


	# 	self.centerOfMass = weightedMagnitude / totalMagnitude
	# 	self.magnitude = sum(self.magnitudeByTime) / len(self.magnitudeByTime)

	def calculateProperties(self, frequencyTimeArray):
		self.cutTail()
		if not self.reconsolidatedShape:
			self.magnitudeByTime = [0 for i in range(self.timeIndexStart, self.timeIndexEnd + 1)]
		self.usedAsHarmonic = [False for i in range(self.timeIndexStart, self.timeIndexEnd + 1)]

		totalMagnitude = 0
		weightedMagnitude = 0
		auxMap = None
		self.points.extend(self.auxiliaryPoints)
		for p in self.points:
			# We reduce the magnitude of each column by what we think is the noise
			magnitude = frequencyTimeArray[p[0]][p[1]]
			weightedMagnitude += p[1] * magnitude 
			totalMagnitude += magnitude
			if not self.reconsolidatedShape:
				self.magnitudeByTime[p[0] - self.timeIndexStart] += magnitude


		self.centerOfMass = weightedMagnitude / totalMagnitude
		self.magnitude = sum(self.magnitudeByTime) / len(self.magnitudeByTime)

	def updateBaseCandidate(self, startIndex, endIndex):
		for i in range(startIndex, endIndex + 1):
			self.usedAsHarmonic[i - self.timeIndexStart] = True
		if len(self.usedAsHarmonic) < len([x for x in self.usedAsHarmonic if x == True]) * 2:
			self.isBaseCandidate = False

	def getEndingPoints(self):
		return [p for p in self.points if p[0] == self.timeIndexEnd]





class BaseShapeStrategy:
	def get2dLocalMaxima(self, d2Array):
		maxima = []
		for i in range(1, len(d2Array) - 1):
			for j in range(1, len(d2Array[0]) - 1):
				if (d2Array[i][j] > d2Array[i - 1][j] and 
				d2Array[i][j] > d2Array[i + 1][j] and 
				d2Array[i][j] > d2Array[i][j - 1] and 
				d2Array[i][j] > d2Array[i][j + 1] and 
				d2Array[i][j] > d2Array[i - 1][j - 1] and 
				d2Array[i][j] > d2Array[i - 1][j + 1] and 
				d2Array[i][j] > d2Array[i + 1][j - 1] and 
				d2Array[i][j] > d2Array[i + 1][j + 1]):
					maxima.append((i, j))
		return maxima

	# filterIntensity is percent of max magnitude to be used as filtering criteria
	def filter2dLocalMaximaByMagnitude(self, d2Array, localMaxima, filterIntensity):
		largestMagnitude = max([d2Array[m[0]][m[1]] for m in localMaxima])
		filteredByMagnitude = [m for m in localMaxima if d2Array[m[0]][m[1]] > largestMagnitude / filterIntensity]
		return filteredByMagnitude

	def getAverageD2array(self, d2Array):
		rowAverage = [sum(d2Array[i]) / len(d2Array[i]) for i in range(len(d2Array))]
		average = sum(rowAverage) / len(rowAverage)
		return average

	def filter2dLocalMaximaByThreshhold(self, d2Array, localMaxima, threshold):
		filteredByMagnitude = [m for m in localMaxima if d2Array[m[0]][m[1]] > threshold]
		return filteredByMagnitude


	def getShapeList(self):
		return None



# The steps of this shape strategy are as follows:
# 1. Filter all local maximum with some fraction of the global max
# 2. call getShape for each local max not yet in a shape
# 3. getShape searches all for corners for value greater than fraction of running average
# 4. attempt to split the shape into multiple shapes based on frequencies (currently just 2)
class ShapeStrategy1(BaseShapeStrategy):
	def getShape(self, point, d2Array, usedPointsSet):
		runningAverage = 0
		points = []
		pointQueue = []
		processedSet = copy.deepcopy(usedPointsSet)

		# Ideally we want do not want to limit the number of points with a hardcoded threshold
		while d2Array[point[0]][point[1]] ** 0.5 > (runningAverage ** 0.5) / 1.5 and not len(points) > 100:
			points.append(point)

			lenPoints = len(points)
			runningAverage = sum([d2Array[i][j] for (i, j) in points]) / lenPoints

			newPoints = [(point[0] - 1, point[1]), 
				(point[0], point[1] + 1), 
				(point[0] + 1, point[1]), 
				(point[0], point[1] - 1)]
			newPoints = [p for p in newPoints if p[0] >= 0 and 
												p[1] >= 1 and 
												p[0] < len(d2Array) and
												p[1] < len(d2Array[0]) and
												p not in processedSet]
			pointQueue.extend(newPoints)
			processedSet.update(newPoints)

			valueList = [d2Array[i][j] for (i, j) in pointQueue]
			maxValue = max(valueList)
			point = pointQueue.pop(valueList.index(maxValue))

		return points


	def getLocalMax(self, arr):
		localMaxima = []
		for i in range(0, len(arr)):
			if i != 0 and arr[i] < arr[i - 1]:
				continue
			if i != len(arr) - 1 and arr[i] < arr[i + 1]:
				continue
			localMaxima.append(arr[i])
		return localMaxima


	# This function is responsible for splitting shapes by frequencies in case they got glued into 1 shape
	# This function knows where the frequencies should lie and simply assign points to one of the 2 groups by index.
	# points lying in the middle belongs to the group that has higher adjacent value.
	def splitShape(self, points, d2Array):

		pointsArrays = []
		points.sort(key=lambda x: x[0])
		timeIndex = points[0][0]
		centerOfMasses = []

		totalMagnitude = 0
		weightedMagnitude = 0
		for point in points:
			if point[0] != timeIndex:
				centerOfMass = weightedMagnitude / totalMagnitude
				centerOfMasses.append(centerOfMass)
				timeIndex += 1
				weightedMagnitude = 0
				totalMagnitude = 0
			weightedMagnitude += point[1] * d2Array[point[0]][point[1]]
			totalMagnitude += d2Array[point[0]][point[1]]
		centerOfMass = weightedMagnitude / totalMagnitude
		centerOfMasses.append(centerOfMass)

		pointsPerNote = defaultdict(lambda: None)

		frequencyIndex = centerOfMasses[0]
		shapeCount = 1
		for com in centerOfMasses:
			# Check if ratio of frequencies is greater than 5%. This is approximate and not symmetrical, could fix.
			# The frequency ratio for successive notes is 6%
			if abs(1 - com / frequencyIndex) >= 0.05:
				shapeCount += 1
				break # TODO: This section needs to be more robust, accounting for more than 2 notes as well as simultaneous notes

		if shapeCount > 1:
			# Find the maximum from the left side and the right side.
			# The lowest column in between these 2 is where we do the split
			index = min([p[1] for p in points])
			maxIndex = max([p[1] for p in points])
			columnSums = []
			for i in range(index, maxIndex + 1):
				columnSums.append(sum([d2Array[p[0]][p[1]] for p in points if p[1] == i]))
			leftMaxIndex = 0
			rightMaxIndex = 0
			localMaxima = self.getLocalMax(columnSums)
			if len(localMaxima) == 1:	#TODO: THis is inefficient, should be caught by shapecount
				return [points]
			m1 = columnSums.index(max(localMaxima))
			localMaxima[localMaxima.index(max(localMaxima))] = 0
			m2 = columnSums.index(max(localMaxima))
			if m1 < m2:
				leftMaxIndex = m1
				rightMaxIndex = m2
			else:
				leftMaxIndex = m2
				rightMaxIndex = m1
			minColumn = columnSums.index(min(columnSums[leftMaxIndex: rightMaxIndex + 1])) + index

			points1 = [p for p in points if p[1] < minColumn]
			points2 = [p for p in points if p[1] > minColumn]
			
			return [points1, points2]

		else:
			return [points]


	# Return list of FrequencyTimeShape.
	# A shape can represent successive notes by frequencies or successive notes by time
	def getShapeList(self, d2Array):
		localMaxima = self.get2dLocalMaxima(d2Array)
		localMaxima = self.filter2dLocalMaximaByMagnitude(d2Array, localMaxima, 8)


		shapeList = []
		usedPointsCache = [[False for i in range(len(d2Array[0]))] for i in range(len(d2Array))]
		usedPointsSet = set([])

		for lm in localMaxima:
			if usedPointsCache[lm[0]][lm[1]]:
				continue
			points = self.getShape(lm, d2Array, usedPointsSet)
			#import pdb;pdb.set_trace()

			for point in points:
				usedPointsCache[point[0]][point[1]] = True
				usedPointsSet.add(point)

			for p in self.splitShape(points, d2Array):
				shape = FrequencyTimeShape(p, d2Array)
				shapeList.append(shape)


		return shapeList



class ShapeStrategy2(BaseShapeStrategy):

	#TODO: remove if uneeded
	def __init__(self, sampleRate, intervalLength):
		self.sampleRate = sampleRate
		self.intervalLength = intervalLength

	# def filter2dLocalMaximaByMagnitude(self, d2Array, localMaxima, filterIntensity):
	# 	return super(ShapeStrategy2, self).filter2dLocalMaximaByMagnitude(d2Array, localMaxima, filterIntensity)

	def getShape(self, lm, d2Array, usedPointsCache):
		points = [lm]
		# Search down
		y, x = lm
		currentValue = d2Array[y][x]
		lmValue = currentValue
		halfCache = 0
		increment = 1.41
		# if lm == (743, 142):
		# 	d2Array[743][142] += 10000000
		# 	#import pdb;pdb.set_trace()
		while True:
			y += 1
			if y >= len(d2Array):
				break
			newValue = d2Array[y][x]
			if halfCache != 0 and currentValue < halfCache / increment: # Conditional end of current shape
				break
			if newValue < currentValue / (increment ** 2): # End of current shape
				break
			if newValue < currentValue / increment: # Conditional end of current shape
				if halfCache != 0:
					break
				halfCache = newValue
			if newValue > currentValue * increment:	# New Shape
				break
			if newValue < lmValue / (increment ** 3):	# End of shape, too much decay?
				break
			# Between 1/2 and 2 of the currentValue is a valid shape point
			points.append((y, x))
			currentValue = newValue
		# Search up
		y, x = lm
		currentValue = d2Array[y][x]
		halfCache = 0
		while True:
			y -= 1
			if y < 0:
				break
			if usedPointsCache[y][x] != []:
				break
			newValue = d2Array[y][x]
			if newValue < currentValue / 2:
				break
			points.append((y, x))
			currentValue = newValue
			# Anything bigger than currentValue would've been part of a lm that was scanned down.
			# The edge case is if the scanned down shape is discarded due to a dominant adjacent frequency.
			# However, in this case, we expect that the adjacent frequency will still be dominating and this shape will likely
			# be discarded again

		# Sum the points in the current column and the left and right adjacent columns
		currentColumnSum = sum([d2Array[y][x] for (y, x) in points])
		rightColumnSum = 1
		if points[0][1] < len(d2Array[0]) - 1:
			rightColumnSum = sum([d2Array[y][x + 1] for (y, x) in points])
		leftColumnSum = 1
		if points[0][1] > 1:
			leftColumnSum = sum([d2Array[y][x - 1] for (y, x) in points])
		# If either adjacent column is dominating, shape would have branched out from that column.
		# if lm == (1791, 22) or lm == (1792, 22):
		# 	import pdb;pdb.set_trace()
		if leftColumnSum > currentColumnSum or rightColumnSum > currentColumnSum:
			return None, None
		# If the left and right columns are about even, it implies most of the magnitude is in the center column.
		ratio = leftColumnSum / rightColumnSum
		greaterColumn = -1
		if ratio < 1:
			greaterColumn = 1
			ratio = 1 / ratio
		# Return the center column plus the larger adjacent column as shapes of the point.
		# The non-dominating column can be chosen from previously cached points.
		# TODO: multiple edge cases not accounted for here. will need to account for in higher frequency resolution
		auxiliaryPoints = [(y, x - greaterColumn) for (y, x) in points]
		points.extend([(y, x + greaterColumn) for (y, x) in points])
		return points, auxiliaryPoints

	def getShapeList(self, d2Array):
		localMaxima = self.get2dLocalMaxima(d2Array)
		average = self.getAverageD2array(d2Array)
		localMaxima = self.filter2dLocalMaximaByMagnitude(d2Array, localMaxima, 100)

		shapeList = []
		usedPointsCache = [[[] for i in range(len(d2Array[0]))] for i in range(len(d2Array))]

		for lm in localMaxima:
			if usedPointsCache[lm[0]][lm[1]]:
				continue
			points, auxiliaryPoints = self.getShape(lm, d2Array, usedPointsCache)
			if points:
				shape = HarmonicShape(points, auxiliaryPoints, d2Array)
				shapeList.append(shape)

				for point in points:
					usedPointsCache[point[0]][point[1]].append(shape)

		shapeList.sort(key=lambda s: s.centerOfMass)
		for shape in shapeList:
			# TODO: center of mass check way to arbitrary and must be changed. Should be where precision is too low
			if shape.centerOfMass < 20:
				shape.isBaseCandidate = False
			if shape.isBaseCandidate:
				baseFrequencyIndex = shape.centerOfMass
				currentHarmonic = 2
				currentIndex = int(baseFrequencyIndex * currentHarmonic)
				while currentIndex < len(d2Array[0]) - 1:
					harmonicFound = []	# List of harmonic shapes alread used
					for timeIndex in range(shape.timeIndexStart, shape.timeIndexEnd + 1):
						for cache in [usedPointsCache[timeIndex][currentIndex], usedPointsCache[timeIndex][currentIndex + 1]]:
							if cache in harmonicFound:
								continue
							for cachedShape in cache:
								# if shape.timeIndexStart < 742 and shape.timeIndexStart >= 739:
								# 	if shape.centerOfMass < 37 and shape.centerOfMass > 35:
								# 		#if currentHarmonic == 5:
								# 		import pdb;pdb.set_trace()

								# Maybe we can make it smaller in frequency precision cases
								# It seems this value is critical so that if too low, harmonic frequencies dont get grouped
								# If too high, false harmonics are detected
								if percentDiff(cachedShape.centerOfMass / currentHarmonic, baseFrequencyIndex) < 0.015:
									# Base frequency magnitude has to be at least twice the harmonic for it to qualify
									# TODO: this segment of code is run multiple times for the same unqualifying shape, consider some caching
									sharedStartIndex = max([shape.timeIndexStart, cachedShape.timeIndexStart])
									sharedEndIndex = min([shape.timeIndexEnd, cachedShape.timeIndexEnd])
									baseFrequencyMagnitude = sum(shape.magnitudeByTime[sharedStartIndex - shape.timeIndexStart : sharedEndIndex - shape.timeIndexStart])
									harmonicFrequencyMagnitude = sum(cachedShape.magnitudeByTime[sharedStartIndex - cachedShape.timeIndexStart : sharedEndIndex - cachedShape.timeIndexStart])
									# This check is also unrealiable and the ratio used is very sensitive. Try another method
									if baseFrequencyMagnitude * (1 + currentHarmonic * 0.1) < harmonicFrequencyMagnitude:
										continue

									# If length of base shape is only a mere fraction of harmonci, it may not be real note.
									cachedShape.updateBaseCandidate(sharedStartIndex, sharedEndIndex)
									shape.harmonicCount += 1

									# As we are combining harmonic frequencies, we dont combine harminc magnitudes
									# with time index greater than base frequency's first time index. This could result
									# in problems.
									# if cachedShape.timeIndexEnd > shape.timeIndexEnd:
									# 	shape.magnitudeByTime.extend([0 for i in range(cachedShape.timeIndexEnd - shape.timeIndexEnd)])
									# 	shape.timeIndexEnd = cachedShape.timeIndexEnd
									for i in range(sharedStartIndex, sharedEndIndex + 1):
										shape.magnitudeByTime[i - shape.timeIndexStart] += cachedShape.magnitudeByTime[i - cachedShape.timeIndexStart]
									harmonicFound.append(cache)
									break


					currentHarmonic += 1
					currentIndex = int(baseFrequencyIndex * currentHarmonic)

		shapeList = self.consolidateShapeList(shapeList, d2Array, usedPointsCache)
		return shapeList

	def consolidateShapeList(self, shapeList, d2Array, usedPointsCache):
		# elementsPerTime = int(self.sampleRate / self.intervalLength / 2)
		# # elementsPerOctave is a very rough estimate, given that elements vary
		# estFrequency = 261
		# elementsPerFrequency = int(estFrequency / self.sampleRate * self.intervalLength)
		# def getMetricsFromPoint(p):
		# 	point = copy.deepcopy(p)
		# 	if point[0] < elementsPerTime:
		# 		point = (elementsPerTime, point[1])
		# 	if point[0] > len(d2Array) - elementsPerTime:
		# 		point = (len(d2Array) - elementsPerTime, point[1])
		# 	if point[1] < elementsPerFrequency:
		# 		point = (point[0], elementsPerFrequency)
		# 	if point[1] > len(d2Array[0]) - elementsPerFrequency:
		# 		point = (point[0], len(d2Array[0]) - elementsPerFrequency)
		# 	maximum = max(
		# 		[max(d2Array[t][point[1] - elementsPerFrequency : point[1] + elementsPerFrequency]) 
		# 			for t in range(point[0] - elementsPerTime, point[0] + elementsPerTime)
		# 		]
		# 	)
		# 	average = sum(
		# 		[sum(d2Array[t][point[1] - elementsPerFrequency : point[1] + elementsPerFrequency]) 
		# 			for t in range(point[0] - elementsPerTime, point[0] + elementsPerTime)
		# 		]
		# 	) / (elementsPerTime * elementsPerFrequency)
		# 	return maximum, average

		newShapeList = []
		for shape in shapeList:
			if shape.isBaseCandidate:
				newShapeList.append(shape)
			else:
				for point in shape.points:
					usedPointsCache[point[0]][point[1]].remove(shape)
		shapeList = newShapeList
		print(len(shapeList))

		maxMagnitudePerShape = [max(shape.magnitudeByTime) for shape in shapeList]
		maxMagnitudePerShape.sort(key=lambda x: -x)
		threshold = sum(maxMagnitudePerShape[50:150]) / 100
		print(max([max(shape.magnitudeByTime) for shape in shapeList]))
		print(threshold)
		lowRange = threshold / 16
		mediumRange = threshold / 4
		highRange = threshold / 2

		newShapeList = []
		for shape in shapeList:
			if max(shape.magnitudeByTime) > lowRange:
				newShapeList.append(shape)
			# maximum, average = getMetricsFromPoint(shape.points[0])
			# if d2Array[shape.points[0][0]][shape.points[0][1]] > maximum / 20 and percentDiff(maximum, average) > 2:
			# 	newShapeList.append(shape)
			else:
				for point in shape.points:
					usedPointsCache[point[0]][point[1]].remove(shape)
		shapeList = newShapeList
		print(len(shapeList))

		shapeList.sort(key=lambda shape: shape.timeIndexStart)
		newShapeList = []
		for shape in shapeList:
			# Check if a point is in cache. If not, it was removed by earlier iteration of this so we do not add to newShapeList
			# Should be correct since this processes shapes top down
			if shape in usedPointsCache[shape.points[0][0]][shape.points[0][1]]:
				lookForConnection = True
				while lookForConnection:
					possibleConnectingShapes = set([])
					cachePoints = set([])
					lookForConnection = False
					for p in shape.getEndingPoints():
						if p[0] < len(d2Array) - 1:
							if p[1] > 1:
								cachePoints.add((p[0] + 1, p[1] - 1))
							cachePoints.add((p[0] + 1, p[1]))
							if p[1] < len(d2Array[0]) - 1:
								cachePoints.add((p[0] + 1, p[1] + 1))
					for cachePoint in cachePoints:
						possibleConnectingShapes.update(usedPointsCache[cachePoint[0]][cachePoint[1]])
					for connectingShape in possibleConnectingShapes:
						if (shape.timeIndexEnd + 1 == connectingShape.timeIndexStart and
							percentDiff(connectingShape.centerOfMass, shape.centerOfMass) < 0.01 and
							percentDiff(shape.magnitudeByTime[-1], connectingShape.magnitudeByTime[0] < 0.5)):
						
							# Combine the 2 shapes into 1 shape by emptying connecting shape and unloading to shape
							points = copy.deepcopy(connectingShape.points)
							points.extend(shape.points)
							auxiliaryPoints = copy.deepcopy(connectingShape.auxiliaryPoints)
							auxiliaryPoints.extend(shape.auxiliaryPoints)

							timeIndices = [p[0] for p in points]
							start = min(timeIndices)
							end = max(timeIndices)
							magnitudeToTransfer = shape.magnitudeByTime[start - shape.timeIndexStart :]
							magnitudeToTransfer.extend(connectingShape.magnitudeByTime[: end - connectingShape.timeIndexStart + 1])
							if sum(magnitudeToTransfer) < 0:
								magnitudeToTransfer = [0 for m in magnitudeToTransfer]
							shape = HarmonicShape(points, auxiliaryPoints, d2Array, magnitudeToTransfer)
							for cp in connectingShape.points:
								usedPointsCache[cp[0]][cp[1]].remove(connectingShape)
								usedPointsCache[cp[0]][cp[1]].append(shape)
							lookForConnection = True
							break
				newShapeList.append(shape)
		shapeList = newShapeList
		print(len(shapeList))


		shapeList.sort(key=lambda shape: shape.magnitude)
		# Evaluate each shape internally and remove all uneeded points

		usedPointsCache = [[[] for i in range(len(d2Array[0]))] for i in range(len(d2Array))]
		newShapeList = []
		for shape in shapeList:
			for i in range(len(shape.magnitudeByTime)):
				# value = sum([d2Array[p[0]][p[1]] for p in shape.points if p[0] - shape.timeIndexStart == i])
				# maximum, average = getMetricsFromPoint(shape.points[0])
				# mediumRange = maximum / 4
				# lowRange = maximum / 20
				# if value < lowRange or percentDiff(maximum, average) < 2:
				# 	shape.magnitudeByTime[i] = -1
				# if value >= lowRange and value < mediumRange:
				# 	isPoint = False
				# 	if (i == len(shape.magnitudeByTime) - 1 and len(shape.magnitudeByTime) != 1 ):
				# 		c = sum([d2Array[p[0]][p[1]] for p in shape.points if p[0] - shape.timeIndexStart == i - 1])
				# 		if (c >= mediumRange and 
				# 			percentDiff(shape.magnitudeByTime[i - 1], shape.magnitudeByTime[i]) > 0.2):
				# 			isPoint = True
				# 	if (i == 0 and len(shape.magnitudeByTime) != 1 ):
				# 		c = sum([d2Array[p[0]][p[1]] for p in shape.points if p[0] - shape.timeIndexStart == i + 1])
				# 		if (c >= mediumRange and 
				# 			percentDiff(shape.magnitudeByTime[i + 1], shape.magnitudeByTime[i]) > 0.2):
				# 			isPoint = True
				# 	if not isPoint:
				# 		shape.magnitudeByTime[i] = -1
				if shape.magnitudeByTime[i] < lowRange:
					shape.magnitudeByTime[i] = -1
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
			for i in range(len(shape.magnitudeByTime) + 1):
				if i == len(shape.magnitudeByTime) or shape.magnitudeByTime[i] < 0:
					if points:
						timeIndices = [p[0] for p in points]
						start = min(timeIndices)
						end = max(timeIndices)
						s = HarmonicShape(points, auxiliaryPoints, d2Array, shape.magnitudeByTime[start - shape.timeIndexStart : end - shape.timeIndexStart + 1])
						# Im assumming that the shapes that are split and dont satisfy this are irrelevant.
						# Could possibly be that earlier logic didnt group shape properly.
						if s.magnitude > 0:
							newShapeList.append(s)
							for p in s.points:
								usedPointsCache[p[0]][p[1]].append(s)
						points = []
						auxiliaryPoints = []
				else:
					points.extend([p for p in shape.points if p[0] == i + shape.timeIndexStart])
					auxiliaryPoints.extend([p for p in shape.auxiliaryPoints if p[0] == i + shape.timeIndexStart])
		shapeList = newShapeList
		print(len(shapeList))


		# # Evaluate each shape relative to other shapes at the same time.
		newShapeList = []
		for shape in shapeList:			
			# Rule 1:
			# If harmonic overlap is over 50% of magnitude, remove
			coveredByHarmonic = False
			allPossibleHarmonics = set([])
			currentHarmonic = 2
			currentIndex = int(shape.centerOfMass * currentHarmonic)
			while currentIndex < len(d2Array[0]) - 1:
				for timeIndex in range(shape.timeIndexStart, shape.timeIndexEnd + 1):
					for cache in [usedPointsCache[timeIndex][currentIndex], usedPointsCache[timeIndex][currentIndex + 1]]:
						for cachedShape in cache:
							if percentDiff(cachedShape.centerOfMass / currentHarmonic, shape.centerOfMass) < (5 - currentHarmonic) * 0.005 + 0.015:
								allPossibleHarmonics.add(cachedShape)
				currentHarmonic += 1
				currentIndex = int(shape.centerOfMass * currentHarmonic)

			for harmonic in allPossibleHarmonics:
				sharedStartIndex = max([shape.timeIndexStart, harmonic.timeIndexStart])
				sharedEndIndex = min([shape.timeIndexEnd, harmonic.timeIndexEnd])
				# If the sum of covered is bigger than half the total
				if sum(shape.magnitudeByTime[sharedStartIndex - shape.timeIndexStart : sharedEndIndex - shape.timeIndexStart + 1]) * 2 > sum(shape.magnitudeByTime):
					# If harmonic actually covers shape.
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
			# 	possibleShapes.update(usedPointsCache[startIndex][i])
			# for possibleShape in possibleShapes:
			# 	if possibleShape != shape:
			# 		if possibleShape.magnitudeByTime[startIndex - possibleShape.timeIndexStart] / firstMagnitude > 1.2:
			# 			coveredByNearbyNote = True
			if not (coveredByHarmonic or coveredByNearbyNote):
				newShapeList.append(shape)
			else:
				for p in shape.points:
					usedPointsCache[p[0]][p[1]].remove(shape)
		shapeList = newShapeList
		print(len(shapeList))
				
		return shapeList



