# 社内gitリポジトリ横断検索RAGシステム（PoC版）　設計メモ
## 1. 目的

社内Organizationに属するGitリポジトリを横断検索し、
README・設定ファイル・ディレクトリ構成・ソースコードおよびコメントを根拠に回答するRAGシステムを構築する。


### ゴール

- 1〜2リポジトリを対象にPoCを実施
- 検索結果を根拠にLLMが回答
- 検索結果が0件の場合はLLMを呼び出さず、明示的に以下を返す

```
回答根拠となる検索結果が０件です
```

## 2. スコープ
### 対象リポジトリ
- 特定Organization配下の社内リポジトリ
- まずは1〜2リポジトリで検証

### 検索対象ファイル
- README（.md）
- ソースコード（.py など）
- 設定ファイル（.yml, .yaml, .json, .toml など）
- Dockerfile
- 環境変数ファイル等
※ UTF-8で読み込む

### 除外対象
- .git
- node_modules
- バイナリファイル
- 1MB以上の巨大ファイル

## 3. アーキテクチャ
### 構成（Docker Compose）
- postgres
- api（FastAPI）
- ollama（ローカルLLM）

```
POSTGRES_HOST=postgres
POSTGRES_DB=search_repo
POSTGRES_USER=app
POSTGRES_PASSWORD=sample
OLLAMA_HOST=http://ollama:11434
```

### データフロー
```
User
  ↓
FastAPI
  ↓
PostgreSQL（全文検索）
  ↓
検索結果0件？ → Yes → 即レスポンス返却
  ↓ No
Ollama（LLM）
  ↓
回答返却
```
### 設計方針
- LLMは検索結果が存在する場合のみ呼び出す
- 推測回答は禁止
- 検索がシステムの主役、LLMは補助

## 4. チャンク単位
チャンク単位は「ファイル単位」とする

理由:
- コードは文単位では意味が分断される
- 実装が単純
- 将来的に関数単位へ分割可能

## 5. データベース設計
### ・テーブル名: documents
### ・カラム定義

|カラム名|型|説明|
|---|---|---|
|id|uuid|主キー(Python側でuuid4()生成)|
|repo_name|text|リポジトリ名|
|file_path|text|ファイルパス|
|file_type|text|拡張子|
|content|text|ファイル内容|
|content_tsv|tsvector|全文検索用|
|indexed_at|timestamp|インデックス日時|

例：
```ruby::sql
CREATE TABLE documents (
  id UUID PRIMARY KEY,
  repo_name TEXT NOT NULL,
  file_path TEXT NOT NULL,
  file_type TEXT NOT NULL,
  content TEXT NOT NULL,
  content_tsv tsvector NOT NULL,
  indexed_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_documents_tsv
ON documents
USING GIN (content_tsv);

CREATE INDEX idx_documents_repo
ON documents (repo_name);
```

>[memo]
>tsvectorとは?
<br>
> PostgreSQLの全文検索機能におけるデータ型。
> 全文検索用に、正規化したデータ型を指す。to_tsvector関数の設定に応じて単語に分解、小文字・語幹化（例：powerful→power）できる。（語幹化することで表記揺れに対応できる。）今回は、分解・小文字化のみ。


### ・インデックス
- GIN(content_tsv)
- btree(repo_name)
- tsvector生成

tsvector生成方法：
INSERT時にアプリ側で to_tsvector を実行して保存する
```
to_tsvector('simple', content)
```
Poc版では、言語的解釈をせずにチューニング要素を少なくするために'simple'を使う。


>[memo]GINとは？
<br>
>tsvector専用のインデックス。
>検索対象の単語を含む行番号を一覧で返す。大量データでも高速な検索が可能。高速な検索ができる代わりにデータの追加・更新には時間がかかる。
> 例えると、
> LIKE検索は、本の全ページをめくって　単語を探すこと。
> GINインデックスは、巻末の「索引」をひくこと。
> このシステムでは、検索対象の単語を含むソースコード行の絞り込みに使用する。


>[memo]btreeとは？
<br>
>単語分解しない通常の一致検索。
> このシステムでは、リポジトリの絞り込みに使用する。




## 6. 検索設計

### 検索クエリ
```
SELECT
  id,
  repo_name,
  file_path,
  ts_rank(content_tsv, plainto_tsquery('simple', :query)) AS score
FROM documents
WHERE content_tsv @@ plainto_tsquery('simple', :query)
AND (:repo_name IS NULL OR repo_name = :repo_name)
ORDER BY score DESC
LIMIT 5;
```
### クエリ方針
- plainto_tsquery を使用
- ts_rank関数で出力したスコア順で上位5件取得
- repo_nameによる絞り込み可能

>[memo]plainto_tsquery とは?
<br>
>ユーザーが入力した自然言語の文章を、全文検索用の「検索クエリ（tsquery型）」に自動で変換する関数。SQL の ORDER BY で並び変えに反映できる。
>Poc版では、言語的解釈をせずにチューニング要素を少なくするために'simple'を使う。

>[memo]ts_rankとは？
>検索したい単語の出現頻度（とその重み）に応じてスコアを算出する関数。

### 件数
- LIMIT 5（固定）



### 0件時の挙動
- LLMは呼ばない
- 固定メッセージを返す

## 7. LLM設計
### モデル
- Ollama（Dockerコンテナ）
- ~~7B〜8Bクラスの量子化モデル~~
- tinyllama（軽量モデル）
Apple M3 / 24GB、Windows11 32GB両方で動作すること

### 呼び出し条件
- 検索結果が1件以上ある場合のみ

### プロンプト方針
- 検索結果のみを根拠に回答する
- 推測は禁止
- 根拠がない場合は指定文言を返す
- 検索結果は番号付きで提示

### プロンプトテンプレ定義

**システムプロンプト**
```
あなたは検索結果のみを根拠として回答するアシスタントです。

【厳守事項】
- 検索結果に記載された情報のみを使用する
- 推測・補完・一般知識の使用は禁止
- 根拠が存在しない場合は「該当する情報は見つかりませんでした。」と出力する
- 必ず根拠となる検索結果番号を明記する
```
**ユーザープロンプト**
```
# 質問
{user_question}

# 検索結果
{numbered_search_results}

# 出力形式
- 回答:
- 根拠: [使用した検索結果番号]
```
※フォーマット崩れでもそのまま返す

**検索結果フォーマット**
```
[1]
repo: xxx
path: xxx
score: 0.87
content:
<ファイル全文>

[2] 
{検索結果2}
[3] 
{検索結果3}
...
```




## 8. API設計
### エンドポイント : POST /ask
```ruby
--- リクエスト ---
{
  "question": "質問内容"
  "repo_name": "repoA" # 任意。指定時は該当repoのみ検索
}

--- レスポンス ---
{
  "answer": "回答",
  "sources": [
    {
      "repo": "...",
      "file_path": "...",
      "score": 0.87
    }
  ]
}
```
## 9. Git取り込み設計
### 方針
- Organizationのrepoをローカルにclone
- repo URLを手動で指定する
- 対象拡張子のみ抽出
- ファイル単位でDB登録
  - UTF-8で読み込む
  - 失敗したらスキップ

### 更新方法（PoC）
- 手動スクリプトで、予め全文をフルインデックスする
- 差分更新は「今後の拡張」とする

## 10. エラー設計

### 10.1 基本方針
- 異常系は明示的に分類する
- ユーザー起因とシステム起因を分離する
- 詳細な内部エラー情報はレスポンスに含めない
- ログには詳細を出力する
- PoCではリトライ制御は実装しない

### 10.2 ユーザー入力エラー
#### 10.2.1. 空文字入力
---
**条件**
- question が空文字または未指定
**対応**
- HTTP 400 Bad Request

レスポンス例
```
{
  "error": "質問が空です"
}
```

#### 10.2.2. 入力文字数超過
--- 
**条件**
- question が8,000文字を超える

**対応**
- HTTP 400 Bad Request

レスポンス例
```
{
  "error": "質問文字数が上限を超えています"
}
```

### 10.3 検索処理エラー
#### 10.3.1. データベース接続失敗
---
 **想定ケース**
- PostgreSQL未起動
- 接続拒否
- 認証失敗

**対応**
- HTTP 500 Internal Server Error

レスポンス例
```
{
  "error": "データベース接続エラー"
}
```
#### 10.3.2. 検索クエリ実行失敗

**想定ケース**
- SQLエラー
- tsquery変換失敗

**対応**
- HTTP 500 Internal Server Error

レスポンス例
```
{
  "error": "検索処理中にエラーが発生しました"
}
```

#### 10.3.3. 検索結果0件
---
**条件**
- 検索結果が0件

**対応**
- LLMは呼び出さない
- HTTP 200
- 固定メッセージを返却
```
回答根拠となる検索結果が０件です
```

### 10.4 LLM関連エラー
#### 10.4.1. LLM未接続
**想定ケース**
- Ollama未起動
- 接続不可

**対応**
- HTTP 500 Internal Server Error

レスポンス例
```
{
  "error": "LLMサービスに接続できません"
}
```
#### 10.4.2. LLMタイムアウト
---
**条件**
- 30秒以内に応答が返らない

**対応**
- HTTP 200
-固定メッセージを返却
```
LLM応答がタイムアウトしました
```

#### 10.4.3. LLM出力フォーマット崩れ
---
**方針**
- フォーマット検証は行わない
- LLM出力をそのまま返却する
- 再試行は行わない（PoCのため）

###　10.6 Git取り込みエラー
####　10.6.1. clone失敗
---
**想定ケース**
- 認証失敗
- リポジトリ不存在

**対応**
- 起動時にエラーとして停止
- ログ出力
- APIは起動しない

####　10.6.2.インデックス処理中のファイルエラー
---
**想定ケース**
- 文字コードエラー
- 巨大ファイル
- 読み込み失敗

**対応**
- 失敗したらスキップ
- 処理は続行

### 10.7 ログ設計（PoC方針）
- すべての500系エラーはログ出力
- LLMタイムアウトはWARNINGレベル
- ファイルスキップはINFOレベル
- スタックトレースはログにのみ出力


## 11.  非機能要件（PoCレベル）
- 完全ローカル実行可能
- Dockerで再現可能
- API課金不要
- 小規模リポジトリで安定動作

## 11. 今後の拡張
目指すゴール：
リポジトリ全体を解析し、構造・仕様・ドメインを自然言語で説明できる「コード理解支援AI」

### Phase1：検索精度・粒度の強化（意味検索対応）

- ファイル単位 → 関数 / クラス単位チャンクへ分割
- embedding（ベクトル検索）の導入
- キーワード検索（tsvector）とベクトル検索のハイブリッド化
- スコアリングロジック改善（BM25 + ベクトル類似度統合）
- Top-K動的調整

### Phase2：構造理解の追加（静的解析）
- ディレクトリツリーの明示抽出・保存
- import解析による依存関係抽出
- クラス継承関係の解析
- エントリーポイント自動検出（main / app起動箇所）
- 設定ファイル（env, yaml等）のキー構造抽出

### Phase3：ドメインルール抽出
- バリデーションロジック抽出（if条件解析）
- Enum / 定数定義の抽出
- 例外クラスの収集
- 業務ルールらしき条件分岐の要約
- 頻出ドメイン用語の抽出（TF-IDF等）

### Phase4：構造的要約エンジン
- リポジトリ全体サマリ生成
- レイヤー構造推定（MVC / DDD等）
- データフロー要約
- 主要モジュール一覧生成
- 外部依存（DB / API / Redis等）抽出

### Phase5：理解支援モードの追加
- 「このシステムの概要を説明して」専用エンドポイント
- 「主要なビジネスルールを教えて」モード
- システムサマリ生成


### Phase6：継続的インデックス最適化
- 差分インデックス更新
- Git hook / CI連携
- 変更差分の影響範囲解析
- ドキュメント更新検知

---
### その他メモ

- [x] LLM入力の最大文字数制限
→8,000文字
  - score順に上から詰める
  - 検索結果contentのみをPythonのlen()で算出した文字数で合計8,000文字まで詰める
  - 超えたら途中で打ち切る


- [x] 再インデックス時の既存削除方針
```
DELETE FROM documents
WHERE repo_name = :repo_name;
```
→repo単位でDELETE → 再登録
  - 1 repo単位でトランザクション
  - DELETE → INSERT群 → COMMIT

- [x] clone対象ブランチ
→デフォルトブランチのみ(将来的に
ブランチ指定オプション追加)

- [x] 巨大ファイルの文字数上限
→50,000文字程度で打ち切り

- [x] CamelCase分割するかどうか
→PoCでは分割しない

- [x] LLMタイムアウト時間
→30秒タイムアウト
タイムアウト時は：
```
LLM応答がタイムアウトしました
```
を返す。