from domain.entities.document import Document
import time

class SearchService:

    def __init__(self, search_strategy, prompt_strategy, llm, history_service=None):
        self.search_strategy = search_strategy
        self.prompt_strategy = prompt_strategy
        self.llm = llm
        self.history_service = history_service

    def execute(self, query: str) -> dict:
        # ① Document取得
        docs: list[Document] = self.search_strategy.search(query)

        # ② Document → context
        context = "\n\n".join([doc.content for doc in docs])
        
        # 👇 履歴追加
        history_context = ""
        if self.history_service:
            history_context = self.history_service.get_context(limit=3)

        full_context = f"""
        {history_context}

        # Retrieved Context
        {context}
        """
        # ③ prompt生成
        prompt = self.prompt_strategy.build(full_context, query)

        # ④ LLM
        start = time.time()
        answer = self.llm.generate(prompt)
        latency_ms = int((time.time() - start) * 1000)

        return {
            "answer": answer,
            "context": context,
            "prompt": prompt,
            "docs": docs,
            "latency_ms": latency_ms
        }