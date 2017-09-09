# Wav specs http://soundfile.sapp.org/doc/WaveFormat/

import threading
import time
from tkinter import *	# Simple GUI
import numpy as np
from math import pow

# Little Endian
maxInt = [2 ** (i * 8 - 1) for i in range(0, 10)]
def getIntFromBytes(bytes):
	total = 0
	l = len(bytes)
	for i in range(0, l):
		total += bytes[i] << (i * 8)

	if total > maxInt[l]:
		return total - maxInt[l] * 2
	else:
		return total


# Waveform list elements corresponds to the different channels.
# Every amplitude value go from -2^(bitsPerSample-1) to 2 ^ bitsPerSample
def getRawWaveData(filename):
	data = []
	with open(filename, 'rb') as f:
		data = f.read(44)	# Wav file metadata length. Should remain this till the end of time.

	chunkSize = getIntFromBytes(data[4:8])	# We might not need this.
	audioFormat = getIntFromBytes(data[20:21])
	numChannels = getIntFromBytes(data[22:23])
	sampleRate = getIntFromBytes(data[24:28])
	byteRate = getIntFromBytes(data[28: 32])
	blockAlign = getIntFromBytes(data[32:34])	# We might not need this.
	bitsPerSample = getIntFromBytes(data[34:35])
	dataSize = getIntFromBytes(data[40:44])

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
	waveform = []
	# 1 Waveform for each channel.
	for i in range(0, numChannels):
		waveform.append([])

	dataCount = (dataSize * 8 // bitsPerSample) // numChannels
	with open(filename, 'rb') as f:
		f.read(44)	# Skip meta data
		for i in range(0, dataCount):
			for j in range(0, numChannels):
				waveHeight = getIntFromBytes(f.read(bitsPerSample // 8))
				waveform[j].append(waveHeight)

	return waveform, sampleRate, bitsPerSample
