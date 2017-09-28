import copy

# FrequencyTimeShape describes a cluster of points deemed to represent a single note.
# The points are stored in the class and so are some of its calculated properties.
# TODO: should split this class into its own base class
class FrequencyTimeShape:
	def __init__(self, points, auxiliaryPoints, frequencyTimeArray, magnitudeByTime=[]):

		self.points = points	# Main points that the shape contains
		self.auxiliaryPoints = auxiliaryPoints	# Auxiliary set of points that the shape may contain
		self.centerOfMass = None	# Center of mass of all points (for frequency only)
		self.magnitude = None	# Arbitrary value to denote overall magnitude of shape
		self.timeIndexStart = None	# First time index of all points
		self.timeIndexEnd = None	# Last time index of all points
		self.isBaseCandidate = True	# If this note qualifies as a base note (ie. not a harmonic)
		self.usedAsHarmonic = []	# Array to keep track of which shape each time index of this shape is a harmonic for.
		self.harmonicCount = 0	# Number of harmonics detected when this shape is used as base frequency.
		self.magnitudeByTime = magnitudeByTime	# Magnitude over time indices. Index 0 here corresponds to timeIndexStart of main array
		self.reconsolidatedShape = False	# This is used in edge case of restructing the shape internally. TODO: make less hacky
		if self.magnitudeByTime:
			self.reconsolidatedShape = True
		self.calculateProperties(frequencyTimeArray)

	def calculateProperties(self, frequencyTimeArray):
		timeIndices = [p[0] for p in self.points]
		self.timeIndexStart = min(timeIndices)
		self.timeIndexEnd = max(timeIndices)

		if not self.reconsolidatedShape:	# MagnitudeByTime will not be recalculated
			self.magnitudeByTime = [0 for i in range(self.timeIndexStart, self.timeIndexEnd + 1)]
		self.usedAsHarmonic = [[] for i in range(self.timeIndexStart, self.timeIndexEnd + 1)]

		totalMagnitude = 0
		weightedMagnitude = 0
		allPoints = copy.deepcopy(self.points)
		allPoints.extend(self.auxiliaryPoints)
		for p in allPoints:
			# We reduce the magnitude of each column by what we think is the noise
			magnitude = frequencyTimeArray[p[0]][p[1]]
			weightedMagnitude += p[1] * magnitude 
			totalMagnitude += magnitude
			if not self.reconsolidatedShape:	# MagnitudeByTime will not be recalculated
				self.magnitudeByTime[p[0] - self.timeIndexStart] += magnitude


		self.centerOfMass = weightedMagnitude / totalMagnitude
		self.magnitude = sum(self.magnitudeByTime) / len(self.magnitudeByTime)

	def print(self):
		print("com: %s" % self.centerOfMass)
		print("index: %d - %d" % (self.timeIndexStart, self.timeIndexEnd))
		print(self.magnitudeByTime)

	# This function is called when another shape uses this one as a harmonic.
	# If more than half of this shape's time duration is used as a harmonic, this shape is no longer a base frequency candidate.
	def updateBaseCandidate(self, startIndex, endIndex, shape):
		for i in range(startIndex, endIndex + 1):
			self.usedAsHarmonic[i - self.timeIndexStart].append(shape)
		if len(self.usedAsHarmonic) < len([x for x in self.usedAsHarmonic if x != []]) * 2:
			self.isBaseCandidate = False

	def getEndingPoints(self):
		return [p for p in self.points if p[0] == self.timeIndexEnd]

class BaseShapeStrategy:
	def __init__(self, sampleRate, intervalsPerSecond):
		self.sampleRate = sampleRate
		self.intervalsPerSecond = intervalsPerSecond
		self.usedPointsCache = None

	# Diagonals count for local maximum
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
	def filter2dLocalMaximaByFraction(self, d2Array, localMaxima, filterIntensity):
		largestMagnitude = max([d2Array[m[0]][m[1]] for m in localMaxima])
		filteredByMagnitude = [m for m in localMaxima if d2Array[m[0]][m[1]] > largestMagnitude / filterIntensity]
		return filteredByMagnitude

	def getD2arrayAverage(self, d2Array):
		rowAverage = [sum(d2Array[i]) / len(d2Array[i]) for i in range(len(d2Array))]
		average = sum(rowAverage) / len(rowAverage)
		return average

	def filter2dLocalMaximaByThreshhold(self, d2Array, localMaxima, threshold):
		filteredByMagnitude = [m for m in localMaxima if d2Array[m[0]][m[1]] > threshold]
		return filteredByMagnitude

	# This function will get the shape for a given maximum.
	# This function uses only heuristics, and does not have full logical coverage for all possible cases.
	# This function is the core of this note processor's idea and will be improved over time.
	def getShape(self, lm, d2Array, isOriginalLm = True):
		points = [lm]
		# Search down
		y, x = lm
		currentValue = d2Array[y][x]
		lmValue = currentValue
		halfCache = 0	# Used to store value of element when the value halfsizes
		maxIncrement = 1.41	# Arbitrary number indicating the relative difference between elements of the same shape
		while True:
			y += 1
			if y >= len(d2Array):
				break
			if self.usedPointsCache[y][x]:	# Element already used in another shape
				break
			newValue = d2Array[y][x]
			if halfCache != 0 and currentValue < halfCache / maxIncrement: # Conditional end of current shape
				break
			if newValue < currentValue / (maxIncrement ** 2): # End of current shape
				break
			if newValue < currentValue / maxIncrement: # Conditional end of current shape
				if halfCache != 0:
					break
				halfCache = newValue
			if newValue > currentValue * maxIncrement:	# New Shape
				break
			if newValue < lmValue / (maxIncrement ** 3):	# End of shape, too much decay?
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
			if self.usedPointsCache[y][x]:
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

		greaterSum = max(leftColumnSum, rightColumnSum)
		greaterColumn = -1
		if greaterSum == rightColumnSum:
			greaterColumn = 1

		if greaterSum > currentColumnSum:
			if [self.usedPointsCache[y][x + greaterColumn] for (y, x) in points if self.usedPointsCache[y][x + greaterColumn]]:
			# If either adjacent column is dominating and is a shape, shape would have branched out from that column.
				return None, None
			else:
				# Infinite recursion could occur if the shape is different from the new column.
				if not isOriginalLm:
					return None, None
				newLm = None
				maxValue = 0
				# Look for the largest element on the larger column. Not necessarily a local max.
				for (y, x) in points:
					if d2Array[y][x + greaterColumn] > maxValue:
						maxValue = d2Array[y][x + greaterColumn]
						newLm = (y, x + greaterColumn)
				return self.getShape(newLm, d2Array, isOriginalLm=False)

		# Return the center column plus the larger adjacent column as shapes of the point.
		# The non-dominating (auxiliary) column can be chosen from previously cached points.
		auxiliaryPoints = [(y, x - greaterColumn) for (y, x) in points]
		points.extend([(y, x + greaterColumn) for (y, x) in points])

		return points, auxiliaryPoints

	def getShapeList(self, d2Array):
		# Get all local maxima of the array which are bigger than average. (below average is defnitely noise)
		localMaxima = self.get2dLocalMaxima(d2Array)
		average = self.getD2arrayAverage(d2Array)
		localMaxima = self.filter2dLocalMaximaByFraction(d2Array, localMaxima, 100)

		shapeList = []
		self.usedPointsCache = [[[] for i in range(len(d2Array[0]))] for i in range(len(d2Array))]

		# Iterate through all localMaxima and tries to derive a shape from each.
		for lm in localMaxima:
			# lm already part of another shape. continue
			if self.usedPointsCache[lm[0]][lm[1]]:
				continue
			points, auxiliaryPoints = self.getShape(lm, d2Array)
			if points:
				shape = FrequencyTimeShape(points, auxiliaryPoints, d2Array)
				shapeList.append(shape)

				for point in points:
					self.usedPointsCache[point[0]][point[1]].append(shape)

		return shapeList


