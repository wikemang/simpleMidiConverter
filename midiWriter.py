# http://www.music.mcgill.ca/~ich/classes/mumt306/StandardMIDIfileformat.html

from enum import Enum

from activeNote import ActiveNote

class MidiEventType(Enum):
	NOTE_START = 1
	NOTE_END = 2

class MidiEvent:
	def __init__(self, noteValue, velocity, startTime, eventType):
		self.noteValue = noteValue
		self.velocity = velocity
		self.startTime = startTime
		self.eventType = eventType
		self.timeFromLastEvent = None

	def setTimeFromLastEvent(self, timeFromLastEvent):
		self.timeFromLastEvent = timeFromLastEvent


# Simple MidiWriter.
# Currently writes only in the "time-code-based" format, using 1000 ticks per second.
class MidiWriter:
	# MAX_NOTE_VELOCITY currently corresponds to what Synthesia uses as the maximum note velocity
	MAX_NOTE_VELOCITY = 120

	def __init__(self, notes):
		self.activeNotes = None
		self.fileName = None
		self.notes = notes

	# Taken from midi docs
	def varLen(self, number):
		buffer = number & 0x7f
		number >>= 7
		while number > 0:
			buffer <<= 8
			buffer |= 0x80
			buffer += (number & 0x7f)
			number >>= 7

		b = []
		while True:
			val = buffer % 256
			b.append(val)
			if buffer & 0x80:
				buffer >>= 8
			else:
				break
		return b

	def getTwosComplement(self, value, bits):
		if value >= 0:
			return value
		else:
			flipped = "0b" + "".join(['1' if c == '0' else '0' for c in (bin(value)[3:]).zfill(bits)])
			return int(flipped, 2) + 1

	# Currently hard coded to be 1000 ticks per second
	def getTimeDivision(self):
		# 1000 ticks per second
		format = 1
		frames = self.getTwosComplement(-25, 7)
		ticksPerFrame = 40
		return [(format << 7) + frames, ticksPerFrame]


	def getHeader(self):
		bytes = []
		for c in "MThd":
			bytes.append(ord(c))
		bytes.extend([0, 0, 0, 6])
		bytes.append(0)	# Format, single track
		bytes.append(0)
		bytes.append(0) # Number of tracks
		bytes.append(1)

		bytes.extend(self.getTimeDivision())
		return bytes


	def getBody(self, midiEvents):
		bytes = []
		for c in "MTrk":
			bytes.append(ord(c))
		bytes.extend([0, 0, 0, 0])	# Placeholder for length

		channel = 0
		for midiEvent in midiEvents:
			bytes.extend(self.varLen(midiEvent.timeFromLastEvent))
			if midiEvent.eventType == MidiEventType.NOTE_START:
				bytes.append((9 << 4 ) + channel)
			elif midiEvent.eventType == MidiEventType.NOTE_END:
				bytes.append((8 << 4 ) + channel)

			bytes.append(midiEvent.noteValue)
			bytes.append(midiEvent.velocity)

		# Write total length of data to the placeholder reserved for length
		length = len(bytes) - 8
		for i in range(4):
			bytes[7 - i] = length % 256
			length >>= 8

		return bytes

	# Generate list of MidiEvents from ActiveNotes
	def processEvents(self, activeNotes):
		events = []
		indexOffset = 12 # Index offset of parsed notes from midi notes.
		for activeNote in activeNotes:
			noteValue = self.notes.index(activeNote.note) + indexOffset
			velocity = int(activeNote.loudness / ActiveNote.MAX_LOUDNESS * MidiWriter.MAX_NOTE_VELOCITY)
			events.append(MidiEvent(noteValue, velocity, int(activeNote.startTime * 1000), MidiEventType.NOTE_START))
			events.append(MidiEvent(noteValue, velocity, int(activeNote.endTime * 1000), MidiEventType.NOTE_END))
		events.sort(key=lambda x: x.startTime)
		lastStartTime = 0
		# Midi specification requires us to specify each notes' time relative to last event, instead of absolute time.
		for event in events:
			event.setTimeFromLastEvent(event.startTime - lastStartTime)
			lastStartTime = event.startTime
		return events

	def writeActiveNotesToFile(self, activeNotes, fileName):
		midiEvents = self.processEvents(activeNotes)

		self.fileName = fileName
		with open("out/" + self.fileName.split("/")[-1] + ".midi", 'bw') as f:
			f.write(bytearray(self.getHeader()))
			f.write(bytearray(self.getBody(midiEvents)))
