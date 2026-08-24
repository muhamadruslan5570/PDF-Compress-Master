from pathlib import Path
from datetime import datetime, timezone
from typing import Optional
import json
import uuid


# =========================================================
# STORAGE HISTORY
# =========================================================

BASE_DIR = Path(__file__).resolve().parent.parent.parent
HISTORY_DIR = BASE_DIR / "storage" / "history"
HISTORY_FILE = HISTORY_DIR / "history.json"


def ensure_history_storage():
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)

    if not HISTORY_FILE.exists():
        HISTORY_FILE.write_text(
            "[]",
            encoding="utf-8"
        )


def load_history():
    ensure_history_storage()

    try:
        data = json.loads(
            HISTORY_FILE.read_text(encoding="utf-8")
        )

        if isinstance(data, list):
            return data

    except (json.JSONDecodeError, OSError):
        pass

    return []


def save_history(history):
    ensure_history_storage()

    HISTORY_FILE.write_text(
        json.dumps(
            history,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )


# =========================================================
# RECORD ACTIVITY
# =========================================================

def record_activity(
    user_id: int = 1,
    activity_type: str = "unknown",
    title: str = "Aktivitas",
    filename: Optional[str] = None,
    status: str = "success",
    file_size: Optional[int] = None,
    metadata: Optional[dict] = None
):
    """
    Mencatat aktivitas user ke history.

    activity_type:
        compress-pdf
        pdf-to-image
        word-to-pdf
        pdf-to-word
        merge-pdf
        ai-ppt
        ai-rpp
        dll.
    """

    history = load_history()

    item = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "type": activity_type,
        "title": title,
        "filename": filename,
        "status": status,
        "file_size": file_size,
        "metadata": metadata or {},
        "created_at": datetime.now(
            timezone.utc
        ).isoformat()
    }

    history.append(item)

    save_history(history)

    return item