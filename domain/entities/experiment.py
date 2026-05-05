# domain/entities/experiment.py

import uuid
from datetime import datetime

class Experiment:

    def __init__(
        self,
        question: str,
        search_mode: str,
        prompt_mode: str,
        search_results: list,
        prompt: str,
        answer: str,
        llm_raw_output: str = "",
        latency_ms: int = 0,
        top_k: int = 3,
        search_config: dict = None,
        total_token: int = 0,
        user_token: int = 0,
        system_token: int = 0,
    ):
        self.id = str(uuid.uuid4())

        self.question = question
        self.search_mode = search_mode
        self.prompt_mode = prompt_mode

        self.search_results = search_results

        self.prompt = prompt
        self.answer = answer
        self.llm_raw_output = llm_raw_output

        self.latency_ms = latency_ms
        
        self.top_k = top_k
        self.search_config = search_config or {}
        self.total_token = total_token
        self.user_token = user_token
        self.system_token = system_token