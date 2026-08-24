"""
PDF AI Chat Service
Mengirim pertanyaan pengguna bersama konteks PDF ke Gemini.
"""

from typing import Optional

from app.services.ai_service import (
    client,
    MODEL_NAME,
    AIServiceError,
)


PDF_SYSTEM_INSTRUCTION = """
Kamu adalah PDF Master AI.

Tugasmu adalah membantu pengguna memahami isi dokumen PDF
yang diberikan.

ATURAN UTAMA:

1. Jawab berdasarkan isi PDF.
2. Jangan mengarang informasi yang tidak terdapat dalam PDF.
3. Jika informasi tidak ditemukan dalam PDF, katakan dengan jujur
   bahwa informasi tersebut tidak ditemukan dalam dokumen.
4. Gunakan bahasa yang sama dengan bahasa pengguna.
5. Jawaban harus jelas, natural, dan mudah dipahami.
6. Jika pengguna meminta rangkuman, buat rangkuman berdasarkan PDF.
7. Jika pengguna meminta penjelasan, jelaskan berdasarkan isi PDF.
8. Jika pengguna bertanya tentang halaman tertentu, prioritaskan
   bagian PDF yang berkaitan dengan halaman tersebut.
9. Jangan menampilkan seluruh isi PDF kecuali pengguna memang
   memintanya.
10. Jangan menganggap informasi di luar PDF sebagai fakta dari PDF.

KONTEKS DOKUMEN PDF AKAN DIBERIKAN SETELAH INSTRUKSI INI.
"""


async def ask_pdf(
    question: str,
    pdf_text: str,
    conversation: Optional[list[dict]] = None,
) -> str:

    question = (question or "").strip()

    if not question:
        raise AIServiceError(
            "Pertanyaan tidak boleh kosong."
        )

    if not pdf_text or not pdf_text.strip():
        raise AIServiceError(
            "Isi PDF tidak tersedia."
        )

    try:

        contents = []

        # =====================================================
        # KONTEKS PERCAKAPAN
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

                if role == "user":

                    contents.append({
                        "role": "user",
                        "parts": [
                            {
                                "text": text
                            }
                        ],
                    })

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
        # PDF + PERTANYAAN
        # =====================================================

        prompt = f"""
ISI DOKUMEN PDF:

---------------- PDF START ----------------

{pdf_text}

----------------- PDF END -----------------

PERTANYAAN PENGGUNA:

{question}

Jawablah pertanyaan pengguna berdasarkan isi dokumen PDF.
"""

        contents.append({
            "role": "user",
            "parts": [
                {
                    "text": prompt
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
                "system_instruction": PDF_SYSTEM_INSTRUCTION,
            },
        )

        reply = getattr(
            response,
            "text",
            None,
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
            f"Gagal memproses PDF dengan Gemini: {str(error)}"
        )