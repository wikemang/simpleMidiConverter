
from simpleMidiConverter import SimpleMidiConverter
from noteProcessors.discreteNoteProcessor.discreteNoteProcessor import DiscreteNoteProcessor
from noteProcessors.continuousNoteProcessor.continuousNoteProcessor import ContinuousNoteProcessor
from noteProcessors.discreteNoteProcessor.baseShapeStrategy import BaseShapeStrategy
from noteProcessors.discreteNoteProcessor.shapeStrategies import FilterShapeStrategy

#a = SimpleMidiConverter(fileName="audio/Ltheme2Modified.wav", noteProcessor=ContinuousNoteProcessor)
# BaseShapeStrategy does a direct conversion from frequency to notes.
a = SimpleMidiConverter(fileName="audio/Ltheme2Modified.wav", noteProcessor=DiscreteNoteProcessor, shapeStrategy=FilterShapeStrategy)
a.run()

notes = [n for n in a.activeNotes if n.note.frequency < 1760]
for note in notes:
	note.print()
