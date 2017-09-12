def percentDiff(a, b):
	if  min([a, b]) == 0:
		return 999	# For any uses of this function, 999 is a redundantly big number
	return abs(1 - max([a, b]) / min([a, b]))
