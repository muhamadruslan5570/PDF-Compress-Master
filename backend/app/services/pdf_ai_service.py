"""
PDF AI service for PDF-Compress-Master.

Membaca PDF menggunakan:
1. pypdf untuk PDF yang memiliki text layer.
2. PyMuPDF + Tesseract OCR untuk PDF scan/gambar.
"""

from io import BytesIO
from typing import Optional

import pymupdf
import pytesseract
from PIL import Image
from pypdf import PdfReader


class PDFAIServiceError(Exception):
    """Error khusus untuk PDF AI service."""
    pass


# ============================================================
# KONFIGURASI OCR
# ============================================================

OCR_DPI = 150

# Bahasa OCR.
# "ind" = Bahasa Indonesia
# "eng" = Bahasa Inggris
OCR_LANGUAGE = "ind+eng"


# ============================================================
# EXTRACT TEXT DENGAN PYPDF
# ============================================================

def extract_text_with_pypdf(
    pdf_bytes: bytes,
) -> dict:
    """
    Membaca text layer dari PDF menggunakan pypdf.
    """

    reader = PdfReader(
        BytesIO(pdf_bytes)
    )

    pages = len(reader.pages)
    pages_text = []

    for page_number, page in enumerate(
        reader.pages,
        start=1,
    ):
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""

        text = text.strip()

        if text:
            pages_text.append(
                f"[Halaman {page_number}]\n{text}"
            )

    full_text = "\n\n".join(
        pages_text
    ).strip()

    return {
        "pages": pages,
        "text": full_text,
    }


# ============================================================
# OCR SATU HALAMAN
# ============================================================

def ocr_page(
    page,
) -> str:
    """
    Mengubah satu halaman PDF menjadi gambar
    lalu menjalankan Tesseract OCR.
    """

    matrix = pymupdf.Matrix(
        OCR_DPI / 72,
        OCR_DPI / 72,
    )

    pixmap = page.get_pixmap(
        matrix=matrix,
        alpha=False,
    )

    image = Image.frombytes(
        "RGB",
        [pixmap.width, pixmap.height],
        pixmap.samples,
    )

    text = pytesseract.image_to_string(
        image,
        lang=OCR_LANGUAGE,
    )

    return text.strip()


# ============================================================
# EXTRACT TEXT DENGAN OCR
# ============================================================

def extract_text_with_ocr(
    pdf_bytes: bytes,
) -> dict:
    """
    Membaca PDF scan menggunakan OCR.
    """

    document = pymupdf.open(
        stream=pdf_bytes,
        filetype="pdf",
    )

    pages = len(document)
    pages_text = []

    try:
        for page_number, page in enumerate(
            document,
            start=1,
        ):
            text = ocr_page(page)

            if text:
                pages_text.append(
                    f"[Halaman {page_number}]\n{text}"
                )

    finally:
        document.close()

    full_text = "\n\n".join(
        pages_text
    ).strip()

    return {
        "pages": pages,
        "text": full_text,
    }


# ============================================================
# FUNGSI UTAMA
# ============================================================

def extract_pdf_text(
    pdf_bytes: bytes,
    use_ocr: bool = True,
) -> dict:
    """
    Membaca teks dari PDF.

    Alur:

    PDF
      ↓
    pypdf
      ↓
    Ada teks?
      ├── Ya  → gunakan teks
      └── Tidak → OCR
    """

    if not pdf_bytes:
        raise PDFAIServiceError(
            "File PDF kosong."
        )

    try:

        # ----------------------------------------------------
        # 1. Coba text layer terlebih dahulu
        # ----------------------------------------------------

        result = extract_text_with_pypdf(
            pdf_bytes
        )

        if result["text"]:
            return {
                "pages": result["pages"],
                "text": result["text"],
                "method": "pypdf",
            }

        # ----------------------------------------------------
        # 2. Kalau tidak ada teks → OCR
        # ----------------------------------------------------

        if not use_ocr:
            raise PDFAIServiceError(
                "Tidak ditemukan teks yang dapat dibaca "
                "di dalam PDF."
            )

        result = extract_text_with_ocr(
            pdf_bytes
        )

        if not result["text"]:
            raise PDFAIServiceError(
                "OCR tidak menemukan teks "
                "di dalam PDF."
            )

        return {
            "pages": result["pages"],
            "text": result["text"],
            "method": "ocr",
        }

    except PDFAIServiceError:
        raise

    except Exception as error:
        raise PDFAIServiceError(
            f"Gagal membaca PDF: {str(error)}"
        )