
from simpleMidiConverter import SimpleMidiConverter
from noteProcessors.noteProcessor.noteProcessor import NoteProcessor
from noteProcessors.noteProcessor.baseShapeStrategy import BaseShapeStrategy
from noteProcessors.noteProcessor.shapeStrategies import FilterShapeStrategy

a = SimpleMidiConverter(fileName="audio/Ltheme.wav", noteProcessor=NoteProcessor, shapeStrategy=FilterShapeStrategy)
# BaseShapeStrategy does a direct conversion from frequency to notes.
# a = SimpleMidiConverter(fileName="audio/Ltheme.wav", noteProcessor=NoteProcessor, shapeStrategy=BaseShapeStrategy)
a.run()

