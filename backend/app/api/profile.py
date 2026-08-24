import os
import json
import shutil
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException, File, UploadFile
from pydantic import BaseModel, EmailStr

router = APIRouter(
    prefix="/api/profile",
    tags=["Profile"]
)

# Jalur direktori penyimpanan fisik (menggunakan Pathlib untuk kompatibilitas Windows)
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent  # Merujuk ke root proyek
STORAGE_DIR = BASE_DIR / "backend" / "storage"
PROFILES_DIR = STORAGE_DIR / "profiles"
AVATARS_DIR = STORAGE_DIR / "avatars"
PROFILE_FILE = PROFILES_DIR / "profile.json"

# Pastikan folder fisik selalu ada
PROFILES_DIR.mkdir(parents=True, exist_ok=True)
AVATARS_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_PROFILE = {
    "name": "User Name",
    "email": "user@example.com",
    "phone": "",
    "plan": "FREE",
    "avatar_url": None,
    "stats": {
        "pdfs_processed": 0,
        "storage_used": "0 MB",
        "ai_requests": 0,
        "account_status": "FREE"
    }
}

class ProfileUpdateSchema(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None

def read_profile_from_disk() -> dict:
    if not PROFILE_FILE.exists():
        write_profile_to_disk(DEFAULT_PROFILE)
        return DEFAULT_PROFILE.copy()
    try:
        with open(PROFILE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Pastikan field default selalu ada jika tidak sengaja hilang
            for key, val in DEFAULT_PROFILE.items():
                if key not in data:
                    data[key] = val
            return data
    except Exception:
        return DEFAULT_PROFILE.copy()

def write_profile_to_disk(data: dict):
    with open(PROFILE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


# GET /api/profile
@router.get("")
@router.get("/")
async def get_profile():
    return read_profile_from_disk()


# PUT /api/profile (Memperbarui data tanpa menghapus field yang ada)
@router.put("")
@router.put("/")
async def update_profile(data: ProfileUpdateSchema):
    try:
        # 1. Baca data yang tersimpan saat ini
        profile = read_profile_from_disk()

        # 2. Update HANYA field yang dikirim dari form
        if data.name is not None and data.name.strip():
            profile["name"] = data.name.strip()

        if data.email is not None and data.email.strip():
            profile["email"] = data.email.strip()

        if data.phone is not None:
            profile["phone"] = data.phone.strip()

        # 3. Tulis kembali ke profile.json (field avatar_url, plan, stats TETAP AMAN)
        write_profile_to_disk(profile)

        return profile
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal memperbarui profil: {str(e)}")


# POST /api/profile/avatar
@router.post("/avatar")
@router.post("/avatar/")
async def upload_avatar(file: UploadFile = File(...)):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File harus berupa gambar (JPG, PNG, WebP).")

    profile = read_profile_from_disk()

    # Hapus file avatar lama jika ada di folder storage/avatars
    if profile.get("avatar_url"):
        old_filename = os.path.basename(profile["avatar_url"].split("?")[0])
        old_file_path = AVATARS_DIR / old_filename
        if old_file_path.exists():
            try:
                os.remove(old_file_path)
            except Exception:
                pass

    ext = Path(file.filename).suffix.lower()
    if not ext:
        ext = ".png"

    filename = f"avatar_user{ext}"
    target_path = AVATARS_DIR / filename

    try:
        with open(target_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal menyimpan file gambar: {str(e)}")

    avatar_url = f"/storage/avatars/{filename}"
    profile["avatar_url"] = avatar_url
    write_profile_to_disk(profile)

    return {"message": "Avatar berhasil diperbarui", "avatar_url": avatar_url, "profile": profile}


# DELETE /api/profile/avatar
@router.delete("/avatar")
@router.delete("/avatar/")
async def delete_avatar():
    profile = read_profile_from_disk()

    if profile.get("avatar_url"):
        filename = os.path.basename(profile["avatar_url"].split("?")[0])
        file_path = AVATARS_DIR / filename
        if file_path.exists():
            try:
                os.remove(file_path)
            except Exception:
                pass

        profile["avatar_url"] = None
        write_profile_to_disk(profile)

    return {"message": "Avatar berhasil dihapus", "profile": profile}


