from typing import Optional
from exceptions import EmailSendError
import smtplib
from email.mime.text import MIMEText
from email.utils import formatdate
import config
import logging

logger = logging.getLogger(__name__)

def send_gmail(subject: str, body: str, to_address: Optional[str] = None) -> None:
    """
    どこからでもメールを送れる共通関数
    """
    if to_address is None:
        to_address = config.FROM_ADDRESS  # 指定がなければ自分に送る

    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = config.FROM_ADDRESS
    msg['To'] = to_address
    msg['Date'] = formatdate()

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(config.FROM_ADDRESS, config.MY_PASSWORD)
            smtp.send_message(msg)
        logger.info(f"📧 メール送信成功: {subject}")
    except Exception as e:
        logger.exception(f"❌ メール送信エラー")
        raise EmailSendError(f"メール送信に失敗しました: {subject}") from e
