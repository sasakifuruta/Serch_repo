# 全文検索の検証レポ

## 1. 目的
本検証の目的は、複数の全文検索手法を比較し、それぞれの特性・精度・適用領域を明確にすることである。

特に以下を明らかにする：
- 各検索手法の精度の違い
- 表記ゆれ・自然文への耐性
- ノイズの発生傾向
- 実運用における適用可能性

---

## 2. 検証対象

以下の5つの検索手法を比較する：

1. n-gram（2-gram）
2. 形態素解析
3. tsvector（simple）
4. tsvector（english）
5. LIKE検索（ベースライン）

---

## 3. 検証方法

### 3.1 評価用クエリ

以下の観点でクエリを用意した：

#### ■ 完全一致系
- fastapi
- docker

#### ■ 表記ゆれ系
- get user
- get_user
- GetUser

#### ■ 自然文系
- ユーザーを取得する処理
- 設定ファイルを読み込む処理

#### ■ 曖昧ワード
- auth
- config


### 3.5 検証データ設計

検索精度の差が明確に出るように、以下の観点でデータを作成する。

#### ■ データ設計方針
- コード検索を想定した実データ風
- 意図的に“揺らぎ”を混ぜる
- 正解・部分一致・ノイズが混在する構造
- 1ファイル＝1チャンク（設計通り）

#### ■ データ分類

**1. 完全一致データ（ベースライン）**
<br>→ クエリと完全一致するケース

|観点|	内容|
|------|------------|
|目的	|LIKEでも取れる最低ライン|
|例	|fastapi, docker|

**2. 表記ゆれデータ（最重要）**
<br>→ 実務で一番差が出る
|パターン|	例|
|------|------------|
|snake_case|get_user|
|camelCase|	getUser|
|PascalCase|GetUser|
|スペース|	get user|

**3. 自然文データ（RAG向け）**
<br>→ 人間が質問する形式
例
ユーザーを取得する処理
設定ファイルを読み込む処理

**4. 曖昧ワード（ノイズ検証）**
<br>→ 検索エンジンの弱点
例
auth
config

5.ノイズデータ（必須）
<br>→ 関係ないがヒットしやすい
例
unrelated text
dummy function

---
### 3.6 検証用データ（INSERT文）
```SQL
INSERT INTO documents (id, repo_name, file_path, file_type, content, content_tsv)
VALUES

-- =========================
-- ① 完全一致データ
-- =========================
(gen_random_uuid(), 'repoA', 'main.py', 'py',
'FastAPI application entry point',
to_tsvector('simple', 'FastAPI application entry point')),

(gen_random_uuid(), 'repoA', 'docker-compose.yml', 'yml',
'Docker container configuration',
to_tsvector('simple', 'Docker container configuration')),

-- =========================
-- ② 表記ゆれ（get_user系）
-- =========================
(gen_random_uuid(), 'repoA', 'user_service.py', 'py',
'def get_user(): return user',
to_tsvector('simple', 'def get_user(): return user')),

(gen_random_uuid(), 'repoA', 'user_service2.py', 'py',
'def getUser(): return user',
to_tsvector('simple', 'def getUser(): return user')),

(gen_random_uuid(), 'repoA', 'user_service3.py', 'py',
'class GetUserService:',
to_tsvector('simple', 'class GetUserService:')),

(gen_random_uuid(), 'repoA', 'user_service4.py', 'py',
'function to get user data',
to_tsvector('simple', 'function to get user data')),

-- =========================
-- ③ 自然文（日本語）
-- =========================
(gen_random_uuid(), 'repoB', 'service.py', 'py',
'ユーザーを取得する処理を実装する',
to_tsvector('simple', 'ユーザーを取得する処理を実装する')),

(gen_random_uuid(), 'repoB', 'config_loader.py', 'py',
'設定ファイルを読み込む処理',
to_tsvector('simple', '設定ファイルを読み込む処理')),

-- =========================
-- ④ 曖昧ワード
-- =========================
(gen_random_uuid(), 'repoB', 'auth.py', 'py',
'authentication logic and auth middleware',
to_tsvector('simple', 'authentication logic and auth middleware')),

(gen_random_uuid(), 'repoB', 'config.py', 'py',
'load config and environment variables',
to_tsvector('simple', 'load config and environment variables')),

-- =========================
-- ⑤ ノイズデータ
-- =========================
(gen_random_uuid(), 'repoC', 'dummy1.py', 'py',
'random unrelated text data',
to_tsvector('simple', 'random unrelated text data')),

(gen_random_uuid(), 'repoC', 'dummy2.py', 'py',
'this is a sample function for testing',
to_tsvector('simple', 'this is a sample function for testing'));
```
---

### 3.2 実行手順

各検索手法に対して以下を実施：

1. 同一クエリを入力
2. 上位5件（Top-K=5）を取得
3. 各結果に対して関連性を評価

---

### 3.3 評価基準

各検索結果に対して以下のラベルを付与：<br>
意味的に関連があるかどうかを評価する

- ◎：完全に関連あり
- ○：部分的に関連あり
- ×：無関係

#### 例
|評価|検索文字|検索結果|
|:--|--:|:--:|
|◎|get_user|get_userそのもの|
|○|get_user|getUser / GetUser / get user|
|×|get_user|それ以外|
|◎|fastapi|FastAPIそのもの|
|○|fastapi|API関連のみ|
|×|fastapi|無関係|

---

### 3.4 評価指標

#### ■ Precision@5
上位5件のうち正解（◎）の割合

#### ■ MRR（Mean Reciprocal Rank）
最初に正解が現れた順位の逆数

#### ■ ノイズ率
無関係（×）の割合

#### ■ ヒット率
検索結果が1件以上返ってきたクエリの割合

---

## 4. 検証結果

### 4.1 定量評価

| 手法 | Precision@5 | MRR | ノイズ率 | ヒット率 |
|------|------------|-----|----------|----------|
| n-gram（2-gram） |  |  |  |  |
| 形態素解析 |  |  |  |  |
| tsvector（simple） |  |  |  |  |
| tsvector（english） |  |  |  |  |
| LIKE検索 |  |  |  |  |

---

### 4.2 クエリ別結果（例）

| クエリ | 手法 | 1位 | 2位 | 3位 | 4位 | 5位 |
|--------|------|-----|-----|-----|-----|-----|
| get_user | tsvector | ◎ | ○ | × | × | × |
| get_user | n-gram | ◎ | ◎ | ○ | × | × |

---

## 5. 考察

### 5.1 各手法の特徴

#### ■ n-gram（2-gram）
- ヒット率は高い
- ノイズが多い傾向

#### ■ 形態素解析
- 日本語クエリに強い
- コード検索との相性は弱い

#### ■ tsvector（simple）
- 高速かつ精度が高い
- 表記ゆれに弱い

#### ■ tsvector（english）
- 語幹化により英語の検索精度が向上
- 日本語には効果が薄い

#### ■ LIKE検索
- 精度・速度ともに劣る
- 比較用のベースラインとして有効

---

### 5.2 比較まとめ

- 精度重視 → tsvector
- ヒット率重視 → n-gram
- 日本語対応 → 形態素解析
- シンプル実装 → LIKE（非推奨）

---

### 5.3 課題

- 表記ゆれへの対応が不十分
- コード特有の命名規則（camelCase等）への対応不足
- ノイズ除去の仕組みが未整備

---

## 6. 結論

全文検索手法はそれぞれ特性が異なり、単独で最適な手法は存在しない。

用途に応じて適切な手法を選択、または組み合わせる必要がある。

特に以下が重要である：

- 前処理（正規化）の重要性
- チャンク設計の影響
- 検索手法の組み合わせ（ハイブリッド化）

---

## 7. 今後の改善案

- ハイブリッド検索の導入（tsvector + n-gram）
- コード特化の前処理導入（camelCase分割など）
- ベクトル検索との比較検証
- チャンク粒度の最適化（ファイル単位 → 関数単位）

---




＝＝＝＝＝＝＝＝＝＝＝＝
### 検証結果

<!-- tsvector -->
curl -s "http://localhost:8000/search?q=get_user" | jq 
curl -s "http://localhost:8000/search?q=getUser" | jq 
curl -s "http://localhost:8000/search?q=fastapi" | jq 
curl -s "http://localhost:8000/search?q=docker" | jq 
curl -s --get \
  --data-urlencode "q=ユーザーを取得する処理" \
  http://localhost:8000/search | jq
curl -s "http://localhost:8000/search?q=auth" | jq 


| クエリ | 手法 | 順位 | 評価 | content | score |
|--------|------|-----|-----|-----|-----|
| get_user | tsvector | 1 | ◎ | def get_user(): | 0.18681316|
| get_user | tsvector | 2 | ○ | function to get user data | 0.09910322|
| getUser | tsvector | 1 | ◎ | def getUser():| 0.06079271|
| fastapi | tsvector | 1 | ◎ | FastAPI | 0.06079271|
| docker | tsvector | 1 | ◎ | Docker | 0.06079271|
| ユーザーを取得する処理 | tsvector | ヒットなし | × | - | - |
| auth | tsvector | 1 | ◎ | authentication logic and auth middleware | 0.06079271 |



<!-- LIKE検索 -->
curl -s "http://localhost:8000/search_like?q=get_user" | jq 
curl -s "http://localhost:8000/search_like?q=getUser" | jq 
curl -s "http://localhost:8000/search_like?q=fastapi" | jq 
curl -s "http://localhost:8000/search_like?q=docker" | jq 
curl -s --get \
  --data-urlencode "q=ユーザーを取得する処理" \
  http://localhost:8000/search_like | jq
curl -s "http://localhost:8000/search_like?q=auth" | jq 

| クエリ | 手法 | 順位 | 評価 | content | score |
|--------|------|-----|-----|-----|-----|
| get_user | LIKE検索 | 1 | ◎ | def get_user(): | 0 |
| get_user | LIKE検索 | 2 | ○ | function to get user data | 0 |
| getUser | LIKE検索 | 1 | ◎ | def getUser():| 0 |
| fastapi | LIKE検索 | ヒットなし | × | - | - |
| docker | LIKE検索 | ヒットなし | × | - | - |
| ユーザーを取得する処理 | LIKE検索 | 1 | ◎ | ーザーを取得する処理を実装する | 0 |
| auth | LIKE検索 | 1 | ◎ | authentication logic and auth middleware | 0 |

<>