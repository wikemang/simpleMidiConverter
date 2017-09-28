import inspect
import json

from activeNote import ActiveNote
from simpleMidiConverter import SimpleMidiConverter
from noteProcessors.discreteNoteProcessor.discreteNoteProcessor import DiscreteNoteProcessor
from noteProcessors.discreteNoteProcessor.baseShapeStrategy import BaseShapeStrategy
from noteProcessors.discreteNoteProcessor.shapeStrategies import FilterShapeStrategy
import utils

# This is a sort of fuzzy regression test. 
# Gets all active notes from a Notes Processor and matches it with the old output from the same NoteProcessor.
# Does approximate time matching of the notes.

# If the new output is "more correct" than the old output, the old output can be replaced with the generateNewOutputFile() function.
# run() will run the tests. Currently waiting to write unit tests and refactor them together.


testProcessors = [
	{"noteProcessor": DiscreteNoteProcessor, "shapeStrategy": BaseShapeStrategy},
	{"noteProcessor": DiscreteNoteProcessor, "shapeStrategy": FilterShapeStrategy},
]
testFiles = ["audio/Ltheme.wav", "audio/Ltheme2.wav"]

LOUDNESS_THRESHOLD = ActiveNote.MAX_LOUDNESS / 10	# All notes must check out to this threshold.
TIME_THRESHOLD = 0.1 	# Time in seconds notes must check out to.

# Checks if a note can be found in the oldNotes list.
def doesExistNote(note, oldNotes):
	if note.loudness > LOUDNESS_THRESHOLD:
		index = utils.binSearch(oldNotes, lambda n: n['startTime'], note.startTime, fuzzy=True)
		# Search higher indices for similar startTimes
		searchIndex = index
		while abs(oldNotes[searchIndex]['startTime'] - note.startTime) < TIME_THRESHOLD:
			if checkNote(oldNotes[searchIndex], note):
				return True
			searchIndex -= 1

		# Search lower indices for similar startTimes
		searchIndex = index
		while abs(oldNotes[searchIndex]['startTime'] - note.startTime) < TIME_THRESHOLD:
			searchIndex += 1
			if checkNote(oldNotes[searchIndex], note):
				return True
	else:
		return True
	return False

# Does a fuzzy check to see if oldNote and newNote is the same
def checkNote(oldNote, newNote):
	if not (oldNote['note']['name'] == newNote.note.name):
		return False
	# Redundant check since this was a pre-condition for this function call
	if not (abs(oldNote['startTime'] - newNote.startTime) < TIME_THRESHOLD):
		return False
	if not (abs(oldNote['endTime'] - newNote.endTime) < TIME_THRESHOLD):
		return False
	if not (abs(oldNote['loudness'] - newNote.loudness) < LOUDNESS_THRESHOLD):
		return False
	return True

def truncateFilename(fileName):
	return fileName[fileName.rindex("/") + 1 : fileName.rindex(".")]

def argsToString(**kwargs):
	string = ""
	for key in sorted(kwargs.keys(), key=lambda x: x[0]):
		string += "_" + kwargs[key].__name__
	return string

def readNotesFromResource(fileName):
	notes = []
	with open(fileName, "r") as f:
		data = json.load(f)
		notes = data["notes"]
	return notes

def toDict(ref):
	dictObject = {}
	for key, value in (ref.__dict__).items():
		if hasattr(value, '__dict__'):
			dictObject[key] = toDict(value)
		else:
			dictObject[key] = value
	return dictObject

def generateNewOutputFile(fileName, newNotes=None, **kwargs):
	newNotes = [toDict(note) for note in newNotes]
	with open(fileName, "w") as f:
		f.write(json.dumps({"notes" : newNotes}, indent=4))

def run():
	for processorArgs in testProcessors:
		for fileName in testFiles:
			smc = SimpleMidiConverter(fileName=fileName, **processorArgs)
			newNotes = smc.getNotes()
			resourceName = truncateFilename(fileName) + argsToString(**processorArgs) + ".json"
			oldResourceName = "tests/oldTestResources/" + resourceName
			newResourceName = "tests/newTestResources/" + resourceName
			oldNotes = readNotesFromResource(oldResourceName)
			oldNotes.sort(key=lambda note: note['startTime'])
			match = True
			for note in newNotes:
				if not doesExistNote(note, oldNotes):
					match = False
					break
			if not match:
				print("Note processors have produced different results. New test resource generated: %s" % newResourceName)
				generateNewOutputFile(newResourceName, newNotes=newNotes, **processorArgs)
