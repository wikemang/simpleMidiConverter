import copy
from matplotlib import pyplot
from matplotlib.style import context

def percentDiff(a, b):
	if  min([a, b]) == 0:
		return 999	# For any uses of this function, 999 is a redundantly big number
	return abs(1 - max([a, b]) / min([a, b]))

# I've read somewhere that python isnt optimized for recursion because of stackframe management so we do this iteratively
# fuzzy=True will imply that the value may not exist and we want the 2 indices the value is between. Return lower index.

def binSearch(array, keyFunc, value, fuzzy=False):
	firstIndex = 0
	lastIndex = len(array) - 1
	middleIndex = int((firstIndex + lastIndex) / 2)
	middleElement = keyFunc(array[middleIndex])
	while middleElement != value:
		if firstIndex == lastIndex:
			if fuzzy:
				if value > middleElement:
					if middleIndex != len(array) - 1:
						return middleIndex
					else:
						return middleIndex - 1
				else:
					if middleIndex != 0:
						return middleIndex - 1
					else:
						return middleIndex
			return -1
		if value > middleElement:
			firstIndex = min(lastIndex, middleIndex + 1)
		else:
			lastIndex = max(firstIndex, middleIndex - 1)
		middleIndex = int((firstIndex + lastIndex) / 2)
		middleElement = keyFunc(array[middleIndex])

	return middleIndex

# Saves a plot of the 2d Array to file.
def d2Plot(d2Array, filename, widthCompression=20, heightCompression=20):

	pyplot.figure(figsize=(len(d2Array[0]) / widthCompression, len(d2Array) / heightCompression))

	pyplot.imshow(d2Array)

	pyplot.colorbar(orientation='vertical')
	pyplot.savefig(filename, dpi=300)
	pyplot.close('all')

def aboutEqual(val1, val2):
	if abs(val1 - val2) < 1:
		return True
	return False


def getVariance(arr):
	if len(arr) == 0:
		return 0
	avg = sum(arr) / len(arr)
	variance = 0
	for a in arr:
		variance += (a - avg) ** 2
	return variance / len(arr)

# I don't fully understand https://en.wikipedia.org/wiki/Jenks_natural_breaks_optimization
# Not real Jenks, just some wannabe algo that serves a similar purpose. TBH I dont understand the algorithm and I dont trust using some cryptic port of it.
# arr is input array
# Indices is start index of each class/group
def naturalBreaksOptimize(arr, indices):
	ranges = copy.deepcopy(indices)
	ranges.append(len(arr))
	finished = False
	while not finished:
		finished = True
		for i in range(len(indices) - 1):
			var1 = getVariance(arr[ranges[i]: ranges[i + 1]])
			var2 = getVariance(arr[ranges[i + 1]: ranges[i + 2]])
			varSum = var1 + var2
			newRange = ranges[i + 1] - 1
			if var1 < var2:
				 newRange += 2
			var3 = getVariance(arr[ranges[i]: newRange])
			var4 = getVariance(arr[newRange: ranges[i + 2]])
			if var3 + var4 < varSum:
				ranges[i + 1] = newRange
				finished = False
	return ranges[:-1]
