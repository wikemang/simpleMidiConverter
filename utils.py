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
