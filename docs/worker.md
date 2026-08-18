# バッチ運用

`worker` の起動・手順・失敗時の挙動・監視の正本です。パイプラインの設計理由は [architecture.md](architecture.md)、しきい値やソース一覧は [configuration.md](configuration.md) を参照してください。

エントリポイントは [backend/src/main.py](../backend/src/main.py) です。

---

## 目次

1. [コンテナの役割とビルド構成](#1-コンテナの役割とビルド構成)
2. [workerコンテナの手動実行](#2-workerコンテナの手動実行)
3. [workerコンテナの定期実行（cron）](#3-workerコンテナの定期実行cron)
4. [パイプライン手順](#4-パイプライン手順)
5. [失敗時の挙動](#5-失敗時の挙動)
6. [DBとログの役割](#6-DBとログの役割)
7. [運用チェック](#7-運用チェック)

---

## 1. コンテナの役割とビルド構成

本システムの `api` と `worker` は「APIサーバ用」と「バッチ/worker用」で役割が明確に分かれていますが、**同一のDockerfile**（`docker/Dockerfile`、`python:3.12-slim`ベース）からそれぞれ個別にビルドされています。ここでは `worker` コンテナの運用上の役割や起動方式、その設計意図について詳述します。

### workerコンテナの役割

- `api` と同じDockerfileからビルドされますが、`worker`は**バッチ専用・ジョブ型**の短命コンテナとして起動されます。
- 起動時に **RSS取得→Gemini分析→ランキング生成→メール通知** の一連処理を実行後、自動終了・破棄されます。
- 外部からのリクエストは受け付けず、`api`とは異なり自己完結型です。
- データ/ログはComposeの`volumes`設定により`api`と同じホストディレクトリ（`./data`, `./logs`）をマウントしており、両者は同一のデータを参照します。

| コンテナ    | 主な役割                                | 起動方法・ライフサイクル                      |
|-------------|------------------------------------------|-----------------------------------------------|
| `api`       | REST APIサーバー。記事ランキング等の閲覧 | 常時起動(`docker compose up -d api`等)       |
| `worker`    | 一括バッチ処理。RSS～分析～通知           | 必要時のみ都度起動・実行終了後に破棄(`docker compose run --rm worker`) |

- `worker`はComposeの`profiles: ["manual"]`により、`docker compose up -d`では**自動では起動しません**。運用者が任意に実行するか、cron等で定期的に呼び出します。
- コンテナの実行例やマウントの詳細は[2.手動実行](#2-手動実行)、パイプラインの各段階は[4.パイプライン手順](#4-パイプライン手順)を参照してください。

> 💡**設計意図**: API・workerで同じDockerfileを共有することで依存関係の管理・開発運用負荷を抑えつつ、それぞれの運用要件（常駐vsバッチ）の違いをDocker Composeの`profiles`と`command`指定で柔軟に切り替えています。

詳細なシステム全体像は [architecture.md](architecture.md#2-コンテナ構成とサービス全体像) を参照してください。

---

## 2. workerコンテナの手動実行

プロジェクトルートで:

```bash
docker compose run --rm worker
```

`worker`にはあらかじめ`python src/main.py`が起動コマンドとして設定されており（`api`の`fastapi run ...`とは別）、上記コマンドで実行されます。`--rm`により終了後にコンテナを削除します。`.env`と`./data` / `./logs`は`api`と同じマウント設定です。

---

## 3. workerコンテナの定期実行（cron）

ホストの cron が毎日 7:00 に上記と同じコマンドを実行します。パスは環境に合わせて置き換えてください。

```bash
# 毎朝 7:00 にプロジェクトルートへ移動し、worker をオンデマンド実行
0 7 * * * cd /path/to/it-news-system && /usr/bin/docker compose run --rm worker >> /path/to/it-news-system/logs/cron.log 2>&1
```

- 登録: ホストで `crontab -e`
- 標準出力・標準エラーは `logs/cron.log` に追記
- アプリの詳細ログは `logs/it_news_system.log`（`./logs`がコンテナの`/app/logs`にマウントされているため、ホスト側からも参照可能）

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
   `batches`の当該行に`success`または`failed`と通知件数を書き込む。`return` / `raise`のどちらでも実行する。

---

## 5. 失敗時の挙動

| 状況 | 挙動 | バッチ status |
|------|------|----------------|
| 設定検証エラー | ログに出して `main` が return。`batches` 行は作らない | （バッチ未開始） |
| 1 RSS ソースの失敗 | そのソースをスキップして続行 | 他が成功すれば `success` |
| 全 RSS ソースの失敗 | 記事0件のまま後続ステップへ進む | `success`（件数 0、通知対象0件と同じ扱い） |
| Gemini 429 / 503 / UNAVAILABLE | 指数バックオフで最大 `GEMINI_MAX_RETRIES` 回再試行 | `running`のまま継続 |
| Gemini が最終的に失敗、または回復不能エラー | 重要度 `0` のダミー分析を保存し、次の記事へ | `running`のまま継続（0 点はランキング・通知から外れる） |
| 通知対象 0 件 | 警告ログのあとメールせず正常終了 | `success`（件数 0） |
| メール送信失敗（`EmailSendError`） | 例外を再送出 | `failed` |
| 上記以外の致命的エラー | `run_batch` が例外を再送出 | `failed` |
| `finish_batch` 自体の失敗 | ログのみ。呼び出し元の成否は変えない | DB 上の status が `running` のまま残る可能性 |

---

## 6. DBとログの役割

| パス | 内容 | 用途 |
|------|------|------|
| `data/news.db` | 記事・分析・ランキング・バッチ履歴 | `worker`が書き込み、`api`が同じファイルを読んで配信 |
| `logs/it_news_system.log` | アプリの INFO/ERROR（ローテーションあり） | 障害調査 |
| `logs/cron.log` | cron が集約したコンテナ stdout/stderr | 定期実行の成否確認 |

ログサイズと世代数は [configuration.md](configuration.md#7-ロギング) を参照してください。

---

<a id="7-運用チェック"></a>

## 7. 運用チェック

### API の死活監視

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

成功時は `Batch {id} 完了 (status=success, count=N)` が出ます。ソーススキップは `スキップして続行`、通知 0 件は `通知対象の記事が0件` と表示されます。

### 再実行時の注意点

このバッチ処理(`docker compose run --rm worker`)は都度新しい「バッチID」で記録を作成して実行されるため、同じ日に何度も実行しても、そのたびに別バッチとして記録されます。

- すでに登録済みの記事(URL単位)は、2回目以降のバッチで重複して保存されません（記事URLはDBで一意に管理されています）。
- ただし、記事ごとの分析データは「記事ID＋バッチID」のセットごとに記録されるため、同じ記事が複数バッチで分析された場合はその分データが追加されます。
- APIの `GET /v1/rankings` は、デフォルトで最新のバッチ（直近のバッチID）のランキングを表示します。

バッチを複数回実行しても問題ありませんが、履歴としてバッチや分析の記録がDB内に残ります。もし「API経由で現在のランキングを確認したいだけ」であれば、workerを再実行せずに、そのまま `GET /v1/rankings` エンドポイントにアクセスしてください。
