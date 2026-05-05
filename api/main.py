import psycopg2
import os
from application.services.search_service import SearchService
from application.services.search_strategy import SearchFactory
from infrastructure.llm.ollama_client import OllamaClient
from application.services.prompt_builder import PromptFactory
from infrastructure.repository.experiment_repository import ExperimentRepository
from application.services.experiment_service import ExperimentService
from application.services.history_service import HistoryService
from fastapi import FastAPI

llm = OllamaClient()
app = FastAPI()

@app.get("/")
def health():
    return {"status": "ok"}

def get_connection():
    return psycopg2.connect(
        host=os.environ["POSTGRES_HOST"],
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
    )

@app.get("/db-check")
def db_check():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT 1;")
    result = cur.fetchone()
    cur.close()
    conn.close()
    return {"result": result}


@app.get("/documents")
def get_documents():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT content FROM documents LIMIT 5;")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return {"data": rows}


@app.get("/search")
def search(q: str):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT file_path, content
        FROM documents
        WHERE content_tsv @@ to_tsquery(%s)
    """, (q,))

    rows = cur.fetchall()

    cur.close()
    conn.close()

    return {"result": rows}


@app.get("/search/like")
def search_like(q: str):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT file_path, content
        FROM documents
        WHERE content ILIKE %s
        LIMIT 10
    """, (f"%{q}%",))

    rows = cur.fetchall()
    cur.close()
    conn.close()

    return {"result": rows}


@app.get("/search/ts")
def search_ts(q: str):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT file_path, content,
               ts_rank(content_tsv, plainto_tsquery(%s)) AS score
        FROM documents
        WHERE content_tsv @@ plainto_tsquery(%s)
        ORDER BY rank DESC
        LIMIT 10
    """, (q, q))

    rows = cur.fetchall()
    cur.close()
    conn.close()

    return {"result": rows}


@app.get("/search/trgm")
def search_trgm(q: str):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT file_path, content,
               similarity(content, %s) AS score
        FROM documents
        WHERE content %% %s
        ORDER BY score DESC
        LIMIT 10
    """, (q, q))

    rows = cur.fetchall()
    cur.close()
    conn.close()

    return {"result": rows}

def to_pgvector(vec):
    return "[" + ",".join(map(str, vec)) + "]"

@app.get("/search/vector")
def search_vector(q: str):
    conn = get_connection()
    cur = conn.cursor()

    query_vec = llm.embed(q)
    query_vec_str = to_pgvector(query_vec)

    cur.execute("""
        SELECT content,
            1 - (embedding <=> %s::vector) AS score
        FROM documents
        ORDER BY score DESC
        LIMIT 3
    """, (query_vec_str,))

    rows = cur.fetchall()
    cur.close()
    conn.close()

    return {"result": rows}


@app.get("/llm-test")
def llm_test(q: str):
    response = llm.generate(q)
    return {"response": response}


@app.get("/rag")
def rag(q: str, search_type="vector", prompt_type="simple"):

    try:
        conn = get_connection()

        search_strategy = SearchFactory.get(search_type, conn, llm)
        prompt_strategy = PromptFactory.get(prompt_type)
        
        exp_repo = ExperimentRepository(conn)
        history_service = HistoryService(exp_repo)

        search_service = SearchService(
            search_strategy,
            prompt_strategy,
            llm,
            history_service
        )

        exp_service = ExperimentService(
            search_service,
            exp_repo
        )

        result = exp_service.run(q, search_type, prompt_type)

        conn.close()

        return {
            "answer": result["answer"],
            "latency_ms": result["latency_ms"],
            "documents": [
                {"content": d.content, "score": d.score}
                for d in result["docs"]
            ]
        }

    except Exception as e:
        return {
            "error": str(e)
        }
    finally:
        conn.close()
        

@app.get("/logs")
def get_logs():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, question, answer, latency_ms, created_at
        FROM experiment_logs
        ORDER BY created_at DESC
        LIMIT 20
    """)

    rows = cur.fetchall()
    cur.close()
    conn.close()

    return {
        "logs": [
            {
                "id": r[0],
                "question": r[1],
                "answer": r[2],
                "latency_ms": r[3],
                "created_at": r[4]
            }
            for r in rows
        ]
    }
    

@app.get("/logs/{log_id}")
def get_log_detail(log_id: str):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT *
        FROM experiment_logs
        WHERE id = %s
    """, (log_id,))

    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row:
        return {"error": "not found"}

    return {
        "id": row[0],
        "question": row[1],
        "search_mode": row[2],
        "prompt_mode": row[3],
        "search_results": row[9],
        "prompt": row[10],
        "answer": row[12],
        "latency_ms": row[13]
    }