# infrastructure/llm/base.py

from abc import ABC, abstractmethod

class LLMClient(ABC):

    @abstractmethod
    def generate(self, prompt: str) -> str:
        pass

    @abstractmethod
    def embed(self, text: str) -> list:
        pass