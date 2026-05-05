class HistoryService:

    def __init__(self, repo):
        self.repo = repo

    def get_context(self, limit=3) -> str:
        questions = self.repo.find_recent(limit)

        if not questions:
            return ""

        history_text = "\n".join([
            f"- {q}" for q in questions
        ])

        return f"""
# Conversation History
{history_text}
"""