import hashlib
import secrets
from datetime import datetime, timedelta, timezone


TOKEN_EXPIRE_MINUTES = 30


def create_verification_token():
    code = f"{secrets.randbelow(1000000):06d}"

    code_hash = hashlib.sha256(
        code.encode("utf-8")
    ).hexdigest()

    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=TOKEN_EXPIRE_MINUTES
    )

    return code, code_hash, expires_at


def hash_verification_token(code: str):
    return hashlib.sha256(
        code.encode("utf-8")
    ).hexdigest()


RESET_TOKEN_EXPIRE_MINUTES = 30


def create_reset_token():
    token = secrets.token_urlsafe(32)

    token_hash = hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()

    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=RESET_TOKEN_EXPIRE_MINUTES
    )

    return token, token_hash, expires_at

# ============================================================
# RESET PASSWORD CODE
# ============================================================

RESET_CODE_EXPIRE_MINUTES = 10


def create_reset_code():
    code = f"{secrets.randbelow(1000000):06d}"

    code_hash = hashlib.sha256(
        code.encode("utf-8")
    ).hexdigest()

    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=RESET_CODE_EXPIRE_MINUTES
    )

    return code, code_hash, expires_at


def hash_reset_code(code: str):
    return hashlib.sha256(
        code.encode("utf-8")
    ).hexdigest()

