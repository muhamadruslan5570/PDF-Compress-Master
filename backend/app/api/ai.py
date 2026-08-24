from fastapi import (
    APIRouter,
    HTTPException,
    UploadFile,
    File,
)
from pydantic import BaseModel, Field
from typing import Optional
from pathlib import Path
import uuid
import json

from app.services.ai_service import (
    generate_reply,
    AIServiceError,
)

from app.services.pdf_ai_service import (
    extract_pdf_text,
    PDFAIServiceError,
)


router = APIRouter(
    prefix="/api/ai",
    tags=["AI"],
)


# ============================================================
# AI CHAT BIASA
# ============================================================

class ChatRequest(BaseModel):
    message: str = Field(
        ...,
        min_length=1,
        max_length=10000,
    )

    conversation: Optional[list[dict]] = None


class ChatResponse(BaseModel):
    success: bool
    reply: str


@router.post(
    "/chat",
    response_model=ChatResponse,
)
async def chat(request: ChatRequest):

    try:
        reply = await generate_reply(
            message=request.message,
            conversation=request.conversation,
        )

        return ChatResponse(
            success=True,
            reply=reply,
        )

    except AIServiceError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=(
                f"Gagal memproses permintaan AI: "
                f"{str(error)}"
            ),
        )


# ============================================================
# PDF AI STORAGE
# ============================================================

PDF_AI_STORAGE = Path(
    "storage/pdf_ai"
)

PDF_AI_STORAGE.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# PDF UPLOAD
# ============================================================

class PDFUploadResponse(BaseModel):
    success: bool
    document_id: str
    filename: str
    pages: int
    characters: int
    method: str


@router.post(
    "/pdf/upload",
    response_model=PDFUploadResponse,
)
async def upload_pdf(
    file: UploadFile = File(...)
):

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="Nama file PDF tidak ditemukan.",
        )

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="File harus berformat PDF.",
        )

    try:

        # ----------------------------------------------------
        # Baca file
        # ----------------------------------------------------

        pdf_bytes = await file.read()

        if not pdf_bytes:
            raise HTTPException(
                status_code=400,
                detail="File PDF kosong.",
            )

        # ----------------------------------------------------
        # Ekstrak teks
        #
        # pypdf → PDF text layer
        # OCR   → PDF scan/gambar
        # ----------------------------------------------------

        result = extract_pdf_text(
            pdf_bytes,
            use_ocr=True,
        )

        # ----------------------------------------------------
        # ID dokumen
        # ----------------------------------------------------

        document_id = str(
            uuid.uuid4()
        )

        # ----------------------------------------------------
        # Data dokumen
        # ----------------------------------------------------

        document_data = {
            "document_id": document_id,
            "filename": file.filename,
            "pages": result["pages"],
            "characters": len(
                result["text"]
            ),
            "method": result["method"],
            "text": result["text"],
        }

        # ----------------------------------------------------
        # Simpan
        # ----------------------------------------------------

        document_path = (
            PDF_AI_STORAGE
            / f"{document_id}.json"
        )

        document_path.write_text(
            json.dumps(
                document_data,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        return PDFUploadResponse(
            success=True,
            document_id=document_id,
            filename=file.filename,
            pages=result["pages"],
            characters=len(
                result["text"]
            ),
            method=result["method"],
        )

    except PDFAIServiceError as error:

        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    except HTTPException:
        raise

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=(
                "Gagal membaca PDF: "
                f"{str(error)}"
            ),
        )


# ============================================================
# PDF CHAT
# ============================================================

class PDFChatRequest(BaseModel):

    document_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
    )

    message: str = Field(
        ...,
        min_length=1,
        max_length=10000,
    )

    conversation: Optional[list[dict]] = None


class PDFChatResponse(BaseModel):
    success: bool
    reply: str
    document_id: str


@router.post(
    "/pdf/chat",
    response_model=PDFChatResponse,
)
async def pdf_chat(
    request: PDFChatRequest
):

    try:

        # ----------------------------------------------------
        # Cari dokumen
        # ----------------------------------------------------

        document_path = (
            PDF_AI_STORAGE
            / f"{request.document_id}.json"
        )

        if not document_path.exists():

            raise HTTPException(
                status_code=404,
                detail="Dokumen PDF tidak ditemukan.",
            )

        # ----------------------------------------------------
        # Baca dokumen
        # ----------------------------------------------------

        document_data = json.loads(
            document_path.read_text(
                encoding="utf-8"
            )
        )

        pdf_text = document_data.get(
            "text",
            "",
        )

        if not pdf_text:

            raise HTTPException(
                status_code=400,
                detail=(
                    "Dokumen tidak memiliki teks "
                    "yang dapat digunakan AI."
                ),
            )

        filename = document_data.get(
            "filename",
            "dokumen.pdf",
        )

        pages = document_data.get(
            "pages",
            0,
        )

        # ----------------------------------------------------
        # Instruksi PDF AI
        # ----------------------------------------------------

        system_instruction = f"""
Kamu adalah PDF Master AI.

Kamu sedang membantu pengguna memahami
dokumen PDF yang mereka upload.

Nama dokumen:
{filename}

Jumlah halaman:
{pages}

Gunakan isi PDF sebagai sumber utama
untuk menjawab pertanyaan pengguna.

ATURAN:

1. Jangan mengarang informasi.
2. Jika jawaban tidak ditemukan dalam PDF,
   katakan bahwa informasi tersebut tidak
   ditemukan dalam dokumen.
3. Prioritaskan isi PDF dibanding pengetahuan
   umum.
4. Jawab dengan bahasa yang sama dengan bahasa
   pengguna.
5. Berikan jawaban yang jelas dan mudah dipahami.
6. Jika pengguna meminta ringkasan, buat
   ringkasan berdasarkan isi PDF.
7. Jika pengguna meminta penjelasan, jelaskan
   berdasarkan isi PDF.
8. Jika memungkinkan, sebutkan halaman sumber.

ISI DOKUMEN PDF
================

{pdf_text}

================
AKHIR DOKUMEN
"""

        # ----------------------------------------------------
        # Conversation memory
        # ----------------------------------------------------

        contents = []

        if isinstance(
            request.conversation,
            list,
        ):

            for item in request.conversation:

                if not isinstance(
                    item,
                    dict,
                ):
                    continue

                role = item.get(
                    "role"
                )

                text = (
                    item.get("content")
                    or item.get("text")
                    or ""
                )

                text = str(
                    text
                ).strip()

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

                elif role in (
                    "assistant",
                    "model",
                ):

                    contents.append({
                        "role": "model",
                        "parts": [
                            {
                                "text": text
                            }
                        ],
                    })

        # ----------------------------------------------------
        # Pertanyaan terbaru
        # ----------------------------------------------------

        contents.append({
            "role": "user",
            "parts": [
                {
                    "text": request.message
                }
            ],
        })

        # ----------------------------------------------------
        # Gemini
        # ----------------------------------------------------

        from app.services.ai_service import (
            client,
            MODEL_NAME,
        )

        response = await client.aio.models.generate_content(
            model=MODEL_NAME,
            contents=contents,
            config={
                "system_instruction":
                    system_instruction,
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

        return PDFChatResponse(
            success=True,
            reply=reply.strip(),
            document_id=request.document_id,
        )

    except HTTPException:
        raise

    except AIServiceError as error:

        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=(
                "Gagal memproses pertanyaan PDF: "
                f"{str(error)}"
            ),
        )