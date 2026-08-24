import os
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv

load_dotenv()

SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")


def send_verification_email(
    recipient_email: str,
    recipient_name: str,
    verification_code: str
):
    message = EmailMessage()

    message["Subject"] = "Kode Verifikasi MR Compress PDF"
    message["From"] = SMTP_USERNAME
    message["To"] = recipient_email

    message.set_content(
        f"""
Halo {recipient_name},

Terima kasih telah membuat akun di MR Compress PDF.

Kode verifikasi email Anda:

{verification_code}

Masukkan kode tersebut pada halaman verifikasi email.

Kode ini berlaku selama 30 menit.

Jika Anda tidak membuat akun ini, abaikan email ini.

Salam,
MR Compress PDF
"""
    )

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.send_message(message)

def send_reset_password_email(
    recipient_email: str,
    recipient_name: str,
    reset_link: str
):
    message = EmailMessage()

    message["Subject"] = "Reset Password MR Compress PDF"
    message["From"] = SMTP_USERNAME
    message["To"] = recipient_email

    message.set_content(
        f"""
Halo {recipient_name},

Kami menerima permintaan untuk mengatur ulang password akun MR Compress PDF Anda.

Silakan klik link berikut untuk membuat password baru:

{reset_link}

Link reset password ini hanya berlaku selama 1 jam.

Jika Anda tidak meminta reset password, abaikan email ini.

Salam,
MR Compress PDF
"""
    )

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.send_message(message)


def send_reset_code_email(
    recipient_email: str,
    recipient_name: str,
    reset_code: str
):
    message = EmailMessage()

    message["Subject"] = "Kode Reset Password MR Compress PDF"
    message["From"] = SMTP_USERNAME
    message["To"] = recipient_email

    message.set_content(
        f"""
Halo {recipient_name},

Kami menerima permintaan untuk mengatur ulang password akun MR Compress PDF Anda.

Kode Reset Password Anda:

{reset_code}

Masukkan kode tersebut pada halaman Reset Password.

Kode ini berlaku selama 1 jam.

Jika Anda tidak meminta reset password, abaikan email ini.

Salam,
MR Compress PDF
"""
    )

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.send_message(message)
