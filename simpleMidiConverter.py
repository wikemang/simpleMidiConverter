import time
import copy

from noteParser import NoteParser
from noteProcessors.discreteNoteProcessor.discreteNoteProcessor import DiscreteNoteProcessor
from midiWriter import MidiWriter
from wavParser import SimpleWavParser


class SimpleMidiConverter:
	def __init__(self, fileName, fileReader=None, noteParser=None, noteProcessor=None, midiWriter=None, **kwargs):

		self.fileName = fileName
		self.fileReader = fileReader or SimpleWavParser()
		self.noteParser = noteParser or NoteParser()

		self.midiWriter = midiWriter or MidiWriter(self.noteParser.parseNotes())
		self.noteProcessor = noteProcessor or DiscreteNoteProcessor
		self.noteProcessorArgs = kwargs
		self.activeNotes = []

	def getNotes(self):
		print("Reading file...")
		t = time.clock()
		self.waveform, self.sampleRate, _ = self.fileReader.getSingleWaveform(self.fileName)
		print("%f s" % (time.clock() - t))

		# TODO refactor this
		self.noteProcessor = self.noteProcessor(self.waveform, self.sampleRate, self.noteParser, **self.noteProcessorArgs)
		print("Getting notes...")
		t = time.clock()
		notes = self.noteProcessor.run()
		print("%f s" % (time.clock() - t))
		return notes

	def run(self):
		self.activeNotes = self.getNotes()
		self.midiWriter.writeActiveNotesToFile(self.activeNotes, self.fileName[:self.fileName.index(".")])
