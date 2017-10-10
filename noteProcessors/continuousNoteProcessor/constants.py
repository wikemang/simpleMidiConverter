
# Constants for note processing
class Constants:
	# Max data buffer for processing columns
	MAX_BUFFER_SIZE = 250	# Should only be about a few seconds (ie the length of really long note)
	# The minimum slope that is recognised as a peak
	CUTOFF_SHARPNESS = 4
	# The width in pixels that each processor works with. Should be odd number for symmetry
	COLUMN_PROCESSOR_DATA_WIDTH = 5
	# The number of elements the peak is calculated with.
	PEAK_BASE = 2
	# Notes must have a minimum length.
	MINIMAL_NOTE_LENGTH = 5
