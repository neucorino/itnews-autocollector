import logging
from logging.handlers import RotatingFileHandler
from config import LOG_FILE, LOG_MAX_BYTES, LOG_BACKUP_COUNT

def setup_logger():
    """ロギングを設定して、loggerオブジェクトを返す"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            RotatingFileHandler(LOG_FILE, maxBytes=LOG_MAX_BYTES, backupCount=LOG_BACKUP_COUNT),
            logging.StreamHandler()
        ]
    )