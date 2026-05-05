from abc import ABC, abstractmethod


class PromptStrategy(ABC):

    @abstractmethod
    def build(self, context: str, question: str) -> str:
        pass


class SimpleRAGPrompt(PromptStrategy):

    def build(self, context: str, question: str) -> str:
        return f"""
以下のコードを参考に質問に答えてください。

# Context
{context}

# Question
{question}
"""


class CodeExplainPrompt(PromptStrategy):

    def build(self, context: str, question: str) -> str:
        return f"""
以下のPythonコードをわかりやすく説明してください。

# Code
{context}

# Question
{question}
"""


class QAPrompt(PromptStrategy):

    def build(self, context: str, question: str) -> str:
        return f"""
以下の情報だけを使って質問に答えてください。

# Context
{context}

# Question
{question}

# Answer
"""


STRATEGIES = {
    "simple": SimpleRAGPrompt,
    "qa": QAPrompt,
    "explain": CodeExplainPrompt,
}

class PromptFactory:
    @staticmethod
    def get(name: str):
        return STRATEGIES.get(name, SimpleRAGPrompt)()