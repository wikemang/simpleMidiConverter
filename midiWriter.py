from activeNote import ActiveNote

class MidiEvent:
	def __init__(self, noteValue, velocity, startTime, eventType):
		self.noteValue = noteValue
		self.velocity = velocity
		self.startTime = startTime
		self.eventType = eventType
		self.timeFromLastEvent = None

	def setTimeFromLastEvent(self, timeFromLastEvent):
		self.timeFromLastEvent = timeFromLastEvent


class MidiWriter:

	def __init__(self, notes):
		self.activeNotes = None
		self.fileName = None
		self.notes = notes

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


	def getTimeDivision(self):
		# 1000 ticks per second
		format = 1
		frames = self.getTwosComplement(-25, 7)
		ticks = 40
		return [(format << 7) + frames, ticks]


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
		bytes.extend([0, 0, 0, 0])	#Placeholder for length

		channel = 0
		for midiEvent in midiEvents:
			if midiEvent.noteValue < 0 or midiEvent.noteValue > 255:
				continue
			bytes.extend(self.varLen(midiEvent.timeFromLastEvent))
			if midiEvent.eventType == "start":
				bytes.append((9 << 4 ) + channel)
			elif midiEvent.eventType == "end":
				bytes.append((8 << 4 ) + channel)

			bytes.append(midiEvent.noteValue)
			bytes.append(midiEvent.velocity)


		# Temp code to test using Synthesia TODO: remove
		deltaTime2 = 100000
		bytes.extend(self.varLen(deltaTime2))
		bytes.append((9 << 4) + 0)
		bytes.append(60)
		bytes.append(80)
		bytes.extend(self.varLen(deltaTime2))
		bytes.append((8 << 4) + 0)
		bytes.append(60)
		bytes.append(0)

		length = len(bytes) - 8
		for i in range(4):
			bytes[7 - i] = length % 256
			length >>= 8

		a = [b for b in bytes if b < 0 or b > 256]
		d = [b for b in range(len(bytes)) if bytes[b] < 0 or bytes[b] > 256]
		return bytes

	def processEvents(self, activeNotes):
		events = []
		indexOffset = 12 # Index offset of parsed notes from midi notes
		for activeNote in activeNotes:
			noteValue = self.notes.index(activeNote.note) + indexOffset
			velocity = int(activeNote.loudness / ActiveNote.getMaxLoudness() * 100)
			events.append(MidiEvent(noteValue, velocity, int(activeNote.startTime * 1000), "start"))
			events.append(MidiEvent(noteValue, velocity, int(activeNote.endTime * 1000), "end"))
		events.sort(key=lambda x: x.startTime)
		lastStartTime = 0
		for event in events:
			event.setTimeFromLastEvent(event.startTime - lastStartTime)
			lastStartTime = event.startTime
		return events

	def writeActiveNotesToFile(self, activeNotes, fileName):
		midiEvents = self.processEvents(activeNotes)

		self.fileName = fileName
		with open(self.fileName + ".midi", 'bw') as f:
			f.write(bytearray(self.getHeader()))
			f.write(bytearray(self.getBody(midiEvents)))
