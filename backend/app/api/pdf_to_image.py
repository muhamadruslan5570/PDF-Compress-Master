from app.services.activity_service import record_activity
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse

import fitz
import io
import zipfile
import re


router = APIRouter(
    prefix="/api",
    tags=["PDF to Image"]
)


def parse_pages(pages_text: str, total_pages: int):
    """
    Contoh:
    1
    1,3,5
    1-3
    1,3-5
    all
    """

    pages_text = (pages_text or "all").strip().lower()

    if pages_text == "all":
        return list(range(total_pages))

    selected = set()

    parts = pages_text.split(",")

    for part in parts:
        part = part.strip()

        if not part:
            continue

        # Range: 1-5
        if "-" in part:
            match = re.fullmatch(r"(\d+)\s*-\s*(\d+)", part)

            if not match:
                raise ValueError(
                    f"Format halaman tidak valid: {part}"
                )

            start = int(match.group(1))
            end = int(match.group(2))

            if start > end:
                raise ValueError(
                    f"Rentang halaman tidak valid: {part}"
                )

            for page_number in range(start, end + 1):

                if page_number < 1 or page_number > total_pages:
                    raise ValueError(
                        f"Halaman {page_number} tidak tersedia."
                    )

                selected.add(page_number - 1)

        else:
            # Single page
            if not part.isdigit():
                raise ValueError(
                    f"Nomor halaman tidak valid: {part}"
                )

            page_number = int(part)

            if page_number < 1 or page_number > total_pages:
                raise ValueError(
                    f"Halaman {page_number} tidak tersedia."
                )

            selected.add(page_number - 1)

    if not selected:
        raise ValueError(
            "Tidak ada halaman yang dipilih."
        )

    return sorted(selected)


@router.post("/pdf-to-image")
async def pdf_to_image(
    file: UploadFile = File(...),
    pages: str = Form("all"),
):
    filename = file.filename or ""

    if not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="File harus berupa PDF."
        )

    try:
        pdf_bytes = await file.read()

        if not pdf_bytes:
            raise HTTPException(
                status_code=400,
                detail="File PDF kosong."
            )

        pdf = fitz.open(
            stream=pdf_bytes,
            filetype="pdf"
        )

        total_pages = len(pdf)

        if total_pages == 0:
            pdf.close()

            raise HTTPException(
                status_code=400,
                detail="PDF tidak memiliki halaman."
            )

        try:
            selected_pages = parse_pages(
                pages,
                total_pages
            )

        except ValueError as error:
            pdf.close()

            raise HTTPException(
                status_code=400,
                detail=str(error)
            )

        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(
            zip_buffer,
            mode="w",
            compression=zipfile.ZIP_DEFLATED
        ) as zip_file:

            for page_index in selected_pages:

                page = pdf.load_page(page_index)

                # Rendering kualitas tinggi
                pix = page.get_pixmap(
                    matrix=fitz.Matrix(2, 2),
                    alpha=False
                )

                image_bytes = pix.tobytes("png")

                page_number = page_index + 1

                image_name = (
                    f"page-{page_number}.png"
                )

                zip_file.writestr(
                    image_name,
                    image_bytes
                )

        pdf.close()

        zip_buffer.seek(0)

        record_activity(
            user_id=1,
            activity_type="pdf-to-image",
            title="PDF to Image",
            filename=filename,
            status="success",
            file_size=zip_buffer.getbuffer().nbytes,
            metadata={
                "original_size": len(pdf_bytes),
                "total_pages": total_pages,
                "selected_pages": len(selected_pages),
                "pages": [p + 1 for p in selected_pages]
            }
        )

        if len(selected_pages) == 1:
            page_number = selected_pages[0] + 1

            return StreamingResponse(
                zip_buffer,
                media_type="application/zip",
                headers={
                    "Content-Disposition": (
                        f'attachment; '
                        f'filename="page-{page_number}.zip"'
                    )
                }
            )

        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={
                "Content-Disposition": (
                    'attachment; filename="pdf-images.zip"'
                )
            }
        )

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=(
                f"Gagal mengubah PDF ke gambar: "
                f"{str(error)}"
            )
        )

