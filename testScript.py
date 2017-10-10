
from simpleMidiConverter import SimpleMidiConverter
from noteProcessors.discreteNoteProcessor.discreteNoteProcessor import DiscreteNoteProcessor
from noteProcessors.continuousNoteProcessor.continuousNoteProcessor import ContinuousNoteProcessor
from noteProcessors.discreteNoteProcessor.baseShapeStrategy import BaseShapeStrategy
from noteProcessors.discreteNoteProcessor.shapeStrategies import FilterShapeStrategy

smc = SimpleMidiConverter(fileName="audio/Ltheme2Modified.wav", noteProcessor=ContinuousNoteProcessor)
#smc = SimpleMidiConverter(fileName="audio/Ltheme2Modified.wav", noteProcessor=DiscreteNoteProcessor, shapeStrategy=FilterShapeStrategy)
smc.run()

notes = [n for n in smc.activeNotes if n.note.frequency < 1760]
for note in notes:
	note.print()
