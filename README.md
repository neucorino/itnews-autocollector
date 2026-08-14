<div id="top"></div>

# IT News Auto-Collector & Delivery System

**Version 1.5.1** — バックエンドを `backend/src/` へ、Dockerfile を `docker/` へ再配置し、フロントエンドとバックエンドのディレクトリ分離を明確化。ローカル／コンテナ双方でプロジェクトルートを正しく解決するようパス解決を調整。

<p style="display: inline">
  <img src="https://img.shields.io/badge/-Python-F2C63C.svg?logo=python&style=for-the-badge">
  <img src="https://img.shields.io/badge/-SQLite-003B57.svg?logo=sqlite&style=for-the-badge&logoColor=white">
  <img src="https://img.shields.io/badge/-Google%20Gemini-8E75B2.svg?logo=googlegemini&style=for-the-badge&logoColor=white">
  <img src="https://img.shields.io/badge/-FastAPI-009688.svg?logo=fastapi&style=for-the-badge&logoColor=white">
  <img src="https://img.shields.io/badge/-Docker-2496ED.svg?logo=docker&style=for-the-badge&logoColor=white">
  <img src="https://img.shields.io/badge/-Linux-FCC624.svg?logo=linux&style=for-the-badge&logoColor=black">
  <img src="https://img.shields.io/badge/-React-61DAFB.svg?logo=react&style=for-the-badge&logoColor=black">
  <img src="https://img.shields.io/badge/-TypeScript-3178C6.svg?logo=typescript&style=for-the-badge&logoColor=white">
  <img src="https://img.shields.io/badge/-Vite-646CFF.svg?logo=vite&style=for-the-badge&logoColor=white">
</p>

---

## 目次

1. [プロジェクト概要](#プロジェクト概要)
2. [Tech Stack](#tech-stack)
3. [セットアップ](#セットアップ)
4. [リポジトリ構成](#リポジトリ構成)
5. [ドキュメント](#ドキュメント)
6. [Roadmap](#roadmap)

---

## プロジェクト概要

ITニュース記事を自動収集し、Google Gemini APIを利用して記事の要約・重要度スコアリングを行うニュース収集システムです。

収集した記事はREST APIおよびWeb UIを通じて提供し、重要度の高いITニュースを効率的に閲覧できる環境を構築しています。

ユーザーごとの関心トピックや「いいね」などのフィードバック情報を活用したパーソナライズ機能にも対応し、個人に最適化されたニュース配信を目指しています。

### 主な機能

- **RSS取得**: 複数のニュースソースからRSSフィードを取得し、記事を自動収集
- **AI分析**: Google Gemini APIを使用して記事の要約・重要度スコアリングを実施
- **ランキング生成**: AI分析結果をもとに記事の重要度ランキングを生成
- **メール通知**: 重要度の高い記事をメールで通知
- **パーソナライズ基盤**: ユーザーの関心トピックや「いいね」情報を保存し、推薦機能に利用可能なデータを管理
- **REST API**: FastAPIによるAPIを提供し、ニュース・ユーザー情報・フィードバック情報を管理
- **フロントエンド**: React + TypeScript + ViteによるWeb UIを提供

### Highlights

- レイヤー分離と SQLite 制約でバッチと API を共存させる
- 重要度 × 鮮度減衰でランキングし、しきい値超えをメール通知する
- 同一イメージから `api`（常時）と `worker`（都度）を起動する

設計の詳細（構成図・DB・API契約）は [docs/architecture.md](docs/architecture.md) を参照してください。

<p align="right">(<a href="#top">トップへ</a>)</p>

---

## Tech Stack

| 分類        | 技術                      |
| --------- | ----------------------- |
| Backend   | FastAPI, Python 3.12    |
| Frontend  | React, TypeScript, Vite |
| Database  | SQLite                  |
| AI        | Google Gemini API       |
| Container | Docker, Docker Compose  |

| コンポーネント        | バージョン          |
| -------------- | -------------- |
| Docker Engine  | v25.0+         |
| Docker Compose | v2.0+          |
| Python         | 3.12 (Docker内) |

<p align="right">(<a href="#top">トップへ</a>)</p>

---

## セットアップ

本システムは **Docker (Compose v2)** を用いたコンテナ環境に完全対応しています。ホストマシンの Python 環境を汚染することなく、依存パッケージのビルドからサーバーの起動までを 1 コマンドで完結できます。

### 1. 前提条件 (Prerequisites)

- Docker Engine (v25.0 以上推奨)
- Docker Compose (v2.0 以上)
- Google Gemini API キー ([Google AI Studio](https://aistudio.google.com/) より取得)

### 2. 環境変数の配置

リポジトリルートに `.env` ファイルを配置し、必要な認証情報を記述します。コンテナ起動時に自動的に読み込まれます。各変数の意味は [docs/configuration.md](docs/configuration.md) を参照してください。

```env
GEMINI_API_KEY=your_api_key_here
GMAIL_USER=your_email@gmail.com
GMAIL_PASS=your_app_password_here
```

### 3. コンテナのビルドと起動

プロジェクトのルートディレクトリで以下のコマンドを実行します。

```bash
# コンテナのビルドおよびバックグラウンド起動
docker compose up -d
```

起動後、自動的に API サーバーが立ち上がります。

- **接続確認**: [http://localhost:8080/](http://localhost:8080/) へアクセス
- **インタラクティブ API ドキュメント (Swagger UI)**: [http://localhost:8080/docs](http://localhost:8080/docs) へアクセス

フロントエンドを動かす場合:

```bash
cd frontend && npm install && npm run dev
```

Vite 開発サーバーは [http://localhost:5173/](http://localhost:5173/) です。バッチの手動実行・cron は [docs/worker.md](docs/worker.md) を参照してください。

### 4. 動作および死活監視の確認

```bash
# STATUSに 「Up X minutes (healthy)」 と刻まれていれば正常にヘルスチェックが回っています
docker compose ps
```

<p align="right">(<a href="#top">トップへ</a>)</p>

---

## リポジトリ構成

```
it-news-system/
├── README.md
├── CHANGELOG.md
├── compose.yaml            # api（常時）と worker（オンデマンド）
├── requirements.txt
├── docker/
│   └── Dockerfile
├── docs/                   # 設計・設定・運用（下記ドキュメント）
├── frontend/               # React + TypeScript + Vite
├── backend/
│   └── src/                # FastAPI / バッチ / DB
├── data/                   # SQLite（ホストボリューム）
└── logs/                   # アプリログ・cron ログ
```

モジュール単位の責務は [docs/architecture.md](docs/architecture.md#3-レイヤーとモジュール) を参照してください。

<p align="right">(<a href="#top">トップへ</a>)</p>

---

## ドキュメント

| 文書 | 内容 |
|------|------|
| [docs/architecture.md](docs/architecture.md) | 構成、データフロー、DB、API 契約、Docker トポロジ |
| [docs/configuration.md](docs/configuration.md) | `.env` と `config.py` の値、検証ルール、CORS / 接続先 |
| [docs/worker.md](docs/worker.md) | バッチの起動、パイプライン、失敗時、cron |
| [CHANGELOG.md](CHANGELOG.md) | バージョンごとの変更履歴（Keep a Changelog） |

<p align="right">(<a href="#top">トップへ</a>)</p>

---

## Roadmap

```
v1.6.0  パーソナライズUI・API連携
         - 興味分野設定UI
         - いいね機能
         - パーソナライズAPIとの連携

v1.7.0  おすすめ機能
         - おすすめスコアの算出
         - 興味分野・いいね履歴を利用した表示順の最適化

v1.8.0  ニュース閲覧機能の強化
         - お気に入り機能
         - 既読管理
         - UI/UXの改善

v2.0.0  ユーザー認証・運用強化
         - JWT認証
         - マイページ
         - Slack / Discord通知
         - 非同期処理（async/await）
```

過去バージョンの詳細は [CHANGELOG.md](CHANGELOG.md) を参照してください。

<p align="right">(<a href="#top">トップへ</a>)</p>
