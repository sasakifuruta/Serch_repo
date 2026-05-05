import psycopg2
import os
import uuid
import ast
import json

from api.parser import parse_python
from infrastructure.llm.ollama_client import OllamaClient

llm = OllamaClient()

DATA_DIR = "data"
print("CWD:", os.getcwd())
print("DATA_DIR:", os.path.abspath(DATA_DIR))

def load_python_files():
    files = []
    for filename in os.listdir(DATA_DIR):
        if filename.endswith(".py"):
            files.append(os.path.join(DATA_DIR, filename))
    return files


def get_connection():
    return psycopg2.connect(
        host=os.environ["POSTGRES_HOST"],
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
    )

def clear_documents(cur):
    cur.execute("DELETE FROM documents;")

def insert_chunk(cur, chunk):
    vector = llm.embed(chunk["content"])

    cur.execute("""
        INSERT INTO documents (
            id,
            file_path,
            chunk_type,
            function_name,
            class_name,
            content,
            content_tsv,
            embedding
        )
        VALUES (%s, %s, %s, %s, %s, %s, to_tsvector('english', %s), %s)
    """, (
        str(uuid.uuid4()),
        chunk["file_path"],
        chunk["chunk_type"],
        chunk.get("function_name"),
        chunk.get("class_name"),
        chunk["content"],
        chunk["content"],
        vector
    ))


def main():
    conn = get_connection()
    cur = conn.cursor()

    # ① 既存データ削除
    clear_documents(cur)

    files = load_python_files()

    for file_path in files:
        with open(file_path, "r") as f:
            code = f.read()

        tree = ast.parse(code)

        chunks = parse_python(code, tree)

        for c in chunks:
            c["file_path"] = os.path.basename(file_path)
            insert_chunk(cur, c)

    conn.commit()
    cur.close()
    conn.close()

    print("ingest completed")


if __name__ == "__main__":
    main()