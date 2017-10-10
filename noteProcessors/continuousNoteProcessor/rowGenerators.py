import gc
import math
from numpy import fft

from noteProcessors.continuousNoteProcessor.constants import Constants
class ContinuousGenerator:
	def __init__(self, samplesPerInterval, intervalsPerFrame, waveform):
		self.samplesPerInterval = samplesPerInterval
		self.intervalsPerFrame = intervalsPerFrame
		self.waveform = waveform

	def generate(self):
		samplesPerFrame = self.samplesPerInterval * self.intervalsPerFrame
		trimFrames = 5

		sampleIndex = 0
		# TODO: since waveform is the max space, this effectively almost doubles space requirement for this program
		# We can re-write paddedWaveform as wrapper around waveform if this becomes a problem
		# You know I just wish python ints didnt take 28 bytes
		paddedWaveform = [0 for i in range(samplesPerFrame - self.samplesPerInterval)]
		paddedWaveform.extend(self.waveform)

		maxSample = len(paddedWaveform) - (2 * samplesPerFrame) + 1
		counter = 0
		maxCounter = int(maxSample / (samplesPerFrame - self.samplesPerInterval * trimFrames * 2)) + 1
		while sampleIndex <= maxSample:
			counter += 1
			print("Processing Frame: %s / %s" % (counter, maxCounter))
			gc.collect()

			currentFFT = []
			prevFFT = [0 for i in range(int(samplesPerFrame / 2))]

			startingSampleIndex = sampleIndex
			for i in range(self.intervalsPerFrame):
				currentFFT = fft.fft(paddedWaveform[sampleIndex: sampleIndex + samplesPerFrame])[:int(samplesPerFrame / 2)]
				d2Row = [abs(currentFFT[j]) - abs(prevFFT[j]) for j in range(len(currentFFT))]
				prevFFT = currentFFT
				sampleIndex += self.samplesPerInterval

				# We trim the first few and last few frames because of the anomolies they may contain.
				if i >= trimFrames and i < self.intervalsPerFrame - trimFrames:
					yield d2Row
			sampleIndex -= self.samplesPerInterval * trimFrames * 2
			# Set the samples used in the current frame to 0, so that the beginning of the next frame is "clean"
			for i in range(max(sampleIndex, startingSampleIndex + samplesPerFrame - self.samplesPerInterval) , sampleIndex + samplesPerFrame - self.samplesPerInterval):
				paddedWaveform[i] = 0
		# Shove a bunch of 0's to the processors to ensure completion
		for i in range(Constants.MAX_BUFFER_SIZE):
			yield [0 for i in range(len(currentFFT))]

class RecursiveGenerator:
	def __init__(self, samplesPerInterval, intervalsPerFrame, waveform):
		self.samplesPerInterval = samplesPerInterval
		self.intervalsPerFrame = intervalsPerFrame
		self.waveform = waveform

	def generate(self):

		samplesPerFrame = self.samplesPerInterval * self.intervalsPerFrame
		fftLen = int(samplesPerFrame / 2) + 1

		sampleIndex = 0
		# TODO: since waveform is the max space, this effectively almost doubles space requirement for this program
		# We can re-write paddedWaveform as wrapper around waveform if this becomes a problem
		# You know I just wish python ints didnt take 28 bytes

		d2Array = []
		maxSample = len(self.waveform)
		counter = 0
		maxCounter = int(maxSample / samplesPerFrame)
		while sampleIndex <= maxSample - samplesPerFrame:
			counter += 1
			print("Processing Frame: %s / %s" % (counter, maxCounter))
			gc.collect()
			# Calculate a fft using the entire frame, we put this in the first frame row.
			frameFFT = [abs(f) for f in fft.fft(self.waveform[sampleIndex: sampleIndex + samplesPerFrame])[:fftLen]]
			frameRows = [[0 for i in range(fftLen)] for j in range(self.intervalsPerFrame)]
			frameRows[0] = frameFFT

			i = 1
			# Simulates a recursive loop for divide and conquer.
			# Essentially the algorith does as follows:
			# 1. Select the scope of the recursion, intervalsPerFrame, which is the # of FFTs to store per frame, and 
			# limits recursion to a depth of log(intervalsPerFrame)
			# 2. Designate the size of the current chunk as n and the start of the current chunk as i. For the first iteration
			# i = 0 and n = intervalsPerFrame.
			# 3. Split the current chunk into 2 equal sub-chunks. The sub-chunk will correspond to a series of samples of the
			# original frame's FFT. The index range of the sub-chunk will have the same ratio as the index range of the 
			# original FFT. ie if chunk index range is 0-1 and total indices are 0-8, the chunk's corresponding samples will be 
			# the first quarter of samples.
			# 4. Calculate FFTs for each sub chunk.
			# 5. Since FFTs of sub chunk will have less elements, intermediate elements are interpolated such that the final
			# subchunk fft has the same elements as the original Frame's FFT
			# 6. The values of the original FFT will be divided into 2 FFTs, using the ratio of the subchunk's FFTs.
			# 7. The 2 new FFTs are placed at i, and i + n/2 respectively, and a new recursive call is made using the subchunks
			# as the new chunk.
			while 2 ** i <= self.intervalsPerFrame:
				j = 0
				pow2 = (2 ** i)	# Reduce some computation time
				while j <= pow2 - 1:
					firstRowIndex =  j * int(self.intervalsPerFrame / pow2)
					secondRowIndex = (j + 1) * int(self.intervalsPerFrame / pow2)
					sampleLen = (secondRowIndex - firstRowIndex) * self.samplesPerInterval
					firstFFTSampleIndex = firstRowIndex * self.samplesPerInterval + sampleIndex
					firstFFT = [abs(f) for f in fft.fft(self.waveform[firstFFTSampleIndex: firstFFTSampleIndex + sampleLen])]
					secondFFTSampleIndex = secondRowIndex * self.samplesPerInterval + sampleIndex
					secondFFT = [abs(f) for f in fft.fft(self.waveform[secondFFTSampleIndex: secondFFTSampleIndex + sampleLen])]
					for k in range(fftLen):
						lerpRatio = 0 # Percent of first half
						if k < pow2:
							lerpRatio = 0.5 # We cant lerp for frequencies that are lost
						else:
							index = k / pow2
							lowerIndex = math.floor(index)
							higherIndex = math.ceil(index)
							if lowerIndex == higherIndex:
								lerpRatio = firstFFT[lowerIndex] / (firstFFT[lowerIndex] + secondFFT[lowerIndex])
							else:
								indexRatio = index - lowerIndex
								firstValue = firstFFT[lowerIndex] * indexRatio + firstFFT[higherIndex] * (1 - indexRatio)
								secondValue = secondFFT[lowerIndex] * indexRatio + secondFFT[higherIndex] * (1 - indexRatio)
								lerpRatio = firstValue / (firstValue + secondValue)
						frameRows[secondRowIndex][k] = (1 - lerpRatio) * frameRows[firstRowIndex][k]
						frameRows[firstRowIndex][k] = lerpRatio * frameRows[firstRowIndex][k]
					j += 2
				i += 1

			for row in frameRows:
				yield row
			sampleIndex += samplesPerFrame
