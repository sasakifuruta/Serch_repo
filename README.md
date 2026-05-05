
ディレクトリ構成
```ruby
.
├── docker-compose.yml
├── .env

├── api/
│   ├── Dockerfile
│   ├── main.py          ← エントリポイント（超薄く）
│   └── routes.py        ← APIルーティング

├── application/
│   └── services/
│       ├── search_service.py
│       ├── prompt_builder.py
│       ├── history_formatter.py
│       └── experiment_service.py

├── domain/
│   └── entities/
│       ├── document.py
│       ├── message.py
│       └── experiment.py

├── infrastructure/
│   ├── repository/
│   │   ├── document_repository.py
│   │   ├── conversation_repository.py
│   │   └── experiment_repository.py
│   │
│   └── llm/
│       └── ollama_client.py
|
└── migrations/          ← DDL管理
```

## 検証環境準備
### 0. Docker Desktopのメモリ設定変更
初期設定（２GB）の場合、3GB以上に変更する

### 1. コンテナセットアップ
1. envファイル作成
```
POSTGRES_DB=search_repo
POSTGRES_USER=XXXXX
POSTGRES_PASSWORD=XXXXX
POSTGRES_HOST=XXXXX
OLLAMA_HOST=http://ollama:11434
```
2. docker compose up -d
3. docker compose ps
NAME                  IMAGE             COMMAND              SERVICE      PORTS
serch_repo-api-1      serch_repo-api    "uvicorn…"   api     0.0.0.0:8000->8000/tcp, [::]:8000->8000/tcp
serch_repo-ollama-1   ollama/ollama     "/bin/…"     ollama  0.0.0.0:11434->11434/tcp, [::]:11434->11434/tcp
serch_repo-postgres-1 ankane/pgvector:latest   "docker-…"   postgres   0.0.0.0:5432->5432/tcp, [::]:5432->5432/tcp

### 2. LLMセットアップ
1. docker compose logs ollama
2. docker compose exec ollama ollama pull phi
3. docker compose exec ollama ollama list
4. 確認
```
curl http://localhost:11434/api/generate -d '{
  "model": "phi",
  "prompt": "Hello",
  "stream": false
}'
```

1. docker compose exec ollama ollama pull nomic-embed-text


### 2. DBセットアップ
1. docker compose exec postgres psql -U <POSTGRES_USER> -d search_repo

2. 拡張機能の有効化
```
search_repo=#
CREATE EXTENSION IF NOT EXISTS pg_trgm;

search_repo=#
CREATE EXTENSION IF NOT EXISTS vector;
```

3. documentsテーブル作成
```
search_repo=#
CREATE TABLE documents (
  id UUID PRIMARY KEY,
  repo_name TEXT,
  file_path TEXT,

  chunk_type TEXT,
  function_name TEXT,
  class_name TEXT,

  content TEXT,
  docstring TEXT,
  imports TEXT,

  content_tsv tsvector,
  embedding vector(768)
);
```

4. インデックス作成
```
search_repo=#
CREATE INDEX idx_documents_tsv ON documents USING GIN(content_tsv);

search_repo=#
CREATE INDEX idx_documents_trgm ON documents USING GIN(content gin_trgm_ops);
```

5. ログテーブル作成
```
search_repo=#
CREATE TABLE experiment_logs (
  id UUID PRIMARY KEY,

  question TEXT,

  search_mode TEXT,
  prompt_mode TEXT,
  use_history BOOLEAN,
  history_mode TEXT,
  history_limit INT,

  top_k INT,
  chunk_type TEXT,
  search_config JSONB,

  search_results JSONB,

  prompt TEXT,
  llm_raw_output TEXT,
  answer TEXT,

  total_token INT,
  user_token INT,
  system_token INT,
  latency_ms INT,

  evaluation TEXT,
  notes TEXT,

  created_at TIMESTAMP DEFAULT NOW()
);
```
6. インデックス作成
```
search_repo=#
CREATE INDEX idx_search_mode ON experiment_logs(search_mode);


search_repo=#
CREATE INDEX idx_prompt_mode ON experiment_logs(prompt_mode);
```

### 3.初期データ投入
1. docker compose exec api python -m api.ingest
2. 確認
```
SELECT file_path, chunk_type, function_name
FROM documents;
```

