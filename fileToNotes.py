from wavParser import *
from noteParser import NoteParser
from midiWriter import MidiWriter
from noteProcessors.noteProcessor.noteProcessor import NoteProcessor

import time
import copy


class FileToNotes:
	def __init__(self, fileName, noteParser=None, noteProcessor=None, midiWriter=None):

		self.fileName = fileName
		self.noteParser = noteParser or NoteParser()

		self.midiWriter = midiWriter or MidiWriter(self.noteParser.parseNotes())

		print("Reading file...")
		t = time.clock()
		self.waveforms, self.sampleRate, _ = getRawWaveData(self.fileName)
		print("%f s" % (time.clock() - t))

		self.noteProcessor = noteProcessor or NoteProcessor(self.waveforms, self.sampleRate, self.noteParser)


	def resetProcessor(self, noteProcessor):
		self.noteProcessor = noteProcessor(self.waveforms, self.sampleRate, self.noteParser)


	def run(self):
		print("Getting notess...")
		t = time.clock()
		notes = self.noteProcessor.run()
		print("%f s" % (time.clock() - t))

		#note1 = ActiveNote(self.noteParser.parseNotes()[50], 1.2, 2.8, 50)
		#note2 = ActiveNote(self.noteParser.parseNotes()[60], 2.2, 4, 80)
		self.midiWriter.writeActiveNotesToFile(notes, self.fileName[:self.fileName.index(".")])
