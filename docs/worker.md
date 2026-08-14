# バッチ運用

`worker` の起動・手順・失敗時の挙動・監視の正本です。パイプラインの設計理由は [architecture.md](architecture.md)、しきい値やソース一覧は [configuration.md](configuration.md) を参照してください。

エントリポイントは [backend/src/main.py](../backend/src/main.py) です。

---

## 目次

1. [役割](#1-役割)
2. [手動実行](#2-手動実行)
3. [定期実行（cron）](#3-定期実行cron)
4. [パイプライン手順](#4-パイプライン手順)
5. [失敗時の挙動](#5-失敗時の挙動)
6. [成果物](#6-成果物)
7. [運用チェック](#7-運用チェック)

---

## 1. 役割

`python src/main.py` が **RSS 取得 → Gemini 分析 → ランキング → メール** を 1 バッチで実行します。

| プロセス | ライフサイクル |
|----------|----------------|
| `api` | 常時起動。ランキング閲覧用 |
| `worker` | 都度起動し、終了後にコンテナを捨てる（`compose run --rm`） |

`worker` は Compose の `profiles: ["manual"]` のため、`docker compose up -d` では立ち上がりません。トポロジは [architecture.md](architecture.md#2-実行トポロジ) を参照してください。

---

## 2. 手動実行

プロジェクトルートで:

```bash
docker compose run --rm worker
```

同一イメージを使い、コマンドだけ `python src/main.py` に上書きします。`--rm` により終了後にコンテナを削除します。`.env` と `./data` / `./logs` は `api` と同じマウントです。

---

## 3. 定期実行（cron）

ホストの cron が毎日 7:00 に上記と同じコマンドを打ちます。パスは環境に合わせて置き換えてください。

```bash
# 毎朝 7:00 にプロジェクトルートへ移動し、worker をオンデマンド実行
0 7 * * * cd /path/to/it-news-system && /usr/bin/docker compose run --rm worker >> /path/to/it-news-system/logs/cron.log 2>&1
```

- 登録: ホストで `crontab -e`
- 標準出力・標準エラーは `logs/cron.log` に追記
- アプリの詳細ログは `logs/it_news_system.log`（コンテナ内からホストへマウント）

---

<a id="4-パイプライン手順"></a>
## 4. パイプライン手順

`main()` → `run_batch()` の順です。

1. **`validate_config`**  
   必須 env と数値範囲を検査する。失敗したらバッチを開始せず終了する。検査項目は [configuration.md](configuration.md#9-起動時検証) を参照。
2. **`start_new_batch`**  
   `batches` に `status=running` の行を作り、`batch_id` を払出す。
3. **ソースごとに `fetch_rss`**  
   `RSS_LIST` を順に処理する。ソースあたり `SOURCE_FETCH_LIMIT` 件。1 ソースの失敗はスキップし、他ソースを続ける。全ソースの記事を集約してから次へ進む。
4. **Gemini 分析 → ランキング**  
   ID 重複を除き `MAX_ARTICLES_PER_BATCH` 件まで分析し、`article_analyses` に保存する。続けて鮮度付きスコアで上位を `rankings` に保存する。式は [architecture.md](architecture.md#6-ランキング設計)。
5. **通知対象抽出 → メール**  
   当該 `batch_id` のランキングから、重要度・さかのぼり日数・件数上限で絞り SMTP 送信する。0 件ならメールは送らない。
6. **`finally` で `finish_batch`**  
   `success` または `failed` と通知件数を書く。`return` / `raise` のどちらでも実行する。

---

## 5. 失敗時の挙動

| 状況 | 挙動 | バッチ status |
|------|------|----------------|
| 設定検証エラー | ログに出して `main` が return。`batches` 行は作らない | （バッチ未開始） |
| 1 RSS ソースの失敗 | そのソースをスキップして続行 | 他が成功すれば `success` |
| Gemini 429 / 503 / UNAVAILABLE | 指数バックオフで最大 `GEMINI_MAX_RETRIES` 回再試行 | 継続 |
| Gemini が最終的に失敗、または回復不能エラー | 重要度 `0` のダミー分析を保存し、次の記事へ | 継続（0 点はランキング・通知から外れる） |
| 通知対象 0 件 | 警告ログのあとメールせず正常終了 | `success`（件数 0） |
| メール送信失敗（`EmailSendError`） | 例外を再送出 | `failed` |
| 上記以外の致命的エラー | `run_batch` が例外を再送出 | `failed` |
| `finish_batch` 自体の失敗 | ログのみ。呼び出し元の成否は変えない | DB 上の status が `running` のまま残る可能性 |

---

## 6. 成果物

| パス | 内容 | 参照者 |
|------|------|--------|
| `data/news.db` | 記事・分析・ランキング・バッチ履歴 | `api` が同じファイルを読む |
| `logs/it_news_system.log` | アプリの INFO/ERROR（ローテーションあり） | 障害調査 |
| `logs/cron.log` | cron が集約したコンテナ stdout/stderr | 定期実行の成否 |

ログサイズと世代数は [configuration.md](configuration.md#7-ロギング) を参照してください。

---

<a id="7-運用チェック"></a>
## 7. 運用チェック

### API の死活

```bash
docker compose ps
```

`api` の STATUS が `Up ... (healthy)` なら healthcheck は通っています。worker は実行中以外は一覧に出ません。

### ログ

```bash
# アプリ（バッチ・API 共通）
tail -n 100 logs/it_news_system.log

# cron 経由の実行
tail -n 100 logs/cron.log
```

成功時は `Batch {id} 完了 (status=success, count=N)` が出ます。ソーススキップは `スキップして続行`、通知 0 件は `通知対象の記事が0件` です。

### 再実行の注意

同じ日に `docker compose run --rm worker` を複数回打つと、その都度新しい `batch_id` が立ちます。

- 記事 URL は UNIQUE のため、同一 URL の行は増えない
- 分析は `(article_id, batch_id)` 単位で増える
- `GET /v1/rankings` の既定は **最新の `batch_id`** を見る

検証の再実行は問題ありませんが、履歴行は残ります。API だけ確認したい場合は worker を再実行せず、既存 DB に対して `GET /v1/rankings` を叩いてください。
