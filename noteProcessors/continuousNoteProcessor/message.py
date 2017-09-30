
class MessageType:
	NO_EVENT = 0
	NEW_NOTE = 1
	NEW_FRAME = 2

class Message:
	def __init__(self, messageType):
		self.messageType = messageType

# This message should tell that a new note be created with the parameters
class NewNoteMessage(Message):
	def __init__(self, startIndex, endIndex, note, loudness, centerFrequencyIndex):
		self.startIndex = startIndex
		self.endIndex = endIndex
		self.note = note
		self.loudness = loudness
		self.centerFrequencyIndex = centerFrequencyIndex
		super(NewNoteMessage, self).__init__(MessageType.NEW_NOTE)
