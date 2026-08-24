"""
Gemini AI service for PDF-Compress-Master.
"""

import os
from typing import Optional

from dotenv import load_dotenv
from google import genai


load_dotenv()


class AIServiceError(Exception):
    """Error dari AI service."""
    pass


GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise AIServiceError(
        "GEMINI_API_KEY belum dikonfigurasi."
    )


client = genai.Client(
    api_key=GEMINI_API_KEY
)


MODEL_NAME = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.6-flash"
)


SYSTEM_INSTRUCTION = """
Kamu adalah PDF Master AI, asisten AI yang ramah, jelas,
dan membantu.

Gunakan percakapan sebelumnya hanya sebagai konteks untuk
memahami maksud pengguna.

Selalu prioritaskan dan jawab pesan pengguna yang TERBARU.

Jangan mengulang jawaban dari pertanyaan sebelumnya kecuali
pengguna memang meminta pengulangan atau rangkuman.

Jika pengguna menggunakan kata seperti:
- "itu"
- "ini"
- "contohnya"
- "jelaskan lagi"
- "bagaimana dengan itu"
- "lanjutkan"

gunakan konteks percakapan sebelumnya untuk memahami
apa yang dimaksud pengguna.

Jangan mengatakan "berikut jawaban untuk pertanyaan pertama
dan kedua" hanya karena terdapat beberapa pesan dalam riwayat.

Jawablah secara natural seperti percakapan biasa.

Gunakan bahasa yang sama dengan bahasa pengguna, kecuali
pengguna meminta bahasa tertentu.
"""


async def generate_reply(
    message: str,
    conversation: Optional[list[dict]] = None,
) -> str:
    """
    Mengirim pesan terbaru ke Gemini dengan conversation memory.
    """

    message = (message or "").strip()

    if not message:
        raise AIServiceError(
            "Pesan tidak boleh kosong."
        )

    try:
        contents = []

        # =====================================================
        # CONVERSATION MEMORY
        # =====================================================

        if isinstance(conversation, list):

            for item in conversation:

                if not isinstance(item, dict):
                    continue

                role = item.get("role")
                text = (
                    item.get("content")
                    or item.get("text")
                    or ""
                )

                text = str(text).strip()

                if not text:
                    continue

                # User message
                if role == "user":

                    contents.append({
                        "role": "user",
                        "parts": [
                            {
                                "text": text
                            }
                        ],
                    })

                # Assistant message
                elif role in ("assistant", "model"):

                    contents.append({
                        "role": "model",
                        "parts": [
                            {
                                "text": text
                            }
                        ],
                    })

        # =====================================================
        # PESAN TERBARU
        # =====================================================

        contents.append({
            "role": "user",
            "parts": [
                {
                    "text": message
                }
            ],
        })

        # =====================================================
        # GEMINI
        # =====================================================

        response = await client.aio.models.generate_content(
            model=MODEL_NAME,
            contents=contents,
            config={
                "system_instruction": SYSTEM_INSTRUCTION,
            },
        )

        reply = getattr(
            response,
            "text",
            None
        )

        if not reply:
            raise AIServiceError(
                "Gemini tidak mengembalikan jawaban."
            )

        return reply.strip()

    except AIServiceError:
        raise

    except Exception as error:
        raise AIServiceError(
            f"Gagal menghubungi Gemini: {str(error)}"
        )