# 設定

システムの動作を変える値の正本です。処理の流れは [architecture.md](architecture.md)、バッチの起動は [worker.md](worker.md) を参照してください。

値は [backend/src/config.py](../backend/src/config.py) およびフロントの接続先に合わせています。ドキュメントと実装が食い違う場合はコードを正とします。

---

## 目次

1. [外部環境変数（`.env`）](#1-外部環境変数env)
2. [パス解決](#2-パス解決)
3. [収集](#3-収集)
4. [スコアリング・通知](#4-スコアリング通知)
5. [Gemini](#5-gemini)
6. [メール](#6-メール)
7. [ロギング](#7-ロギング)
8. [FastAPI のチューニング値](#8-fastapi-のチューニング値)
9. [起動時検証](#9-起動時検証)
10. [フロントの接続先](#10-フロントの接続先)

---

## 1. 外部環境変数（`.env`）

プロジェクトルートの `.env` を Compose の `env_file` で注入します。イメージには埋め込みません。

| 変数名 | 型 | 役割 | 備考 |
|--------|-----|------|------|
| `GEMINI_API_KEY` | `str` | Google Gemini API の認証キー | [Google AI Studio](https://aistudio.google.com/) から取得 |
| `GMAIL_USER` | `str` | 送信元 Gmail アドレス | `FROM_ADDRESS` に入る |
| `GMAIL_PASS` | `str` | Gmail の SMTP アプリパスワード | `MY_PASSWORD` に入る |

変更後はコンテナを再起動してください。

```bash
docker compose restart
```

worker は都度起動のため、次回 `docker compose run --rm worker` から新しい `.env` が使われます。

---

<a id="2-パス解決"></a>
## 2. パス解決

`BASE_DIR` は `data/` と `logs/` の基準です。

| 定数 | 型 | 値 | 意味 |
|------|-----|-----|------|
| `_SRC_DIR` | `Path` | `Path(__file__).resolve().parent` | `backend/src`（コンテナでは `/app/src`） |
| `_LOCAL_ROOT` | `Path` | `_SRC_DIR.parent.parent` | リポジトリルート候補 |
| `BASE_DIR` | `Path` | `_LOCAL_ROOT` に `compose.yaml` があればそれ、なければ `_SRC_DIR.parent` | ローカルはリポジトリルート、コンテナは `/app` |
| `DB_PATH` | `Path` | `BASE_DIR / "data" / "news.db"` | SQLite |
| `LOG_FILE` | `Path` | `BASE_DIR / "logs" / "it_news_system.log"` | アプリログ |

ローカル（`backend/src` から見て `../../compose.yaml` がある）ではリポジトリルート、コンテナ（`/app/src` から見て `compose.yaml` が無い）では `/app` になります。テーブル定義は [architecture.md](architecture.md#5-データモデル) を参照してください。

---

## 3. 収集

| 定数 | 型 | 値 | 変更時の注意 |
|------|-----|-----|----------------|
| `RSS_LIST` | `list[tuple[str, str]]` | 下記 | `(URL, ソース名)`。増やすと Gemini 呼び出しも増える |
| `SOURCE_FETCH_LIMIT` | `int` | `20` | ソースあたりの取得上限 |
| `MAX_ARTICLES_PER_BATCH` | `int` | `100` | 1 バッチで Gemini に渡す記事の合計上限（ID 重複排除後） |

```python
RSS_LIST = [
    ("https://news.ycombinator.com/rss", "Hacker News"),
    ("https://techcrunch.com/feed/", "TechCrunch"),
    ("https://www.theverge.com/rss/index.xml", "The Verge"),
    ("https://feeds.arstechnica.com/arstechnica/index", "Ars Technica"),
    ("https://github.blog/feed/", "GitHub Blog"),
]
```

パイプライン上の位置は [worker.md](worker.md#4-パイプライン手順) を参照してください。

---

<a id="4-スコアリング通知"></a>
## 4. スコアリング・通知

式とソート規則は [architecture.md](architecture.md#6-ランキング設計) を正とします。ここは数値だけです。

| 定数 | 型 | 値 | 役割 |
|------|-----|-----|------|
| `IMPORTANCE_THRESHOLD` | `int` | `6` | ランキング生成・メール通知の重要度下限（1〜10） |
| `RANKING_LIMIT` | `int` | `10` | バッチが `rankings` に保存する件数 |
| `NOTIFICATION_LOOKBACK_DAYS` | `int` | `7` | 公開日のさかのぼり日数（ランキング生成・通知共通） |
| `NOTIFICATION_LIMIT` | `int` | `5` | 1 回のメールに載せる最大件数 |
| `FRESHNESS_TABLE` | `dict[int, float]` | 下記 | 経過日数 0〜7 に対する鮮度係数 |

API の `GET /v1/rankings` 既定 `min_importance` は **7** です（次節）。バッチのしきい値 `6` より厳しいです。

```python
FRESHNESS_TABLE = {
    0: 1.00,  # 当日
    1: 0.95,
    2: 0.90,
    3: 0.85,
    4: 0.60,  # ここから減衰が大きい
    5: 0.40,
    6: 0.20,
    7: 0.10,
}
```

ランキング生成 SQL は 0〜6 日をこの表と同じ係数で掛け、7 日以上は `0.00` にします。

---

<a id="5-gemini"></a>
## 5. Gemini

分析がパイプラインのどこで走るかは [architecture.md](architecture.md#4-データフロー) と [worker.md](worker.md) を参照してください。運用で触る文言はここに置きます。

| 定数 | 型 | 値 | 役割 |
|------|-----|-----|------|
| `MODEL_ID` | `str` | `"gemini-2.5-flash-lite"` | 使用モデル |
| `TEMPERATURE` | `float` | `1.0` | 生成のランダム性 |
| `GEMINI_SLEEP_SECONDS` | `int` | `5` | 記事間ウェイト。429/503 時は `5 * 2^attempt` 秒 |
| `GEMINI_MAX_RETRIES` | `int` | `5` | 一時エラーの最大リトライ回数 |
| `USER_PREFERENCES` | `str` | 下記 | プロンプトに注入する関心トピック |
| `PROMPT_TEMPLATE` | `str` | 下記 | ユーザープロンプト |
| `SYSTEM_INSTRUCTION` | `str` | 下記 | システム指示 |

```python
USER_PREFERENCES = """
プログラミング言語 (Python),
開発ツールの新機能,
バックエンド技術スタック,
データベース技術スタック,
インフラ技術スタック,
AI/ML技術スタック
"""
```

```python
PROMPT_TEMPLATE = """
以下の記事をITエンジニアの視点で分析してください。
今回のユーザーの【特に関心の高いトピック】を踏まえてスコアリングを行う必要があります。

【ユーザーの関心トピック】: {user_preferences}

【記事のID】: {id}
【タイトル】: {title}
【内容】: {summary}

出力は必ずシステム指示（System Instruction）で指定されたJSONの配列（List[dict]）形式のみを返してください。
"""
```

```python
SYSTEM_INSTRUCTION = """
あなたは、第一線で活躍する好奇心旺盛なシニアソフトウェアエンジニアです。
ユーザーごとにパーソナライズされたITニュースのフィルタリングとスコアリングを担当しています。

提供されるタイトルと内容、そして【ユーザーの関心トピック】を照らし合わせ、以下の基準で【厳格にメリハリをつけて】1〜10点でスコアリング（importance）してください。

【最優先：7〜10点】
・【ユーザーの関心トピック】に直接関連する「新機能」「技術アップデート」「実戦的な活用事例・ガイド」。
・エンジニアの実務や技術選定に強烈なインパクトを与えるような、対象分野の重大な業界ニュース。

【興味あり：5〜6点】
・【ユーザーの関心トピック】に周辺領域として関連するニュース（例：言語が指定された場合の、関連ツールやインフラの話題など）。
・実務にすぐ直結はしないが、技術的に筋の良い新しいアプローチや実験的試み。

【低優先：1〜4点】
・【ユーザーの関心トピック】に全く該当しない、興味の対象外のニュース。
・テック企業に関する単なる政治的・法的な議論、人事の噂話。
・一般的な製品のカジュアルなガジェットレビュー（コンシューマー向け情報）。

出力形式は、必ず以下のJSONスキーマを厳守して返してください：
{
"id": "記事のID（必ず数字）",
"ai_summary": "3行で簡潔に要約した文章（必ず日本語）",
"importance": 1から10の整数値,
"reason": "今回のユーザーの関心トピックと照らし合わせ、なぜこの重要度スコアにしたのかの具体的な理由（必ず日本語）",
"category": "技術カテゴリ"
}
"""
```

---

## 6. メール

| 定数 | 型 | 参照元 | 役割 |
|------|-----|--------|------|
| `FROM_ADDRESS` | `str` | `GMAIL_USER` | SMTP 送信元 |
| `MY_PASSWORD` | `str` | `GMAIL_PASS` | SMTP アプリパスワード |

件名や本文テンプレートの定数は `backend/src/constants.py` です。配信タイミングは [worker.md](worker.md) を参照してください。

---

<a id="7-ロギング"></a>
## 7. ロギング

| 定数 | 型 | 値 | 役割 |
|------|-----|-----|------|
| `LOG_FILE` | `Path` | `BASE_DIR / "logs" / "it_news_system.log"` | アプリログ |
| `LOG_MAX_BYTES` | `int` | `5 * 1024 * 1024`（5 MiB） | ローテーションサイズ |
| `LOG_BACKUP_COUNT` | `int` | `3` | 世代数 |

cron の標準出力は `logs/cron.log` です。見方は [worker.md](worker.md#7-運用チェック) を参照してください。

---

<a id="8-fastapi-のチューニング値"></a>
## 8. FastAPI のチューニング値

パスとレスポンス形は [architecture.md](architecture.md#7-rest-api-契約) を正とします。

| 定数 / 設定 | 値 | 役割 |
|-------------|-----|------|
| `API_TITLE` | `"IT News Live API"` | OpenAPI タイトル |
| `API_DESCRIPTION` | `"ITニュースを収集し、Geminiで分析・配信するAPI"` | OpenAPI 説明 |
| `API_VERSION` | `"1.3.2"` | FastAPI の `version`（リポジトリのリリース番号 1.5.1 とは別） |
| CORS `allow_origins` | `http://localhost:3000`、`http://localhost:5173`、`http://127.0.0.1:5173` | ブラウザからの fetch を許可するオリジン |
| CORS `allow_credentials` | `True` | 資格情報付きリクエストを許可 |
| CORS `allow_methods` / `allow_headers` | `*` | メソッド・ヘッダーは制限しない |
| ランキング API 既定クエリ | `limit=10`、`min_importance=7`、`lookback_days=7`、`batch_id` 省略時は最新バッチ | `GET /v1/rankings` |

Vite のオリジンを変えたら CORS リストも合わせて更新してください。

---

<a id="9-起動時検証"></a>
## 9. 起動時検証

バッチは `main()` 先頭で `validate_config()` を呼びます。失敗時は `ConfigValidationError` を上げ、バッチは開始しません。例外クラス自体は設定項目ではないため、ここには値の検査内容だけを書きます。

検査する項目:

- 必須環境変数 `GEMINI_API_KEY` / `GMAIL_USER` / `GMAIL_PASS` が空でない
- `IMPORTANCE_THRESHOLD` が 1〜10
- `NOTIFICATION_LIMIT` が正数
- `NOTIFICATION_LOOKBACK_DAYS` が正数
- `GEMINI_MAX_RETRIES` が正数
- `BASE_DIR` が存在する
- `LOG_FILE` の親ディレクトリを作成できる（無ければ作成）

---

<a id="10-フロントの接続先"></a>
## 10. フロントの接続先

[frontend/src/api.ts](../frontend/src/api.ts):

```ts
const API_BASE_URL = 'http://localhost:8080/v1'
```

ランキングは `GET ${API_BASE_URL}/rankings` です。API を別ホストで動かすときはこの定数と CORS オリジンの両方を更新してください。画面側の呼び出し関係は [architecture.md](architecture.md#8-フロントエンド連携) を参照してください。
