
class ActiveNote:
	def __init__(self, note, startTime, endTime, loudness):
		self.note = note
		self.startTime = startTime
		self.endTime = endTime
		self.loudness = loudness

	def print(self):
		print("Note: %f \tStart: %f \t End: %f \tLoudness: %f" % ((self.note.name + "  " + int(self.note.frequency)).ljust(15), self.start, closestNote.end, self.loudness))

	@classmethod
	def printList(cls, noteList):
		for note in noteList:
			note.print()

	@classmethod
	def sortList(cls, noteList):
		noteList.sort(key=lambda x: x.startTime)

	@classmethod
	def getMaxLoudness(cls):
		return 120
