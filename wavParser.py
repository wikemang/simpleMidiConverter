# Wav specs http://soundfile.sapp.org/doc/WaveFormat/

# Simple .wav parser that parses the contents of a wav file into memory.
# TODO: could extend to use Audacity to convert from other formats.

class SimpleWavParser:
	# Little Endian	
	maxInt = [2 ** (i * 8 - 1) for i in range(0, 10)]
	def getIntFromBytes(self, bytes):
		total = 0
		l = len(bytes)
		for i in range(0, l):
			total += bytes[i] << (i * 8)

		if total > SimpleWavParser.maxInt[l]:
			return total - SimpleWavParser.maxInt[l] * 2
		else:
			return total

	# Waveform list elements corresponds to the different channels.
	# Every amplitude value go from -2^(bitsPerSample-1) to 2 ^ (bitsPerSample-1)
	def getRawData(self, filename):
		data = []
		with open(filename, 'rb') as f:
			data = f.read(44)	# Wav file metadata length. Should remain this till the end of time.

		chunkSize = self.getIntFromBytes(data[4:8])	# We might not need this.
		audioFormat = self.getIntFromBytes(data[20:21])
		numChannels = self.getIntFromBytes(data[22:23])
		sampleRate = self.getIntFromBytes(data[24:28])
		byteRate = self.getIntFromBytes(data[28: 32])
		blockAlign = self.getIntFromBytes(data[32:34])	# We might not need this.
		bitsPerSample = self.getIntFromBytes(data[34:35])
		dataSize = self.getIntFromBytes(data[40:44])

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
		waveform = [[] for n in range(numChannels)]
		dataCount = (dataSize * 8 // bitsPerSample) // numChannels
		bytesPerSample = bitsPerSample // 8
		dataSamples = []
		with open(filename, 'rb') as f:
			f.read(44)	# Skip meta data
			dataSamples = f.read(bytesPerSample * numChannels * dataCount)
		for i in range(0, dataCount):
			for j in range(0, numChannels):
				index = (i * numChannels + j) * bytesPerSample
				waveHeight = self.getIntFromBytes(dataSamples[index: index + bytesPerSample])
				waveform[j].append(waveHeight)

		return waveform, sampleRate, bitsPerSample
