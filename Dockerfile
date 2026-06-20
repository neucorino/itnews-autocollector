# ==============================================================================
# ステージ1: アプリケーションのベース環境を構築
# ==============================================================================
FROM python:3.12-slim

# コンテナ内の作業ディレクトリを設定
WORKDIR /app

# Pythonがpycファイルを作成するのを防ぐ
ENV PYTHONDONTWRITEBYTECODE=1
# 標準出力・エラー出力をバッファリングせず、即座にログに出力する
ENV PYTHONUNBUFFERED=1
# Pythonのモジュール探索ルートを/appに固定（絶対インポートの担保）
ENV PYTHONPATH=/app

# システム依存関係のインストール（必要に応じてコンパイル環境等を導入）
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 先に依存ライブラリをコピーしてインストール（レイヤーキャッシュの活用）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションのソースコードと、設定ファイルを配置
COPY src/ ./src/

# データ永続化・ログ用のディレクトリをコンテナ内に事前に確保
RUN mkdir -p data logs

# ポートの開放（FastAPIのデフォルトポート8080を想定）
EXPOSE 8080

# コンテナ起動時のデフォルトコマンド（Compose側で上書き可能）
CMD ["fastapi", "run", "src/api.py", "--port", "8080", "--host", "0.0.0.0"]