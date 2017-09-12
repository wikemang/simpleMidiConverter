from noteParser import NoteParser

class AbstractNoteProcessor:
	def __init__(self, waveforms, sampleRate, noteParser=None):
		self.waveforms = waveforms
		self.sampleRate = sampleRate
		self.noteParser = noteParser or NoteParser()
		self.noteList = self.noteParser.parseNotes()	# Parse list of all notes and their frequencies

	def run(self):
		assert(False)
