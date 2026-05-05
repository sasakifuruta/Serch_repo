from domain.entities.document import Document


class DocumentRepository:

    def __init__(self, conn):
        self.conn = conn

    def find_similar_by_vector(self, vec_str: str, limit=3):
        cur = self.conn.cursor()

        cur.execute("""
            SELECT content, 
                1 - (embedding <=> %s::vector) AS score
            FROM documents
            ORDER BY score DESC
            LIMIT %s
        """, (vec_str, limit))

        rows = cur.fetchall()
        cur.close()

        return [Document(content=r[0], score=r[1]) for r in rows]


    def find_by_tsquery(self, query: str, limit=3):
        cur = self.conn.cursor()

        cur.execute("""
            SELECT content,
                ts_rank(content_tsv, plainto_tsquery(%s)) AS score
            FROM documents
            WHERE content_tsv @@ plainto_tsquery(%s)
            LIMIT %s
        """, (query, limit))

        rows = cur.fetchall()
        cur.close()

        return [Document(content=r[0], score=r[1]) for r in rows]


    def find_hybrid_candidates(self, vec_str: str, query: str):
        cur = self.conn.cursor()

        # vector
        cur.execute("""
            SELECT content,
                   1 - (embedding <=> %s::vector) AS score
            FROM documents
            LIMIT 10
        """, (vec_str,))
        vec_rows = cur.fetchall()

        # ts
        cur.execute("""
            SELECT content,
                   ts_rank(content_tsv, plainto_tsquery(%s)) AS score
            FROM documents
            WHERE content_tsv @@ plainto_tsquery(%s)
            LIMIT 10
        """, (query, query))
        ts_rows = cur.fetchall()

        cur.close()
        
        vec_docs = [Document(content=r[0], score=r[1]) for r in vec_rows]
        ts_docs = [Document(content=r[0], score=r[1]) for r in ts_rows]

        return vec_docs, ts_docs