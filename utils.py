def percentDiff(a, b):
	if  min([a, b]) == 0:
		return 999
	return abs(1 - max([a, b]) / min([a, b]))