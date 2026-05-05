
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

└── migrations/          ← DDL管理
```