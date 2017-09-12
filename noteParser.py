# NoteParse is a singleton and parses an html table of notes into memory.
# notes.html is from https://pages.mtu.edu/~suits/notefreqs.html

class Note:
	def __init__(self, name, frequency):
		self.name = name
		self.frequency = frequency

class NoteParser:
	class __NoteParser:
		def __init__(self):
			self.notes = []

		def parseNotes(self):
			if self.notes != []:
				return self.notes
			data = None
			with open("notes.html", 'r') as f:
				data = f.read()
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
				self.notes.append(Note(name, frequency))
			return self.notes

	def __init__(self):
		self.notes = None

	instance = None
	def __new__(cls):
		if not NoteParser.instance:
			NoteParser.instance = NoteParser.__NoteParser()
		return NoteParser.instance

