class Document:

    def __init__(self, content: str, score: float = 0):
        self.content = content
        self.score = score

    def __repr__(self):
        return f"Document(content={self.content[:30]}...)"

    def __hash__(self):
        return hash(self.content)

    def __eq__(self, other):
        return isinstance(other, Document) and self.content == other.content