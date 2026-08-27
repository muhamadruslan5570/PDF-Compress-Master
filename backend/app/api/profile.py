import os
import json
import shutil
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, File, UploadFile, Query, Depends
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.models import User


router = APIRouter(
    prefix="/api/profile",
    tags=["Profile"]
)


BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
STORAGE_DIR = BASE_DIR / "backend" / "storage"
PROFILES_DIR = STORAGE_DIR / "profiles"
AVATARS_DIR = STORAGE_DIR / "avatars"

PROFILES_DIR.mkdir(parents=True, exist_ok=True)
AVATARS_DIR.mkdir(parents=True, exist_ok=True)


class ProfileUpdateSchema(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None


def get_profile_file(user_id: int) -> Path:
    return PROFILES_DIR / f"user_{user_id}.json"


def get_avatar_directory(user_id: int) -> Path:
    directory = AVATARS_DIR / f"user_{user_id}"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def get_user_or_404(user_id: int, db: Session) -> User:
    if user_id <= 0:
        raise HTTPException(
            status_code=400,
            detail="User ID tidak valid."
        )

    user = (
        db.query(User)
        .filter(User.id == user_id)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=404,
            detail="Pengguna tidak ditemukan."
        )

    return user


def default_profile(user: User) -> dict:
    return {
        "id": user.id,
        "name": user.name or "",
        "email": user.email or "",
        "phone": "",
        "plan": user.plan or "FREE",
        "avatar_url": None,
        "stats": {
            "pdfs_processed": 0,
            "storage_used": "0 MB",
            "ai_requests": 0
        }
    }


def read_profile_from_disk(user: User) -> dict:
    profile_file = get_profile_file(user.id)

    if not profile_file.exists():
        profile = default_profile(user)
        write_profile_to_disk(user.id, profile)
        return profile

    try:
        with open(profile_file, "r", encoding="utf-8") as f:
            profile = json.load(f)

        defaults = default_profile(user)

        for key, value in defaults.items():
            if key not in profile:
                profile[key] = value

        profile["id"] = user.id

        return profile

    except Exception:
        return default_profile(user)


def write_profile_to_disk(user_id: int, data: dict):
    profile_file = get_profile_file(user_id)

    with open(profile_file, "w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            indent=4,
            ensure_ascii=False
        )


def build_profile(user: User, profile: dict) -> dict:
    profile["id"] = user.id
    profile["name"] = user.name or profile.get("name", "")
    profile["email"] = user.email or profile.get("email", "")
    profile["plan"] = user.plan or profile.get("plan", "FREE")

    return profile


# ============================================================
# GET PROFILE
# ============================================================

@router.get("")
@router.get("/")
async def get_profile(
    user_id: int = Query(...),
    db: Session = Depends(get_db)
):
    user = get_user_or_404(user_id, db)

    profile = read_profile_from_disk(user)

    profile = build_profile(user, profile)

    write_profile_to_disk(user.id, profile)

    return profile


# ============================================================
# UPDATE PROFILE
# ============================================================

@router.put("")
@router.put("/")
async def update_profile(
    data: ProfileUpdateSchema,
    user_id: int = Query(...),
    db: Session = Depends(get_db)
):
    user = get_user_or_404(user_id, db)

    profile = read_profile_from_disk(user)

    if data.name is not None:
        name = data.name.strip()

        if name:
            user.name = name
            profile["name"] = name

    if data.email is not None:
        email = str(data.email).lower().strip()

        existing = (
            db.query(User)
            .filter(
                User.email == email,
                User.id != user.id
            )
            .first()
        )

        if existing:
            raise HTTPException(
                status_code=409,
                detail="Email sudah digunakan oleh pengguna lain."
            )

        user.email = email
        profile["email"] = email

    if data.phone is not None:
        profile["phone"] = data.phone.strip()

    db.commit()
    db.refresh(user)

    profile = build_profile(user, profile)

    write_profile_to_disk(user.id, profile)

    return profile


# ============================================================
# UPLOAD AVATAR
# ============================================================

@router.post("/avatar")
@router.post("/avatar/")
async def upload_avatar(
    file: UploadFile = File(...),
    user_id: int = Query(...),
    db: Session = Depends(get_db)
):
    user = get_user_or_404(user_id, db)

    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail="File harus berupa gambar (JPG, PNG, WebP)."
        )

    profile = read_profile_from_disk(user)
    user_avatar_dir = get_avatar_directory(user.id)

    old_avatar = profile.get("avatar_url")

    if old_avatar:
        old_filename = os.path.basename(
            old_avatar.split("?")[0]
        )

        old_file = user_avatar_dir / old_filename

        if old_file.exists():
            try:
                old_file.unlink()
            except Exception:
                pass

    ext = Path(file.filename or "").suffix.lower()

    if ext not in [".jpg", ".jpeg", ".png", ".webp"]:
        ext = ".png"

    filename = f"avatar_user_{user.id}{ext}"

    target_path = user_avatar_dir / filename

    try:
        with open(target_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Gagal menyimpan file gambar: {str(e)}"
        )

    avatar_url = (
        f"/storage/avatars/user_{user.id}/{filename}"
    )

    profile["avatar_url"] = avatar_url

    write_profile_to_disk(user.id, profile)

    return {
        "message": "Avatar berhasil diperbarui.",
        "avatar_url": avatar_url,
        "profile": build_profile(user, profile)
    }


# ============================================================
# DELETE AVATAR
# ============================================================

@router.delete("/avatar")
@router.delete("/avatar/")
async def delete_avatar(
    user_id: int = Query(...),
    db: Session = Depends(get_db)
):
    user = get_user_or_404(user_id, db)

    profile = read_profile_from_disk(user)

    avatar_url = profile.get("avatar_url")

    if avatar_url:
        filename = os.path.basename(
            avatar_url.split("?")[0]
        )

        user_avatar_dir = get_avatar_directory(user.id)

        file_path = user_avatar_dir / filename

        if file_path.exists():
            try:
                file_path.unlink()
            except Exception:
                pass

        profile["avatar_url"] = None

        write_profile_to_disk(user.id, profile)

    return {
        "message": "Avatar berhasil dihapus.",
        "profile": build_profile(user, profile)
    }
