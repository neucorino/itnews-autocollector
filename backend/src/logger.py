import logging
from logging.handlers import RotatingFileHandler
from src.config import LOG_FILE, LOG_MAX_BYTES, LOG_BACKUP_COUNT

def setup_logger():
    """ロギングを設定して、loggerオブジェクトを返す"""
    # ルートロガーを取得
    root_logger = logging.getLogger()
    # 既存のハンドラをすべて削除し、重複を防ぐ
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            RotatingFileHandler(LOG_FILE, maxBytes=LOG_MAX_BYTES, backupCount=LOG_BACKUP_COUNT),
            logging.StreamHandler()
        ],
        force=True  # 既存のロガー設定を上書き
    )