from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from argon2 import PasswordHasher
from datetime import datetime, timezone, timedelta
import hashlib
import secrets
from authlib.integrations.starlette_client import OAuth
from dotenv import load_dotenv
import os

from app.core.database import get_db
from app.core.models import User
from app.services.email_verification import (
    create_verification_token,
    hash_verification_token,
    create_reset_token,
    create_reset_code,
    hash_reset_code
)
from app.services.email_sender import send_verification_email, send_reset_password_email, send_reset_code_email


router = APIRouter(
    prefix="/api/auth",
    tags=["Authentication"]
)

# ============================================================
# GOOGLE OAUTH
# ============================================================

load_dotenv()

FRONTEND_URL = os.getenv(
    "FRONTEND_URL",
    "http://127.0.0.1:5500"
).rstrip("/")

oauth = OAuth()

oauth.register(
    name="google",
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    authorize_url="https://accounts.google.com/o/oauth2/v2/auth",
    access_token_url="https://oauth2.googleapis.com/token",
    jwks_uri="https://www.googleapis.com/oauth2/v3/certs",
    userinfo_endpoint="https://openidconnect.googleapis.com/v1/userinfo",
    client_kwargs={
        "scope": "openid email profile"
    }
)

@router.get("/google")
async def google_login(request: Request):
    redirect_uri = os.getenv(
        "GOOGLE_REDIRECT_URI",
        "http://127.0.0.1:8000/api/auth/google/callback"
    )

    return await oauth.google.authorize_redirect(
        request,
        redirect_uri,
        prompt="select_account"
    )


@router.get("/google/callback")
async def google_callback(
    request: Request,
    db: Session = Depends(get_db)
):
    token = await oauth.google.authorize_access_token(request)

    userinfo = token.get("userinfo")

    if not userinfo:
        raise HTTPException(
            status_code=400,
            detail="Google user information was not returned."
        )

    google_id = userinfo.get("sub")
    email = userinfo.get("email")
    name = userinfo.get("name") or email

    if not google_id or not email:
        raise HTTPException(
            status_code=400,
            detail="Google account information is incomplete."
        )

    email = email.lower().strip()

    user = (
        db.query(User)
        .filter(User.email == email)
        .first()
    )

    if not user:
        user = User(
            name=name[:100],
            email=email,
            password_hash=None,
            is_verified=True,
            plan="FREE",
            google_id=google_id
        )

        db.add(user)
        db.commit()
        db.refresh(user)

    else:
        user.google_id = google_id
        user.is_verified = True
        user.last_login = datetime.now(timezone.utc)

        db.commit()

    redirect_url = f"{FRONTEND_URL}/pages/dashboard.html"

    print("GOOGLE LOGIN BERHASIL")
    print("USER:", user.email)
    print("FRONTEND_URL:", FRONTEND_URL)
    print("REDIRECT:", redirect_url)

    return RedirectResponse(
        url=redirect_url,
        status_code=302
    )

password_hasher = PasswordHasher()


# ============================================================
# REGISTER
# ============================================================

class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str


class RegisterResponse(BaseModel):
    message: str
    user_id: int


@router.post("/register", response_model=RegisterResponse)
def register(
    data: RegisterRequest,
    db: Session = Depends(get_db)
):
    email = data.email.lower().strip()
    name = data.name.strip()

    if not name:
        raise HTTPException(
            status_code=400,
            detail="Name is required."
        )

    if len(data.password) < 8:
        raise HTTPException(
            status_code=400,
            detail="Password must contain at least 8 characters."
        )

    existing_user = (
        db.query(User)
        .filter(User.email == email)
        .first()
    )

    if existing_user:
        raise HTTPException(
            status_code=409,
            detail="Email is already registered."
        )

    password_hash = password_hasher.hash(data.password)

    (
        verification_code,
        verification_code_hash,
        verification_expires_at
    ) = create_verification_token()

    user = User(
        name=name,
        email=email,
        password_hash=password_hash,
        is_verified=False,
        plan="FREE",
        verification_token_hash=verification_code_hash,
        verification_expires_at=verification_expires_at
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    send_verification_email(
        recipient_email=user.email,
        recipient_name=user.name,
        verification_code=verification_code
    )

    return RegisterResponse(
        message="Registration successful. Verification code has been sent to your email.",
        user_id=user.id
    )


# ============================================================
# VERIFY EMAIL
# ============================================================

class VerifyEmailRequest(BaseModel):
    email: EmailStr
    code: str


class VerifyEmailResponse(BaseModel):
    message: str


@router.post("/verify-email", response_model=VerifyEmailResponse)
def verify_email(
    data: VerifyEmailRequest,
    db: Session = Depends(get_db)
):
    email = data.email.lower().strip()
    code = data.code.strip()

    if not code.isdigit() or len(code) != 6:
        raise HTTPException(
            status_code=400,
            detail="Kode verifikasi harus terdiri dari 6 digit."
        )

    user = (
        db.query(User)
        .filter(User.email == email)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=400,
            detail="Email atau kode verifikasi tidak valid."
        )

    if user.is_verified:
        return VerifyEmailResponse(
            message="Email sudah diverifikasi."
        )

    if not user.verification_token_hash:
        raise HTTPException(
            status_code=400,
            detail="Kode verifikasi tidak tersedia."
        )

    if not user.verification_expires_at:
        raise HTTPException(
            status_code=400,
            detail="Kode verifikasi tidak tersedia."
        )

    expires_at = user.verification_expires_at

    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=400,
            detail="Kode verifikasi sudah kedaluwarsa."
        )

    code_hash = hash_verification_token(code)

    if code_hash != user.verification_token_hash:
        raise HTTPException(
            status_code=400,
            detail="Kode verifikasi salah."
        )

    user.is_verified = True
    user.verification_token_hash = None
    user.verification_expires_at = None

    db.commit()

    return VerifyEmailResponse(
        message="Email berhasil diverifikasi. Akun Anda sekarang aktif."
    )


# ============================================================
# LOGIN
# ============================================================

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    message: str
    user_id: int
    name: str
    email: str


@router.post("/login", response_model=LoginResponse)
def login(
    data: LoginRequest,
    db: Session = Depends(get_db)
):
    email = data.email.lower().strip()

    user = (
        db.query(User)
        .filter(User.email == email)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Email atau password salah."
        )

    if not user.password_hash:
        raise HTTPException(
            status_code=401,
            detail="Email atau password salah."
        )

    try:
        password_hasher.verify(
            user.password_hash,
            data.password
        )
    except Exception:
        raise HTTPException(
            status_code=401,
            detail="Email atau password salah."
        )

    if not user.is_verified:
        raise HTTPException(
            status_code=403,
            detail="Email belum diverifikasi."
        )

    user.last_login = datetime.now(timezone.utc)

    db.commit()

    return LoginResponse(
        message="Login berhasil.",
        user_id=user.id,
        name=user.name,
        email=user.email
    )


# ============================================================
# FORGOT PASSWORD
# ============================================================

class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ForgotPasswordResponse(BaseModel):
    message: str


@router.post(
    "/forgot-password",
    response_model=ForgotPasswordResponse
)
def forgot_password(
    data: ForgotPasswordRequest,
    db: Session = Depends(get_db)
):
    email = data.email.lower().strip()

    user = (
        db.query(User)
        .filter(User.email == email)
        .first()
    )

    # Jangan membocorkan apakah email terdaftar
    if not user:
        return ForgotPasswordResponse(
            message="Jika email terdaftar, kode reset password akan dikirim."
        )

    # Generate kode reset 6 digit
    reset_code, reset_code_hash, reset_code_expires_at = create_reset_code()

    user.reset_code_hash = reset_code_hash
    user.reset_code_expires_at = reset_code_expires_at

    # Hapus token reset lama
    user.reset_token_hash = None
    user.reset_expires_at = None

    db.commit()

    # Kirim kode 6 digit ke email
    send_reset_code_email(
        recipient_email=user.email,
        recipient_name=user.name,
        reset_code=reset_code
    )

    return ForgotPasswordResponse(
        message="Kode reset password telah dikirim ke email."
    )



# ============================================================
# VERIFY RESET PASSWORD CODE
# ============================================================

class VerifyResetCodeRequest(BaseModel):
    email: EmailStr
    code: str


class VerifyResetCodeResponse(BaseModel):
    message: str
    reset_token: str


@router.post(
    "/verify-reset-code",
    response_model=VerifyResetCodeResponse
)
def verify_reset_code(
    data: VerifyResetCodeRequest,
    db: Session = Depends(get_db)
):
    email = data.email.lower().strip()
    code = data.code.strip()

    # Validasi format kode
    if not code.isdigit() or len(code) != 6:
        raise HTTPException(
            status_code=400,
            detail="Kode reset harus terdiri dari 6 digit."
        )

    user = (
        db.query(User)
        .filter(User.email == email)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=400,
            detail="Email atau kode reset tidak valid."
        )

    if not user.reset_code_hash:
        raise HTTPException(
            status_code=400,
            detail="Kode reset tidak tersedia atau sudah digunakan."
        )

    if not user.reset_code_expires_at:
        raise HTTPException(
            status_code=400,
            detail="Kode reset tidak tersedia atau sudah kedaluwarsa."
        )

    # Pastikan timezone aman
    expires_at = user.reset_code_expires_at

    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    # Cek expired
    if expires_at < datetime.now(timezone.utc):
        user.reset_code_hash = None
        user.reset_code_expires_at = None
        db.commit()

        raise HTTPException(
            status_code=400,
            detail="Kode reset sudah kedaluwarsa."
        )

    # Hash kode yang dikirim user
    code_hash = hash_reset_code(code)

    # Cocokkan kode
    if code_hash != user.reset_code_hash:
        raise HTTPException(
            status_code=400,
            detail="Kode reset salah."
        )

    # Buat token baru untuk tahap reset password
    reset_token = secrets.token_urlsafe(32)

    reset_token_hash = hashlib.sha256(
        reset_token.encode("utf-8")
    ).hexdigest()

    reset_expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=10
    )

    user.reset_token_hash = reset_token_hash
    user.reset_expires_at = reset_expires_at

    # Kode 6 digit hanya boleh digunakan sekali
    user.reset_code_hash = None
    user.reset_code_expires_at = None

    db.commit()

    return VerifyResetCodeResponse(
        message="Kode reset password berhasil diverifikasi.",
        reset_token=reset_token
    )



# ============================================================
# RESET PASSWORD
# ============================================================

class ResetPasswordRequest(BaseModel):
    reset_token: str
    new_password: str


class ResetPasswordResponse(BaseModel):
    message: str


@router.post(
    "/reset-password",
    response_model=ResetPasswordResponse
)
def reset_password(
    data: ResetPasswordRequest,
    db: Session = Depends(get_db)
):
    reset_token = data.reset_token.strip()
    new_password = data.new_password

    # Validasi password
    if len(new_password) < 8:
        raise HTTPException(
            status_code=400,
            detail="Password minimal 8 karakter."
        )

    if not reset_token:
        raise HTTPException(
            status_code=400,
            detail="Reset token tidak ditemukan."
        )

    # Hash token yang diterima
    reset_token_hash = hashlib.sha256(
        reset_token.encode("utf-8")
    ).hexdigest()

    # Cari user berdasarkan token
    user = (
        db.query(User)
        .filter(User.reset_token_hash == reset_token_hash)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=400,
            detail="Reset token tidak valid."
        )

    # Pastikan token mempunyai waktu kedaluwarsa
    if not user.reset_expires_at:
        raise HTTPException(
            status_code=400,
            detail="Reset token tidak tersedia."
        )

    expires_at = user.reset_expires_at

    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(
            tzinfo=timezone.utc
        )

    # Cek expired
    if expires_at < datetime.now(timezone.utc):
        user.reset_token_hash = None
        user.reset_expires_at = None
        db.commit()

        raise HTTPException(
            status_code=400,
            detail="Reset token sudah kedaluwarsa."
        )

    # Hash password baru menggunakan Argon2
    password_hasher = PasswordHasher()

    user.password_hash = password_hasher.hash(
        new_password
    )

    # Token hanya boleh digunakan sekali
    user.reset_token_hash = None
    user.reset_expires_at = None

    user.last_login = datetime.now(timezone.utc)

    db.commit()

    return ResetPasswordResponse(
        message="Password berhasil diubah."
    )



