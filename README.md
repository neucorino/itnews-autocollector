<div id="top"></div>

# IT News Auto-Collector & Delivery System

**Version 1.3.1** — Docker Compose による API サーバーの死活監視と自動再起動を追加。ヘルスチェックエンドポイントにより、コンテナ環境でのサービス信頼性を強化しました。

<p style="display: inline">
  <img src="https://img.shields.io/badge/-Python-F2C63C.svg?logo=python&style=for-the-badge">
  <img src="https://img.shields.io/badge/-SQLite-003B57.svg?logo=sqlite&style=for-the-badge&logoColor=white">
  <img src="https://img.shields.io/badge/-Google%20Gemini-8E75B2.svg?logo=googlegemini&style=for-the-badge&logoColor=white">
  <img src="https://img.shields.io/badge/-FastAPI-009688.svg?logo=fastapi&style=for-the-badge&logoColor=white">
  <img src="https://img.shields.io/badge/-Docker-2496ED.svg?logo=docker&style=for-the-badge&logoColor=white">
  <img src="https://img.shields.io/badge/-Linux-FCC624.svg?logo=linux&style=for-the-badge&logoColor=black">
</p>

---

## 目次

1. [はじめに](#はじめに)
2. [プロジェクトについて](#プロジェクトについて)
3. [運用ワークフロー](#運用ワークフロー)
4. [ビジネス上の価値](#ビジネス上の価値)
5. [バージョン履歴と改善点](#バージョン履歴と改善点)
6. [環境](#環境)
7. [アーキテクチャ](#アーキテクチャ)
8. [工夫した点・アピールポイント](#工夫した点アピールポイント)
9. [リポジトリ構成](#リポジトリ構成)
10. [Dockerfile の設計](#dockerfile-の設計)
11. [セットアップと実行](#セットアップと実行)
12. [トラブルシューティング](#トラブルシューティング)
13. [ライセンス・連絡](#ライセンス連絡)

---

## はじめに

**バックエンド寄りの Python 製オートメーション**として公開しているポートフォリオ用リポジトリです。マネージドクラウドに縛られない **自ホストで完結する設計**、**LLM を業務フローに組み込んだ処理**、**FastAPI による REST API 層**、そして **Docker による再現可能な実行環境** を示す目的でまとめています。

| 対象者 | 参照箇所 |
|--------|----------|
| **採用・発注担当** | [ビジネス上の価値](#ビジネス上の価値) → [バージョン履歴](#バージョン履歴と改善点) → [工夫した点・アピールポイント](#工夫した点アピールポイント) → [環境](#環境) |
| **クライアント（非エンジニア）** | [プロジェクトについて](#プロジェクトについて) → [ビジネス上の価値](#ビジネス上の価値) → [運用ワークフロー](#運用ワークフロー) |
| **開発者・共同作業者** | [リポジトリ構成](#リポジトリ構成) → [Dockerfile の設計](#dockerfile-の設計) → [セットアップと実行](#セットアップと実行) → [トラブルシューティング](#トラブルシューティング) |

---

## プロジェクトについて

複数の IT ニュースソース（RSS）から記事を **自動取得** し、**Google Gemini API** で要約・重要度スコア・技術カテゴリの付与を行います。取得した記事を SQLite に蓄積し、**重要度と鮮度係数を組み合わせたランキングアルゴリズム** により期間内トップ記事を算出したうえで、しきい値を超えた記事のみ **Gmail（SMTP）で通知** します。
v1.2.0 からは **FastAPI による REST API** を追加し、v1.3.0 では **Docker (Compose v2)** によるコンテナ化を完了。v1.3.1 では **ヘルスチェックと自動再起動** により運用の安定性を強化しています。バッチ処理・API サーバー・データ永続化を分離しつつ、同一イメージから両サービスを起動できる構成へと進化しています。

<p align="right">(<a href="#top">トップへ</a>)</p>

---

## 運用ワークフロー

### システム概要 (System Overview)

1. `docker compose up -d` で API サーバー（`api` サービス）を常時起動する。
2. 必要に応じて `docker compose run --rm worker` で収集・分析バッチを実行する。
3. RSS から新規記事を取り込み、未分析記事を Gemini で処理する。
4. ランキングを更新し、通知条件を満たす記事があればメールを送る。
5. ホストマウントされた `data/news.db` を介して、API サーバーから蓄積データを REST 経由で取得できる。
6. ログファイルで成功・失敗を追跡する。

### ワークフロー

- **コンテナ基盤**: Docker Compose v2（`api` 常時起動 / `worker` オンデマンド実行）
- **処理パイプライン**: RSS 取得 → SQLite 保存 → Gemini 分析 → ランキング生成 → メール配信
- **データ提供**: FastAPI (Port: 8080) を介した REST API

<p align="right">(<a href="#top">トップへ</a>)</p>

---

## ビジネス上の価値

- **時間削減**: 毎日のニュースサイト巡回と取捨選択を自動化します。
- **意思決定の補助**: 記事の要約・重要度スコア・公開日時を組み合わせたランキングにより、キャッチアップの優先順位が明確になります。
- **再現性**: 記事の選別ルールを設定することで、毎回同じ基準でスクリーニングが可能です。
- **外部連携性**: REST API 経由でランキング・通知候補を取得できるため、ダッシュボードや他システムとの連携基盤として機能します。
- **運用しやすさ**: ログローテーション、環境変数による秘密情報の分離、モジュール分割による保守性、Docker による環境の再現性を意識した構成です。

<p align="right">(<a href="#top">トップへ</a>)</p>

---

## バージョン履歴と改善点

### v1.3.1 での改善点【最新】

| 改善内容 | 詳細 |
|---------|------|
| **ヘルスチェック API** | `GET /health` エンドポイントを追加し、API サーバーの死活監視に対応 |
| **Compose healthcheck** | `api` サービスで 30 秒間隔のヘルスチェックを設定し、3 回連続失敗で unhealthy と判定 |
| **自動再起動** | `restart: always` により、プロセス異常終了や unhealthy 判定時にコンテナを自動復旧 |
| **curl の導入** | `Dockerfile` に `curl` を追加し、Compose からのヘルスチェック実行を可能に |
| **Linuxシステムcronによるバッチ（worker）の自律定期実行** | オンデマンド実行用にコンポーネント分離した `worker` コンテナを、ホストOS（Ubuntu）側の定期実行タスクスケジューラー（cron）に登録。 |
| **プロダクション運用のための堅牢なデバッグログ設計** | cron実行時における最小限の環境変数を考慮した絶対パス制御を徹底。`cron.log`へ、コンテナの標準出力およびエラー出力（`2>&1`）をすべて集約。 | 


### Version History

```
v1.0    コア機能完成

v1.1    設計・アーキテクチャ改善

v1.1.1  堅牢性の向上・リファクタリング

v1.2.0  REST API化

v1.2.1  ランキングアルゴリズムの改善・公開日時の正規化

v1.3.0  Docker コンテナ化
        - Dockerfile / compose.yaml の追加
        - API サーバー（api）と収集バッチ（worker）のサービス分離
        - ホストボリュームによる data/・logs/ の永続化と DB 共有
        - `.env` による秘密情報のコンテナ注入
        - `docker compose up -d` による API 常時起動
        - `docker compose run --rm worker` によるバッチのオンデマンド実行

v1.3.1  サービス信頼性の強化【最新】
        - GET /health エンドポイントの追加
        - compose.yaml への healthcheck 設定
        - api サービスの restart: always による自動再起動
        - Dockerfile への curl 追加
        - Linuxシステムcronによるバッチ（worker）の自律定期実行
        - プロダクション運用のための堅牢なデバッグログ設計

v2.0    運用・拡張（予定）
        - Slack / Discord 通知
        - GitHub リリースタグの作成と CHANGELOG の固定（Git 運用の仕上げ）
        - API 機能のさらなる拡張（クエリパラメータや追加エンドポイント）
        - 非同期処理（async/await）の全面導入
        - Web UI の構築
```

<p align="right">(<a href="#top">トップへ</a>)</p>

---

## 環境

### 実行基盤（推奨）

| コンポーネント | バージョン | 用途 |
|--------------|-----------|------|
| Docker Engine | v25.0 以上推奨 | コンテナ実行環境 |
| Docker Compose | v2.0 以上 | マルチサービス管理 |

### アプリケーションスタック

| ライブラリ | バージョン | 用途 |
|-----------|-----------|------|
| Python | 3.12 | 実行環境（コンテナ内） |
| fastapi | 最新安定版 | REST API フレームワーク（★v1.2.0） |
| feedparser | 6.0.12 | RSS 取得・パース |
| requests | 2.32.5 | HTTP 通信 |
| python-dotenv | 1.2.1 | 環境変数管理 |
| pydantic | 2.12.5 | データバリデーション・モデル定義（★v1.2.0） |
| google-genai | 1.62.0 | Gemini API クライアント |
| tenacity | 9.1.2 | リトライ処理 |
| tqdm | 4.67.3 | 進捗表示 |
| websockets | 16.0 | WebSocket 通信 |

その他の標準ライブラリ（`sqlite3` / `smtplib` / `logging`）は Python 付属のため別途インストール不要です。

<p align="right">(<a href="#top">トップへ</a>)</p>

---

## アーキテクチャ

### データフロー

```mermaid
flowchart LR
    subgraph ext["外部システム"]
        Web[RSS配信元]
        GeminiAPI[Google Gemini API]
        SMTP[メールサーバー]
        Client[API クライアント]
    end

    subgraph dc["Docker Compose"]
        subgraph api["api サービス（常時起動）"]
            apiMod[api.py<br/>FastAPI REST API]
        end
        subgraph worker["worker サービス（オンデマンド）"]
            fetch[rss_fetcher.py<br/>RSS記事収集]
            service[service.py<br/>ビジネスロジック制御]
            analyze[gemini_analyzer.py<br/>LLM解析・スコアリング]
            rank[ranking.py<br/>ランキングロジック]
            notify[mail_sender.py<br/>メール配信]
        end
    end

    subgraph ds["データストア"]
        storage[(db.py / SQLite<br/>data/news.db)]
    end

    Web -->|RSSフィードXML| fetch
    fetch -->|未処理記事| service
    service <-->|プロンプト / 構造化出力| GeminiAPI
    service -.->|解析依頼| analyze
    service -.->|ランキング集計| rank
    service -->|記事・分析結果・順位| storage
    storage -->|データ参照| service
    service -->|通知対象データ| notify
    notify -->|SMTPプロトコル| SMTP

    Client -->|HTTP リクエスト| apiMod
    apiMod -->|SQLクエリ| storage
    storage -->|型安全なデータ / Pydanticモデル| apiMod
    apiMod -->|JSON レスポンス| Client

    analyze ~~~ rank
    
```

### モジュール構成（概念）

```mermaid
flowchart TD
    subgraph Core [データ収集・分析バッチフロー]
        Main[main.py<br/>バッチエントリーポイント]
        RSS[rss_fetcher.py<br/>RSS記事取得]
        AI[gemini_analyzer.py<br/>LLM要約・解析]
        Rank[ranking.py<br/>ランキング生成]
        Service[service.py<br/>ビジネスロジック制御]
    end

    subgraph API [REST API層]
        FastAPI[api.py<br/>FastAPI Webサーバー]
    end

    subgraph Output [永続化・外部出力]
        Mail[mail_sender.py<br/>通知メール送信]
        Utils[my_utils.py<br/>汎用ユーティリティ]
        DB[db.py<br/>DatabaseManager]
        SQLite[(SQLite / news.db)]
    end

    subgraph Infra [共通基盤・パッケージ定義]
        Init["__init__.py<br/>パッケージ初期化"]
        Config[config.py<br/>環境設定管理]
        Const[constants.py<br/>定数定義]
        Exc[exceptions.py<br/>独自例外定義]
        Queries[queries.py<br/>SQLクエリ集約]
        Logger[logger.py<br/>ロギング一元管理]
        Models[models.py<br/>Pydantic / データ型定義]
    end

    Main --> RSS
    Main --> AI
    Main --> Service
    Service --> Rank
    Service --> DB
    Service --> Mail
    Mail --> Utils
    FastAPI --> DB
    DB --> SQLite
    Core -.-> Infra
    API -.-> Infra
    Output -.-> Infra
    Init -.-> Core
    Init -.-> API
```

<p align="right">(<a href="#top">トップへ</a>)</p>

---

## 工夫した点・アピールポイント

### 1. 変化に強いクリーンな「レイヤードアーキテクチャ」の採用

```
Presentation / API 層  （api.py — FastAPI エンドポイント）
       ↓
Service 層            （service.py — ビジネスロジック）
       ↓
Data 層               （db.py — DB・永続化）
       ↓
Infrastructure 層     （外部API・ログ・設定）
```

ビジネスロジック・データアクセス・データモデルを層単位で分離しているため、機能追加時の影響範囲が限定されます。この設計により、既存のバッチ処理に手を加えることなく FastAPI による REST API 機能を独立コンポーネントとして統合できました。

### 2. 本番運用を想定した「堅牢性・セキュリティ」の徹底

- **フェイルファスト設計**: 起動直後に `validate_config()` で設定値を検証し、不完全な状態での稼働を防ぎます。
- **リソース管理**: `DatabaseManager` にコンテキストマネージャーを実装し、例外発生時でも確実に DB 接続をクローズします。
- **依存注入（DI）パターン**: 依存関係をコンストラクタ経由で注入することで、テスト時のモック差し替えを容易にしています。
- **SQL インジェクション対策**: SQLite への全アクセスに名前付きプレースホルダーを用いた動的パラメータバインディングを徹底しています。
- **型安全な API レスポンス**: Pydantic v2 の `response_model` により内部データ構造を隠蔽し、CORSMiddleware で接続オリジン・許可メソッドを適切に制限しています。

### 3. ニュース特性を反映した「ランキングアルゴリズムと LLM 設計」

- **段階的鮮度減衰モデル**: 公開からの経過時間に応じてスコアが段階的に低下。重要度 × 鮮度係数の `rank_score` で時間的価値を順位に反映。
- **公開日時の正規化と安定ソート**: RFC 2822 形式を `YYYY-MM-DD HH:MM:SS` へ統一保存し、同一スコア時は公開日時 → ID の優先順位で並び順を確定することで一貫したランキングを保証します。
- **LLM の継続的改善**: Gemini 2.5 Flash-Lite へ移行してコストを削減しつつ、Temperature の引き上げとプロンプト改修でスコアリング精度を維持しています。

### 4. 再現可能な「Docker コンテナ基盤」の構築

- **API / Worker の役割分離**: 同一 Docker イメージから `api`（FastAPI 常時起動）と `worker`（バッチオンデマンド）を起動。関心の分離をインフラ層でも一貫させています。
- **ホストボリュームによる DB 共有**: `data/news.db` をホストにマウントし、バッチ処理結果を API サーバーへ即時反映。コンテナ再起動後もデータを保持します。
- **レイヤーキャッシュ最適化**: `requirements.txt` を先に COPY → `pip install` することで、ソース変更時の再ビルド時間を短縮。
- **秘密情報の外部注入**: `.env` を `env_file` で読み込み、API キーや SMTP 認証情報をイメージに含めない設計。
- **ヘルスチェックと自動再起動**: `GET /health` と Compose `healthcheck` で API サーバーの死活を監視し、`restart: always` により異常時の自動復旧を実現。
- **ホストcronとDockerのProfiles機能を組み合わせたオンデマンド自律運用**: 常時起動が必要な`api`サービスと、1日1回だけ動かす`worker`サービスのライフサイクルを最適化。ホストOSの堅牢な `cron` と Docker Compose の `profiles: ["manual"]` を組み合わせることで、「毎朝指定時刻に自動で`worker`コンテナが立ち上がり、配信を終えると、コンテナが自ら消滅（`--rm`）する」という、ホストマシンのリソースを無駄にしないハイブリッドバッチアーキテクチャを実現しました。

<p align="right">(<a href="#top">トップへ</a>)</p>

---

## リポジトリ構成

```
it-news-system/
├── README.md
├── CHANGELOG.md
├── Dockerfile              # コンテナイメージ定義（v1.3.0 / ★v1.3.1）
├── compose.yaml            # Docker Compose サービス定義（v1.3.0 / ★v1.3.1）
├── requirements.txt
├── src/
│   ├── main.py             # エントリポイント（バッチ処理）
│   ├── __init__.py         # パッケージ初期化（★v1.2.0）
│   ├── api.py              # FastAPI サーバー・エンドポイント定義（v1.2.0 / ★v1.3.1）
│   ├── service.py          # 収集〜分析〜ランキングのオーケストレーション
│   ├── ranking.py          # ランキング生成ロジック
│   ├── gemini_analyzer.py  # Gemini API による AI 分析
│   ├── rss_fetcher.py      # RSS 取得
│   ├── db.py               # DB 操作（コンテキストマネージャー対応）
│   ├── mail_sender.py      # メール送信処理
│   ├── models.py           # Pydantic・データモデル定義
│   ├── config.py           # パス・API・通知しきい値など
│   ├── constants.py        # アプリケーション定数定義
│   ├── exceptions.py       # カスタム例外定義
│   ├── queries.py          # データベースクエリ定義
│   ├── logger.py
│   └── my_utils.py         # SMTP 送信ヘルパ
├── data/                   # SQLite（ホストボリュームとしてマウント）
│   └── news.db
└── logs/                   # ログ出力先（ホストボリュームとしてマウント）
    └── it_news_system.log
```

<p align="right">(<a href="#top">トップへ</a>)</p>

---

## Dockerfile の設計

本プロジェクトの `Dockerfile` は、**軽量な Python 3.12 ベースイメージ**を起点とし、本番相当の API サーバー起動をデフォルトとする構成です。

### 構成の概要

| ステップ | 内容 | 意図 |
|---------|------|------|
| ベースイメージ | `python:3.12-slim` | 最小限の OS フットプリントで Python 3.12 実行環境を確保 |
| システム依存 | `curl` | Compose `healthcheck` から `/health` へ HTTP リクエストを送るために使用（★v1.3.1） |
| 環境変数 | `PYTHONDONTWRITEBYTECODE=1` | `.pyc` ファイル生成を抑制し、イメージサイズと不要ファイルを削減 |
| 環境変数 | `PYTHONUNBUFFERED=1` | 標準出力・エラー出力をバッファリングせず、コンテナログに即時反映 |
| 環境変数 | `PYTHONPATH=/app` | 絶対インポート（`src.*`）の探索ルートを固定し、実行環境の差異を排除 |
| システム依存 | `build-essential` | 一部 Python パッケージのネイティブコンパイルに備える |
| 依存インストール | `requirements.txt` を先に COPY | Docker レイヤーキャッシュを活用し、ソース変更時の再ビルドを高速化 |
| ソース配置 | `COPY src/ ./src/` | アプリケーションコードを `/app/src/` に配置 |
| ディレクトリ確保 | `mkdir -p data logs` | Fail-Fast 回避のため、永続化・ログ用ディレクトリを事前作成 |
| ポート公開 | `EXPOSE 8080` | FastAPI サーバーの待受ポートを明示 |
| デフォルト CMD | `fastapi run src/api.py --port 8080 --host 0.0.0.0` | コンテナ単体起動時は API サーバーとして動作（Compose 側でも上書き可能） |

### compose.yaml との連携

`compose.yaml` では同一イメージから 2 つのサービスを定義しています。

| サービス | 役割 | 起動方法 |
|---------|------|---------|
| `api` | FastAPI サーバーを常時起動 | `docker compose up -d` |
| `worker` | RSS 取得〜分析〜メール配信バッチ | `docker compose run --rm worker` |

両サービスとも `./data` と `./logs` をホストにマウントし、**バッチ処理で更新された SQLite データを API サーバーが即座に参照できる**設計です。`worker` は `profiles: ["manual"]` により、`up -d` 時の自動起動を抑制し、必要なタイミングでのみ実行します。

`api` サービスには `healthcheck`（30 秒間隔で `GET /health` を確認）と `restart: always` を設定しており、API サーバーの死活監視と異常時の自動再起動に対応しています（★v1.3.1）。

<p align="right">(<a href="#top">トップへ</a>)</p>

---

## セットアップと実行 (Setup & Execution)

本システムは **Docker (Compose v2)** を用いたコンテナ環境に完全対応しています。ホストマシンの Python 環境を汚染することなく、依存パッケージのビルドからサーバーの起動までを 1 コマンドで完結できます。

### 1. 前提条件 (Prerequisites)

- Docker Engine (v25.0 以上推奨)
- Docker Compose (v2.0 以上)
- Google Gemini API キー ([Google AI Studio](https://aistudio.google.com/) より取得)

### 2. 環境変数の配置

リポジトリルートに `.env` ファイルを配置し、必要な認証情報を記述します。コンテナ起動時に自動的に読み込まれます。

```env
GEMINI_API_KEY=your_api_key_here
GMAIL_USER=your_email@gmail.com
GMAIL_PASS=your_app_password_here
```

#### 環境変数一覧

| 変数名 | 役割 | 備考 |
|--------|------|------|
| `GEMINI_API_KEY` | Gemini API の認証キー | Google AI Studio で発行 |
| `GMAIL_USER` | 送信元 Gmail アドレス | 自身の取得アドレスを記載 |
| `GMAIL_PASS` | Gmail の SMTP 用パスワード | アプリパスワードを推奨 |

#### アプリケーション内部動作設定（`src/config.py`）

| 変数名 | 役割 | 推奨設定値 |
|--------|------|-----------|
| `IMPORTANCE_THRESHOLD` | 配信対象（重要度）のしきい値（1〜10） | `7` |
| `NOTIFICATION_LOOKBACK_DAYS` | スコアリング対象とする過去日数 | `7` |
| `NOTIFICATION_LIMIT` | 1 度に送る最大記事数 | `5` |
| `FRESHNESS_TABLE` | 経過日数に対応する鮮度係数 | 3 日目まで緩やか、4 日目以降急激に減衰 |

```
FRESHNESS_TABLE = {
    0: 1.00,  # 当日
    1: 0.95,  # 1日後
    2: 0.90,  # 2日後
    3: 0.85,  # 3日後
    4: 0.60,  # 4日後（ここから急激に低下）
    5: 0.40,
    6: 0.20,
    7: 0.10,  # 7日後（実質的な掲載期限）
}
```

プロジェクトのルートディレクトリで以下のコマンドを実行します。

```bash
# コンテナのビルドおよびバックグラウンド起動
docker compose up -d
```

起動後、自動的に API サーバーが立ち上がります。

- **接続確認**: [http://localhost:8080/](http://localhost:8080/) へアクセス
- **インタラクティブ API ドキュメント (Swagger UI)**: [http://localhost:8080/docs](http://localhost:8080/docs) へアクセス

#### 公開 API エンドポイント一覧

| エンドポイント | メソッド | 概要 |
|--------------|---------|------|
| `/v1/rankings` | GET | 直近のバッチでスコアリングされた高重要度記事のランキング一覧 |
| `/v1/notifications` | GET | しきい値を満たした通知対象記事の最新スナップショット |
| `/health` | GET | API サーバーの死活監視用（Docker Compose healthcheck から利用）（★v1.3.1） |
| `/docs` | GET | Swagger UI（仕様確認・対話型 API テスト） |

### 4. ニュース収集・分析バッチの自律定期実行 (Worker CLI)

ホストOS（Ubuntu）側の定期実行タスクスケジューラー（cron）に登録した `worker` コンテナが、毎日朝7時に自動で立ち上がり、RSS フィードの取得、LLM による重要度分析、ランキング生成、メール配信のパイプラインを実行します。ホストのターミナルで `crontab -e` を実行し、以下のタスクを登録します。

```bash
#毎朝7:00に自動でプロジェクトルートへ移動し、一時的なコンテナで worker をオンデマンド実行
0 7 * * * cd /path/to/it-news-system && /usr/bin/docker compose run --rm worker >> /path/to/it-news-system/logs/cron.log 2>&1
```

### 5.動作および死活監視の確認
APIコンテナが正常に健康状態を宣言できているか確認するには、以下のコマンドのカッコ内のステータスを確認します。

```bash
# STATUSに 「Up X minutes (healthy)」 と刻まれていれば正常にヘルスチェックが回っています
docker compose ps
```


<p align="right">(<a href="#top">トップへ</a>)</p>

---

## トラブルシューティング

### コンテナが起動しない / ビルドに失敗する

Docker Engine と Compose v2 がインストールされているか確認してください。`docker compose build --no-cache` でキャッシュを無視して再ビルドできます。

### `.env` が読み込まれない／キーが空になる

`.env` は **プロジェクトルート**（`README.md` と同じ階層）に置いてください。変数名の typo と値前後の余分な引用符も確認してください。

### `data/` または `logs/` が無い

初回起動前に `mkdir -p data logs` を実行してください。Dockerfile 内でも作成していますが、ホスト側のマウント先ディレクトリは事前に用意しておくと安全です。

### API サーバーに接続できない

`docker compose ps` で `api` サービスが `running` か確認してください。ポート 8080 が他プロセスで使用されていないかも確認します。`docker inspect --format='{{.State.Health.Status}}' it-news-api` でヘルスチェック状態（`healthy` / `unhealthy`）も確認できます。

### Worker バッチが失敗する

`docker compose run --rm worker` の標準出力と `logs/it_news_system.log` を確認してください。Gemini API キーや Gmail 認証情報の設定ミスが多い原因です。

### Gemini API からエラーが返る

`GEMINI_API_KEY` の有効性とクォータを確認してください。429（レート制限）の場合は間隔を空けて再実行するか、1 バッチあたりの記事数を下げてください。

### `database is locked`（SQLite）

`api` と `worker` が同時に `news.db` へ書き込もうとすると発生します。バッチ実行中は API への書き込み系操作を避けるか、バッチ完了後に再試行してください。

### メールが届かない

Gmail は**アプリパスワード**を使用してください。また、`IMPORTANCE_THRESHOLD` が高すぎて通知候補が 0 件になっていないか確認してください。

### ランキングスコアが意図通りにならない

`config.py` の `FRESHNESS_TABLE` と `DEFAULT_MIN_IMPORTANCE` を見直してください。スコアは「重要度 × 鮮度係数」で算出されるため、重要度が低い記事は鮮度が高くても上位に来ません。

### 記事の公開日時が正しく表示されない

RSS フィードによっては RFC 2822 形式以外の日時文字列を返す場合があります。`logs/it_news_system.log` でパースエラーが出ていないか確認してください。

<p align="right">(<a href="#top">トップへ</a>)</p>


## ライセンス・連絡

リポジトリにライセンスファイルを置く場合は、そのファイルに従ってください。案件相談・ポートフォリオに関する連絡は、プロフィールに記載の連絡先までお願いします。