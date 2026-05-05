# infrastructure/repository/experiment_repository.py

import json

class ExperimentRepository:

    def __init__(self, conn):
        self.conn = conn

    def save(self, exp):
        cur = self.conn.cursor()

        cur.execute("""
            INSERT INTO experiment_logs (
                id,
                question,
                search_mode,
                prompt_mode,
                search_results,
                prompt,
                llm_raw_output,
                answer,
                latency_ms,
                top_k,
                search_config,
                total_token,
                user_token,
                system_token
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            exp.id,
            exp.question,
            exp.search_mode,
            exp.prompt_mode,
            json.dumps(exp.search_results),
            exp.prompt,
            exp.llm_raw_output,
            exp.answer,
            exp.latency_ms,
            exp.top_k,
            json.dumps(exp.search_config),
            exp.total_token,
            exp.user_token,
            exp.system_token
        ))

        self.conn.commit()
        cur.close()
        
        
    def find_recent(self, limit=3):
        cur = self.conn.cursor()

        cur.execute("""
            SELECT question
            FROM experiment_logs
            ORDER BY created_at DESC
            LIMIT %s
        """, (limit,))

        rows = cur.fetchall()
        cur.close()

        return [r[0] for r in rows]