from numpy import fft
from noteParser import NoteParser
from activeNote import ActiveNote

import copy


class NoteProcessor2:
	def __init__(self, waveforms, sampleRate, noteParser):
		self.waveforms = waveforms
		self.sampleRate = sampleRate
		self.noteList = noteParser.parseNotes()
		self.intervalSize = 8

	def getActiveNotes(self, note, fourierTransform, waveform):
		# get index of fourierTransform corresponding to note frequency
		lenWav = len(waveform)
		freqIndex = round(note.frequency * lenWav / self.sampleRate)

		# remove frequencies centered at closest index. TODO fine tune for better accuracy
		fT = copy.deepcopy(fourierTransform) # TODO: make this more effcient. Since we are only changing few elements
		totalRemovedReal = sum([int(a) for a in fT[freqIndex - 1: freqIndex + 2]])
		
		#fT[freqIndex - 1: freqIndex + 2] = [0, 0, 0]
		#fT[lenWav - (freqIndex + 1): lenWav - (freqIndex - 2)] = [0, 0, 0]
		
		for i in range (freqIndex - 1, freqIndex + 2):
			fT[i] = fT[i] - float(fT[i])
		for i in range (lenWav - (freqIndex + 1), lenWav - (freqIndex - 2)):
			fT[i] = fT[i] - float(fT[i])

		fT[0] -= totalRemovedReal * 2
		if len(fT) % 2 == 0:
			fT[len(fT) - 1] -= totalRemovedReal * 2

		# compare new waveform with removed note with old waveform
		newWaveform = [int(a) for a in fft.ifft(fT)]
		diffWaveform = [abs(newWaveform[i] - waveform[i]) for i in range(len(waveform))]

		# tmp code
		fT = copy.deepcopy(fourierTransform)

		for i in range (freqIndex - 1):
			fT[i] = fT[i] - float(fT[i])
		for i in range (freqIndex + 2, lenWav - (freqIndex + 1)):
			fT[i] = fT[i] - float(fT[i])
		for i in range (lenWav - (freqIndex - 2), lenWav):
			fT[i] = fT[i] - float(fT[i])
		fT[0] = float(sum(fT))
		if len(fT) % 2 == 0:
			fT[len(fT) - 1] -= fT[0]
		jksWaveform = [abs(int(a)) for a in fft.ifft(fT)]

		asdf = [abs(jksWaveform[i] - diffWaveform[i]) for i in range(len(waveform))]

		import pdb;pdb.set_trace()

		maxAmplitude = max(waveform)


		print("Analysing: %s, \t %s \t%s" % (note.name.ljust(8), max(diffWaveform), sum(diffWaveform) / lenWav))
		#import pdb;pdb.set_trace()
		visualiseArray(diffWaveform, True)



	def run(self):
		for waveform in self.waveforms:
			fourierTransform = fft.fft(waveform)
			self.getActiveNotes(self.noteList[28], fourierTransform, waveform)
			for note in self.noteList:
				activeNotes = self.getActiveNotes(note, fourierTransform, waveform)
			# [a.print() for a in intervalPropertyList[100].dataPoints]
			# visualiseArray(intervalPropertyList[100].fourierTransform, True)
