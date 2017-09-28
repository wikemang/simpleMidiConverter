from noteParser import NoteParser
import utils

class AbstractNoteProcessor:
	def __init__(self, waveform, sampleRate, noteParser=None):
		self.waveform = waveform
		self.sampleRate = sampleRate
		self.noteParser = noteParser or NoteParser()
		self.noteList = self.noteParser.parseNotes()	# Parse list of all notes and their frequencies

	def getClosestNote(self, frequency):
		closestNote = None
		diffPercent = None

		i = utils.binSearch(self.noteList, lambda n: n.frequency, frequency, fuzzy=True)
		lowerNotePercent = frequency / self.noteList[i].frequency
		higherNotePercent = self.noteList[i + 1].frequency / frequency
		if lowerNotePercent < higherNotePercent:
			closestNote = self.noteList[i]
			diffPercent = lowerNotePercent
		else:
			closestNote = self.noteList[i + 1]
			diffPercent = 1 / higherNotePercent
		return closestNote, diffPercent

	def run(self):
		assert(False)
