# Wav specs http://soundfile.sapp.org/doc/WaveFormat/

# Simple .wav parser that parses the contents of a wav file into memory.
# TODO: could extend to use Audacity to convert from other formats.

# using pythons wave std library is considered, but it parses samples as a string, possibly adding extra run time.
class SimpleWavParser:
	# Little Endian	
	maxInt = [2 ** (i * 8 - 1) for i in range(0, 10)]
	def getIntFromBytes(self, bytes, byteLength):
		total = 0
		for i in range(0, byteLength):
			total += bytes[i] << (i * 8)

		if total > SimpleWavParser.maxInt[byteLength]:
			return total - SimpleWavParser.maxInt[byteLength] * 2
		else:
			return total

	# Waveform list elements corresponds to the different channels.
	# Every amplitude value go from -2^(bitsPerSample-1) to 2 ^ (bitsPerSample-1)
	def getRawData(self, filename):
		data = []
		with open(filename, 'rb') as f:
			data = f.read(44)	# Wav file metadata length. Should remain this till the end of time.

		chunkSize = self.getIntFromBytes(data[4:8], 4)	# We might not need this.
		audioFormat = self.getIntFromBytes(data[20:21], 1)
		numChannels = self.getIntFromBytes(data[22:23], 1)
		sampleRate = self.getIntFromBytes(data[24:28], 4)
		byteRate = self.getIntFromBytes(data[28:32], 4)
		blockAlign = self.getIntFromBytes(data[32:34], 2)	# We might not need this.
		bitsPerSample = self.getIntFromBytes(data[34:35], 1)
		dataSize = self.getIntFromBytes(data[40:44], 4)

		# print "chunkSize %s" % chunkSize
		# print "audioFormat %s" % audioFormat
		# print "numChannels %s" % numChannels
		# print "sampleRate %s" % sampleRate
		# print "byteRate %s" % byteRate
		# print "blockAlign %s" % blockAlign
		# print "bitsPerSample %s" % bitsPerSample
		# print "dataSize %s" % dataSize

		assert(audioFormat == 1)	# 1 for uncompressed
		assert(byteRate == sampleRate * numChannels * bitsPerSample / 8) # Assertion suggested by Wav specs

		# One waveform for each channel.
		bytesPerSample = bitsPerSample // 8
		dataCount = (dataSize // bytesPerSample) // numChannels

		waveforms = [[0 for i in range(dataCount)] for n in range(numChannels)]
		dataSamples = []

		with open(filename, 'rb') as f:
			f.read(44)	# Skip meta data
			dataSamples = f.read(bytesPerSample * numChannels * dataCount)
		index = 0

		for i in range(dataCount):
			for j in range(numChannels):
				waveHeight = self.getIntFromBytes(dataSamples[index: index + bytesPerSample], bytesPerSample)
				waveforms[j][i] = waveHeight
				index += bytesPerSample

		return waveforms, sampleRate, bitsPerSample

	# Takes a lot less space compared to raw data
	# Returns waveform superpositioned from all channels
	def getSingleWaveform(self, filename):
		data = []
		with open(filename, 'rb') as f:
			data = f.read(44)	# Wav file metadata length. Should remain this till the end of time.

		chunkSize = self.getIntFromBytes(data[4:8], 4)	# We might not need this.
		audioFormat = self.getIntFromBytes(data[20:21], 1)
		numChannels = self.getIntFromBytes(data[22:23], 1)
		sampleRate = self.getIntFromBytes(data[24:28], 4)
		byteRate = self.getIntFromBytes(data[28:32], 4)
		blockAlign = self.getIntFromBytes(data[32:34], 2)	# We might not need this.
		bitsPerSample = self.getIntFromBytes(data[34:35], 1)
		dataSize = self.getIntFromBytes(data[40:44], 4)

		# print "chunkSize %s" % chunkSize
		# print "audioFormat %s" % audioFormat
		# print "numChannels %s" % numChannels
		# print "sampleRate %s" % sampleRate
		# print "byteRate %s" % byteRate
		# print "blockAlign %s" % blockAlign
		# print "bitsPerSample %s" % bitsPerSample
		# print "dataSize %s" % dataSize

		assert(audioFormat == 1)	# 1 for uncompressed
		assert(byteRate == sampleRate * numChannels * bitsPerSample / 8) # Assertion suggested by Wav specs

		# One waveform for each channel.
		bytesPerSample = bitsPerSample // 8
		dataCount = (dataSize // bytesPerSample) // numChannels

		waveform = [0 for i in range(dataCount)]
		dataSamples = []

		with open(filename, 'rb') as f:
			f.read(44)	# Skip meta data
			dataSamples = f.read(bytesPerSample * numChannels * dataCount)
		index = 0

		for i in range(dataCount):
			for j in range(numChannels):
				waveHeight = self.getIntFromBytes(dataSamples[index: index + bytesPerSample], bytesPerSample)
				waveform[i] += waveHeight
				index += bytesPerSample

		return waveform, sampleRate, bitsPerSample
