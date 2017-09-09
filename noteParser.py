# NoteParse is a singleton and parses an html table of notes into memory.

class Note:
	def __init__(self, name, frequency):
		self.name = name
		self.frequency = frequency

class NoteParser:
	class __NoteParser:
		def __init__(self):
			self.notes = None

		def parseNotes(self):
			if self.notes != None:
				return self.notes
			data = None
			notes = []
			with open("notes.html", 'r') as f:
				data = f.read()	# Wav file metadata length. Should remain this till the end of time.
			rows = data.split("<tr>")[1:]
			for row in rows:
				row = row.replace("<sub>", "")
				row = row.replace("</sub>", "")
				row = row.replace("</sup>", "")
				row = row.replace("<sup>", "")
				row = row.replace("&nbsp;", "")
				items = row.split("<td align=center>")
				name = items[1][:items[1].index("</td>")]
				frequency = float(items[2][:items[2].index("</td>")])
				notes.append(Note(name, frequency))
			self.notes = notes
			return notes

	def __init__(self):
		self.notes = None

	instance = None
	def __new__(cls):
		if not NoteParser.instance:
			NoteParser.instance = NoteParser.__NoteParser()
		return NoteParser.instance

