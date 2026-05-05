# infrastructure/llm/ollama_client.py

import requests
import os
from .base import LLMClient

OLLAMA_HOST = os.environ["OLLAMA_HOST"]

class OllamaClient(LLMClient):

    def generate(self, prompt: str, model="phi") -> str:
        res = requests.post(
            f"{OLLAMA_HOST}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False
            },
            timeout=60
        )

        if res.status_code != 200:
            raise Exception(f"LLM error: {res.text}")

        return res.json()["response"]

    def embed(self, text: str, model="nomic-embed-text") -> list:
        res = requests.post(
            f"{OLLAMA_HOST}/api/embeddings",
            json={
                "model": model,
                "prompt": text
            },
            timeout=60
        )

        if res.status_code != 200:
            raise Exception(f"Embedding error: {res.text}")

        return res.json()["embedding"]