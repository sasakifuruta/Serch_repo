# application/services/experiment_service.py

from domain.entities.experiment import Experiment

class ExperimentService:
    """
    RAG実行 + 実験ログ保存を担当
    """
    def __init__(self, search_service, repo):
        self.search_service = search_service
        self.repo = repo

    def run(self, query, search_type, prompt_type):

        result = self.search_service.execute(query)

        exp = Experiment(
            question=query,
            search_mode=search_type,
            prompt_mode=prompt_type,
            search_results=[
                {"content": d.content, "score": d.score}
                for d in result["docs"]
            ],
            prompt=result["prompt"],
            answer=result["answer"],
            llm_raw_output=result["answer"],
            latency_ms=result["latency_ms"],
            top_k=len(result["docs"]),
            search_config={
                "strategy": search_type
            }
        )

        self.repo.save(exp)

        return result