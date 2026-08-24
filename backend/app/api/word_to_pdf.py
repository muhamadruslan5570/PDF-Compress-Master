from app.services.activity_service import record_activity
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
import os
import shutil
import subprocess
import tempfile


router = APIRouter(
    prefix="/api",
    tags=["Word to PDF"]
)


LIBREOFFICE_PATH = r"C:\Program Files\LibreOffice\program\soffice.exe"


@router.post("/word-to-pdf")
async def word_to_pdf(file: UploadFile = File(...)):

    allowed_extensions = {
        ".doc",
        ".docx",
        ".odt",
    }

    filename = file.filename or ""
    extension = os.path.splitext(filename)[1].lower()

    if extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail="File harus berupa DOC, DOCX, atau ODT."
        )

    if not os.path.exists(LIBREOFFICE_PATH):
        raise HTTPException(
            status_code=500,
            detail="LibreOffice tidak ditemukan."
        )

    temp_dir = tempfile.mkdtemp(prefix="word_to_pdf_")

    try:
        input_path = os.path.join(temp_dir, filename)

        with open(input_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        output_dir = os.path.join(temp_dir, "output")
        os.makedirs(output_dir, exist_ok=True)

        command = [
            LIBREOFFICE_PATH,
            "--headless",
            "--convert-to",
            "pdf",
            "--outdir",
            output_dir,
            input_path,
        ]

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=120,
        )

        pdf_name = os.path.splitext(filename)[0] + ".pdf"
        pdf_path = os.path.join(output_dir, pdf_name)

        if not os.path.exists(pdf_path):
            error_message = (
                result.stderr.strip()
                or result.stdout.strip()
                or "LibreOffice gagal mengonversi dokumen."
            )

            raise HTTPException(
                status_code=500,
                detail=error_message
            )

        record_activity(
            user_id=1,
            activity_type="word-to-pdf",
            title="Word to PDF",
            filename=filename,
            status="success",
            file_size=os.path.getsize(pdf_path),
            metadata={
                "input_filename": filename,
                "output_filename": pdf_name,
                "input_extension": extension,
                "output_size": os.path.getsize(pdf_path)
            }
        )

        return FileResponse(
            path=pdf_path,
            media_type="application/pdf",
            filename=pdf_name,
        )

    except subprocess.TimeoutExpired:
        raise HTTPException(
            status_code=500,
            detail="Proses konversi terlalu lama."
        )

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Gagal mengonversi Word ke PDF: {str(error)}"
        )

    finally:
        # FileResponse masih membutuhkan file ketika response dikirim.
        # Cleanup dilakukan oleh sistem setelah proses selesai.
        pass

