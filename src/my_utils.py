import smtplib
from email.mime.text import MIMEText
from email.utils import formatdate
import os
from dotenv import load_dotenv

# .env ファイルから設定を読み込む
load_dotenv()
FROM_ADDRESS = os.getenv('GMAIL_USER')
MY_PASSWORD = os.getenv('GMAIL_PASS')

def send_gmail(subject, body, to_address=None):
    """
    どこからでもメールを送れる共通関数
    """
    if to_address is None:
        to_address = FROM_ADDRESS  # 指定がなければ自分に送る

    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = FROM_ADDRESS
    msg['To'] = to_address
    msg['Date'] = formatdate()

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(FROM_ADDRESS, MY_PASSWORD)
            smtp.send_message(msg)
        print(f"📧 メール送信成功: {subject}")
    except Exception as e:
        print(f"❌ メール送信エラー: {e}")
