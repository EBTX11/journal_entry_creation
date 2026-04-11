class JournalEntry:
    def __init__(self, tag, index, year, title, desc):
        self.tag = tag
        self.index = index
        self.year = year
        self.title = title
        self.desc = desc

    @property
    def key(self):
        return f"{self.tag}_je_{self.index}"