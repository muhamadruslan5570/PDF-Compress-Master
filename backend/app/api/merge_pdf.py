from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from app.services.activity_service import record_activity
from pypdf import PdfReader, PdfWriter

import io
import os
import shutil
import tempfile


router = APIRouter(
    prefix="/api",
    tags=["Merge PDF"],
)


MAX_FILE_SIZE = 20 * 1024 * 1024
MAX_FILES = 20


@router.post("/merge-pdf")
async def merge_pdf(
    files: list[UploadFile] = File(...)
):
    """
    Menggabungkan beberapa file PDF menjadi satu PDF.
    """

    if not files:
        raise HTTPException(
            status_code=400,
            detail="Minimal upload 2 file PDF."
        )

    if len(files) < 2:
        raise HTTPException(
            status_code=400,
            detail="Minimal upload 2 file PDF."
        )

    if len(files) > MAX_FILES:
        raise HTTPException(
            status_code=400,
            detail=f"Maksimal {MAX_FILES} file PDF."
        )

    temp_dir = tempfile.mkdtemp(
        prefix="mr_merge_pdf_"
    )

    output_path = os.path.join(
        temp_dir,
        "merged.pdf"
    )

    try:
        writer = PdfWriter()

        total_size = 0

        for index, file in enumerate(files):

            if not file.filename:
                raise HTTPException(
                    status_code=400,
                    detail=f"File ke-{index + 1} tidak memiliki nama."
                )

            if not file.filename.lower().endswith(".pdf"):
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"File '{file.filename}' "
                        "bukan PDF."
                    )
                )

            data = await file.read()

            if not data:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"File '{file.filename}' kosong."
                    )
                )

            if len(data) > MAX_FILE_SIZE:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"File '{file.filename}' "
                        "melebihi batas 20 MB."
                    )
                )

            total_size += len(data)

            if total_size > MAX_FILE_SIZE * MAX_FILES:
                raise HTTPException(
                    status_code=400,
                    detail="Total ukuran file terlalu besar."
                )

            input_path = os.path.join(
                temp_dir,
                f"input_{index}.pdf"
            )

            with open(
                input_path,
                "wb"
            ) as f:
                f.write(data)

            try:
                reader = PdfReader(
                    input_path
                )

                if reader.is_encrypted:

                    try:
                        reader.decrypt("")
                    except Exception:
                        raise HTTPException(
                            status_code=400,
                            detail=(
                                f"PDF '{file.filename}' "
                                "terkunci password."
                            )
                        )

                if not reader.pages:
                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"PDF '{file.filename}' "
                            "tidak memiliki halaman."
                        )
                    )

                for page in reader.pages:
                    writer.add_page(page)

            except HTTPException:
                raise

            except Exception as error:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"PDF '{file.filename}' "
                        f"tidak dapat dibaca: {error}"
                    )
                )

        # Metadata hasil.
        writer.add_metadata({
            "/Title": "Merged PDF",
            "/Producer": "MR PDF Compressor",
        })

        with open(
            output_path,
            "wb"
        ) as output_file:

            writer.write(
                output_file
            )

        if not os.path.exists(
            output_path
        ):
            raise RuntimeError(
                "File hasil merge gagal dibuat."
            )

        with open(
            output_path,
            "rb"
        ) as f:
            merged_data = f.read()

        if not merged_data:
            raise RuntimeError(
                "File hasil merge kosong."
            )

        record_activity(
            user_id=1,
            activity_type="merge-pdf",
            title="Merge PDF",
            filename="merged.pdf",
            status="success",
            file_size=len(merged_data),
            metadata={
                "source_files": [
                    file.filename for file in files
                ],
                "file_count": len(files),
                "original_total_size": total_size,
                "merged_size": len(merged_data),
            },
        )

        return StreamingResponse(
            io.BytesIO(merged_data),
            media_type="application/pdf",
            headers={
                "Content-Disposition": (
                    'attachment; '
                    'filename="merged.pdf"'
                ),
                "Access-Control-Expose-Headers": (
                    "X-Original-Files, "
                    "X-Merged-Size"
                ),
                "X-Original-Files": str(
                    len(files)
                ),
                "X-Merged-Size": str(
                    len(merged_data)
                ),
            },
        )

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=(
                f"Gagal menggabungkan PDF: "
                f"{str(error)}"
            )
        )

    finally:
        shutil.rmtree(
            temp_dir,
            ignore_errors=True
        )

