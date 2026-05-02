import os
import psycopg2
from fastapi import FastAPI

app = FastAPI()

def get_connection():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST"),
        dbname=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD")
    )

# =================
# tsvector検索
# =================
def search_documents(query: str):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            id,
            repo_name,
            file_path,
            content,
            ts_rank(content_tsv, plainto_tsquery('simple', %s)) AS score
        FROM documents
        WHERE content_tsv @@ plainto_tsquery('simple', %s)
        LIMIT 5;
    """, (query, query))

    rows = cur.fetchall()

    results = []
    for row in rows:
        results.append({
            "id": str(row[0]),
            "repo_name": row[1],
            "file_path": row[2],
            "content": row[3],
            "score": float(row[4])
        })

    return results


@app.get("/search")
def search(q: str):
    results = search_documents(q)

    if len(results) == 0:
        return {
            "results": [],
            "message": "0件"
        }

    return {
        "results": results
    }
    
    
# ================
# LIKE検索
# ================
def search_documents_like(query: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT
            id,
            repo_name,
            file_path,
            content,
            0 AS score
        FROM documents
        WHERE content LIKE %s
        LIMIT 5;
    """, ('%' + query + '%',))

    rows = cur.fetchall()

    results = []
    for row in rows:
        results.append({
            "id": str(row[0]),
            "repo_name": row[1],
            "file_path": row[2],
            "content": row[3],
            "score": float(row[4])
        })

    return results

@app.get("/search_like")
def search_like(q: str):
    results = search_documents_like(q)

    if len(results) == 0:
        return {
            "results": [],
            "message": "0件"
        }

    return {
        "results": results
    }