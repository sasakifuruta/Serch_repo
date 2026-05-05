from infrastructure.repository.document_repository import DocumentRepository
from domain.entities.document import Document
from abc import ABC, abstractmethod


class SearchStrategy(ABC):

    @abstractmethod
    def search(self, query: str) -> list[Document]:
        pass
    

class VectorSearch(SearchStrategy):

    def __init__(self, repo, llm):
        self.repo = repo
        self.llm = llm

    def search(self, query: str) -> list[Document]:
        vec = self.llm.embed(query)
        vec_str = "[" + ",".join(map(str, vec)) + "]"

        return self.repo.find_similar_by_vector(vec_str)    


class TSSearch(SearchStrategy):

    def __init__(self, repo):
        self.repo = repo

    def search(self, query: str) -> list[Document]:
        return self.repo.find_by_tsquery(query)
    

class HybridSearch(SearchStrategy):

    def __init__(self, repo, llm):
        self.repo = repo
        self.llm = llm

    def search(self, query: str) -> list[Document]:
        vec = self.llm.embed(query)
        vec_str = "[" + ",".join(map(str, vec)) + "]"

        vec_docs, ts_docs = self.repo.find_hybrid_candidates(vec_str, query)

        scores = {}

        for doc in vec_docs:
            scores[doc] = scores.get(doc, 0) + doc.score * 0.7

        for doc in ts_docs:
            scores[doc] = scores.get(doc, 0) + doc.score * 0.3

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        return [c for c, _ in ranked[:3]]
    

STRATEGIES = {
    "vector": VectorSearch,
    "ts": TSSearch,
    "hybrid": HybridSearch,
}

class SearchFactory:
    @staticmethod
    def get(name: str, conn, llm):
        repo = DocumentRepository(conn)
        cls = STRATEGIES.get(name, VectorSearch)
        
        if cls == TSSearch:
            return cls(repo)
        return cls(repo, llm)