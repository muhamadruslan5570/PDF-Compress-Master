from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from pathlib import Path
from datetime import datetime, timezone
import json
import uuid


router = APIRouter(
    prefix="/api",
    tags=["History"]
)


# =========================================================
# STORAGE
# =========================================================

HISTORY_DIR = Path("storage/history")
HISTORY_FILE = HISTORY_DIR / "history.json"


def ensure_storage():
    """Memastikan folder dan file history tersedia."""
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)

    if not HISTORY_FILE.exists():
        HISTORY_FILE.write_text(
            "[]",
            encoding="utf-8"
        )


def load_history():
    """Membaca seluruh data history."""
    ensure_storage()

    try:
        data = json.loads(
            HISTORY_FILE.read_text(encoding="utf-8")
        )

        if not isinstance(data, list):
            return []

        return data

    except (json.JSONDecodeError, OSError):
        return []


def save_history(data):
    """Menyimpan data history."""
    ensure_storage()

    HISTORY_FILE.write_text(
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )


# =========================================================
# REQUEST MODEL
# =========================================================

class HistoryCreate(BaseModel):
    user_id: Optional[int] = 1
    type: str
    title: str
    filename: Optional[str] = None
    status: str = "success"


# =========================================================
# GET HISTORY
# =========================================================

@router.get("/history")
def get_history(user_id: int = 1):
    """
    Mengambil history milik user.
    """

    history = load_history()

    user_history = [
        item
        for item in history
        if item.get("user_id", 1) == user_id
    ]

    # Terbaru di atas
    user_history.sort(
        key=lambda item: item.get("created_at", ""),
        reverse=True
    )

    return {
        "success": True,
        "history": user_history,
        "total": len(user_history)
    }

# =========================================================
# GET HISTORY STATISTICS
# =========================================================

@router.get("/history/stats")
def get_history_stats(user_id: int = 1):
    """
    Mengambil statistik aktivitas user dari history.
    """

    history = load_history()

    user_history = [
        item
        for item in history
        if item.get("user_id", 1) == user_id
    ]

    # Hanya aktivitas yang berhasil
    successful = [
        item
        for item in user_history
        if item.get("status", "success") == "success"
    ]

    # =====================================================
    # HITUNG TOOL
    # =====================================================

    tool_counts = {
        "compress-pdf": 0,
        "merge-pdf": 0,
        "pdf-to-word": 0,
        "word-to-pdf": 0,
        "pdf-to-image": 0,
    }

    for item in successful:
        activity_type = item.get("type")

        if activity_type in tool_counts:
            tool_counts[activity_type] += 1

    # =====================================================
    # PDF PROCESSED
    # =====================================================

    pdfs_processed = len(successful)

    # =====================================================
    # STORAGE / OUTPUT SIZE
    # =====================================================

    total_output_size = 0

    for item in successful:
        file_size = item.get("file_size")

        if isinstance(file_size, (int, float)):
            total_output_size += file_size

        metadata = item.get("metadata") or {}

        output_size = metadata.get("output_size")

        if isinstance(output_size, (int, float)):
            total_output_size += 0

    # =====================================================
    # FORMAT STORAGE
    # =====================================================

    def format_size(size):
        if size < 1024:
            return f"{size} B"

        if size < 1024 * 1024:
            return f"{size / 1024:.2f} KB"

        if size < 1024 * 1024 * 1024:
            return f"{size / (1024 * 1024):.2f} MB"

        return f"{size / (1024 * 1024 * 1024):.2f} GB"

    # =====================================================
    # AI REQUESTS
    # =====================================================

    ai_types = {
        "ai-ppt",
        "ai-rpp",
        "ai-chat",
        "chat-ai",
    }

    ai_requests = sum(
        1
        for item in successful
        if item.get("type") in ai_types
    )

    # =====================================================
    # ACCOUNT STATUS
    # =====================================================

    account_status = "ACTIVE"

    # =====================================================
    # RESPONSE
    # =====================================================

    return {
        "success": True,

        "user_id": user_id,

        "stats": {
            "pdfs_processed": pdfs_processed,

            "storage_used": format_size(
                total_output_size
            ),

            "storage_bytes": total_output_size,

            "ai_requests": ai_requests,

            "account_status": account_status,

            "total_activities": len(user_history),

            "successful_activities": len(successful),

            "tools": tool_counts,
        }
    }

# =========================================================
# CREATE HISTORY
# =========================================================

@router.post("/history")
def create_history(data: HistoryCreate):
    """
    Menambahkan aktivitas baru ke history.
    """

    history = load_history()

    new_history = {
        "id": str(uuid.uuid4()),
        "user_id": data.user_id,
        "type": data.type,
        "title": data.title,
        "filename": data.filename,
        "status": data.status,
        "created_at": datetime.now(
            timezone.utc
        ).isoformat()
    }

    history.append(new_history)

    save_history(history)

    return {
        "success": True,
        "message": "History berhasil ditambahkan",
        "history": new_history
    }


# =========================================================
# DELETE SINGLE HISTORY
# =========================================================

@router.delete("/history/{history_id}")
def delete_history(
    history_id: str,
    user_id: int = 1
):
    """
    Menghapus satu history milik user.
    """

    history = load_history()

    target = None

    for item in history:
        if (
            item.get("id") == history_id
            and item.get("user_id", 1) == user_id
        ):
            target = item
            break

    if target is None:
        raise HTTPException(
            status_code=404,
            detail="History tidak ditemukan"
        )

    history.remove(target)

    save_history(history)

    return {
        "success": True,
        "message": "History berhasil dihapus",
        "deleted_id": history_id
    }


# =========================================================
# DELETE ALL HISTORY
# =========================================================

@router.delete("/history")
def delete_all_history(user_id: int = 1):
    """
    Menghapus seluruh history milik user.
    """

    history = load_history()

    remaining_history = [
        item
        for item in history
        if item.get("user_id", 1) != user_id
    ]

    deleted_count = (
        len(history) - len(remaining_history)
    )

    save_history(remaining_history)

    return {
        "success": True,
        "message": "Seluruh history berhasil dihapus",
        "deleted": deleted_count
    }