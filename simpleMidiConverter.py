import time
import copy

from noteParser import NoteParser
from noteProcessors.noteProcessor.noteProcessor import NoteProcessor
from midiWriter import MidiWriter
from wavParser import SimpleWavParser


class SimpleMidiConverter:
	def __init__(self, fileName, fileReader=None, noteParser=None, noteProcessor=None, midiWriter=None, **kwargs):

		self.fileName = fileName
		self.fileReader = fileReader or SimpleWavParser()
		self.noteParser = noteParser or NoteParser()

		self.midiWriter = midiWriter or MidiWriter(self.noteParser.parseNotes())
		self.noteProcessor = noteProcessor or NoteProcessor
		self.noteProcessorArgs = kwargs



	def run(self):
		print("Reading file...")
		t = time.clock()
		self.waveforms, self.sampleRate, _ = self.fileReader.getRawData(self.fileName)
		print("%f s" % (time.clock() - t))

		# TODO refactor this
		self.noteProcessor = self.noteProcessor(self.waveforms, self.sampleRate, self.noteParser, **self.noteProcessorArgs)
		print("Getting notes...")
		t = time.clock()
		notes = self.noteProcessor.run()
		print("%f s" % (time.clock() - t))
		self.midiWriter.writeActiveNotesToFile(notes, self.fileName[:self.fileName.index(".")])
