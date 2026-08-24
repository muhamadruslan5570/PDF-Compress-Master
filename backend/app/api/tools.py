from app.services.activity_service import record_activity
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse

import io
import os
import shutil
import subprocess
import tempfile
import uuid


router = APIRouter(
    prefix="/api",
    tags=["PDF Tools"],
)


# ============================================================
# CONFIGURATION
# ============================================================

MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB

GHOSTSCRIPT = r"C:\Program Files\gs\gs10.07.1\bin\gswin64c.exe"

DEFAULT_TARGET_KB = 500


# ============================================================
# COMPRESSION STAGES
#
# Semakin ke bawah semakin agresif.
#
# Penting:
# Nilai 70/80/90/100 adalah tingkat agresivitas,
# BUKAN berarti hasil pasti turun 70/80/90/100%.
# ============================================================

PROFILES = {
    "low": [
        (110, 65),
        (95, 55),
        (80, 45),
        (65, 35),
    ],

    "recommended": [
        (100, 60),
        (85, 50),
        (70, 40),
        (55, 30),
    ],

    "extreme": [
        # 70%
        (100, 60),

        # 80%
        (80, 45),

        # 90%
        (60, 30),

        # 100%
        (40, 15),
    ],
}


# ============================================================
# EXTRA EXTREME
#
# Hanya dipakai apabila target belum tercapai.
# Semua percobaan tetap dimulai dari ORIGINAL PDF.
# ============================================================

EXTREME_EXTRA = [
    (35, 12),
    (30, 10),
    (25, 8),
]


# ============================================================
# UTILITY
# ============================================================

def reduction_percent(
    original_size: int,
    new_size: int,
) -> float:

    if original_size <= 0:
        return 0.0

    return (
        (original_size - new_size)
        / original_size
    ) * 100.0


def mb(size: int) -> float:
    return size / 1024 / 1024


def kb(size: int) -> float:
    return size / 1024


# ============================================================
# GHOSTSCRIPT
# ============================================================

def run_ghostscript(
    input_path: str,
    output_path: str,
    dpi: int,
    jpeg_quality: int,
) -> None:

    command = [
        GHOSTSCRIPT,

        "-sDEVICE=pdfwrite",

        "-dCompatibilityLevel=1.4",

        "-dNOPAUSE",
        "-dBATCH",
        "-dSAFER",

        "-dQUIET",

        # ----------------------------------------------------
        # PDF OPTIMIZATION
        # ----------------------------------------------------

        "-dOptimize=true",

        "-dDetectDuplicateImages=true",

        "-dCompressFonts=true",

        "-dSubsetFonts=true",

        # ----------------------------------------------------
        # COLOR IMAGES
        # ----------------------------------------------------

        "-dDownsampleColorImages=true",

        "-dColorImageDownsampleType=/Bicubic",

        f"-dColorImageResolution={dpi}",

        "-dColorImageResolutionThreshold=1.0",

        "-dAutoFilterColorImages=false",

        "-dColorImageFilter=/DCTEncode",

        # ----------------------------------------------------
        # GRAYSCALE
        # ----------------------------------------------------

        "-dDownsampleGrayImages=true",

        "-dGrayImageDownsampleType=/Bicubic",

        f"-dGrayImageResolution={dpi}",

        "-dGrayImageResolutionThreshold=1.0",

        "-dAutoFilterGrayImages=false",

        "-dGrayImageFilter=/DCTEncode",

        # ----------------------------------------------------
        # MONOCHROME
        # ----------------------------------------------------

        "-dDownsampleMonoImages=true",

        "-dMonoImageDownsampleType=/Subsample",

        f"-dMonoImageResolution={max(50, dpi * 2)}",

        # ----------------------------------------------------
        # JPEG
        # ----------------------------------------------------

        f"-dJPEGQ={jpeg_quality}",

        # ----------------------------------------------------
        # OUTPUT
        # ----------------------------------------------------

        f"-sOutputFile={output_path}",

        input_path,
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=180,
    )

    if result.returncode != 0:

        error = (
            result.stderr.strip()
            or result.stdout.strip()
            or "Ghostscript gagal."
        )

        raise RuntimeError(error)


# ============================================================
# CREATE CANDIDATE
# ============================================================

def make_candidate(
    input_path: str,
    temp_dir: str,
    dpi: int,
    jpeg: int,
):
    output_path = os.path.join(
        temp_dir,
        f"candidate_{uuid.uuid4().hex}.pdf",
    )

    run_ghostscript(
        input_path=input_path,
        output_path=output_path,
        dpi=dpi,
        jpeg_quality=jpeg,
    )

    if not os.path.exists(output_path):
        return None, 0

    size = os.path.getsize(output_path)

    if size <= 0:
        return None, 0

    return output_path, size


# ============================================================
# SMART COMPRESSION
# ============================================================

def compress_pdf_smart(
    input_path: str,
    original_size: int,
    target_bytes: int,
    level: str,
    temp_dir: str,
):
    profiles = PROFILES.get(
        level,
        PROFILES["recommended"],
    )

    best_path = None
    best_size = original_size

    attempt = 0

    print("")
    print("=" * 72)
    print("MR PDF COMPRESSOR")
    print("=" * 72)

    print(
        f"Level     : {level}"
    )

    print(
        f"Original  : {mb(original_size):.2f} MB"
    )

    print(
        f"Target    : {kb(target_bytes):.0f} KB"
    )

    print("=" * 72)

    # ========================================================
    # TAHAP UTAMA
    # ========================================================

    for index, (dpi, jpeg) in enumerate(
        profiles,
        start=1,
    ):

        attempt += 1

        try:

            candidate_path, candidate_size = (
                make_candidate(
                    input_path=input_path,
                    temp_dir=temp_dir,
                    dpi=dpi,
                    jpeg=jpeg,
                )
            )

            if not candidate_path:
                continue

            reduction = reduction_percent(
                original_size,
                candidate_size,
            )

            print(
                f"[Attempt {attempt}] "
                f"DPI={dpi} "
                f"JPEG={jpeg} "
                f"Size={mb(candidate_size):.2f} MB "
                f"Reduction={reduction:.2f}%"
            )

            # ------------------------------------------------
            # JANGAN PERNAH MENGAMBIL HASIL LEBIH BESAR
            # DARI ORIGINAL
            # ------------------------------------------------

            if candidate_size >= original_size:

                print(
                    "    -> SKIP: "
                    "hasil lebih besar/sama dengan original."
                )

                os.remove(candidate_path)

                continue

            # ------------------------------------------------
            # SIMPAN HASIL TERKECIL
            # ------------------------------------------------

            if candidate_size < best_size:

                if (
                    best_path
                    and os.path.exists(best_path)
                ):
                    os.remove(best_path)

                best_path = candidate_path
                best_size = candidate_size

                print(
                    "    -> BEST RESULT BARU"
                )

            else:

                os.remove(candidate_path)

            # ------------------------------------------------
            # TARGET
            #
            # Misalnya target 500 KB:
            #
            # 700 KB -> lanjut
            # 600 KB -> lanjut
            # 510 KB -> lanjut
            # 500 KB -> STOP
            # 490 KB -> STOP
            # ------------------------------------------------

            if candidate_size <= target_bytes:

                print("")
                print(
                    "    >>> TARGET TERCAPAI <<<"
                )

                print(
                    f"    Target : "
                    f"{kb(target_bytes):.0f} KB"
                )

                print(
                    f"    Result : "
                    f"{kb(candidate_size):.0f} KB"
                )

                return (
                    best_path,
                    best_size,
                    True,
                )

        except subprocess.TimeoutExpired:

            print(
                f"[Attempt {attempt}] TIMEOUT"
            )

        except Exception as error:

            print(
                f"[Attempt {attempt}] ERROR: "
                f"{str(error)}"
            )

    # ========================================================
    # EXTRA EXTREME
    #
    # Hanya untuk extreme.
    # ========================================================

    if level == "extreme":

        for dpi, jpeg in EXTREME_EXTRA:

            attempt += 1

            try:

                candidate_path, candidate_size = (
                    make_candidate(
                        input_path=input_path,
                        temp_dir=temp_dir,
                        dpi=dpi,
                        jpeg=jpeg,
                    )
                )

                if not candidate_path:
                    continue

                reduction = reduction_percent(
                    original_size,
                    candidate_size,
                )

                print(
                    f"[Attempt {attempt}] "
                    f"DPI={dpi} "
                    f"JPEG={jpeg} "
                    f"Size={mb(candidate_size):.2f} MB "
                    f"Reduction={reduction:.2f}%"
                )

                if candidate_size >= original_size:

                    print(
                        "    -> SKIP: "
                        "hasil lebih besar/sama "
                        "dengan original."
                    )

                    os.remove(candidate_path)

                    continue

                if candidate_size < best_size:

                    if (
                        best_path
                        and os.path.exists(best_path)
                    ):
                        os.remove(best_path)

                    best_path = candidate_path
                    best_size = candidate_size

                    print(
                        "    -> BEST RESULT BARU"
                    )

                else:

                    os.remove(candidate_path)

                if candidate_size <= target_bytes:

                    print("")
                    print(
                        "    >>> TARGET TERCAPAI <<<"
                    )

                    return (
                        best_path,
                        best_size,
                        True,
                    )

            except subprocess.TimeoutExpired:

                print(
                    f"[Attempt {attempt}] TIMEOUT"
                )

            except Exception as error:

                print(
                    f"[Attempt {attempt}] ERROR: "
                    f"{str(error)}"
                )

    # ========================================================
    # TARGET TIDAK TERCAPAI
    # ========================================================

    print("")
    print("=" * 72)
    print("BEST RESULT")
    print("=" * 72)

    print(
        f"Original   : "
        f"{mb(original_size):.2f} MB"
    )

    print(
        f"Compressed : "
        f"{mb(best_size):.2f} MB"
    )

    print(
        f"Reduction  : "
        f"{reduction_percent(original_size, best_size):.2f}%"
    )

    print(
        f"Target     : "
        f"{kb(target_bytes):.0f} KB"
    )

    print(
        "STATUS     : Target belum tercapai."
    )

    print("=" * 72)

    return (
        best_path,
        best_size,
        False,
    )


# ============================================================
# API ENDPOINT
# ============================================================

@router.post("/compress-pdf")
async def compress_pdf(
    file: UploadFile = File(...),
    level: str = Form("recommended"),
    target_kb: int = Form(DEFAULT_TARGET_KB),
):

    # ========================================================
    # FILE VALIDATION
    # ========================================================

    if not file.filename:

        raise HTTPException(
            status_code=400,
            detail="Nama file tidak ditemukan.",
        )

    if not file.filename.lower().endswith(".pdf"):

        raise HTTPException(
            status_code=400,
            detail="File harus berformat PDF.",
        )

    # ========================================================
    # LEVEL VALIDATION
    # ========================================================

    if level not in (
        "low",
        "recommended",
        "extreme",
    ):

        level = "recommended"

    # ========================================================
    # TARGET VALIDATION
    # ========================================================

    try:
        target_kb = int(target_kb)
    except (TypeError, ValueError):

        target_kb = DEFAULT_TARGET_KB

    if target_kb < 50:
        target_kb = 50

    # ========================================================
    # GHOSTSCRIPT CHECK
    # ========================================================

    if not os.path.exists(GHOSTSCRIPT):

        raise HTTPException(
            status_code=500,
            detail=(
                "Ghostscript tidak ditemukan di: "
                f"{GHOSTSCRIPT}"
            ),
        )

    # ========================================================
    # READ FILE
    # ========================================================

    contents = await file.read()

    original_size = len(contents)

    if original_size <= 0:

        raise HTTPException(
            status_code=400,
            detail="File PDF kosong.",
        )

    if original_size > MAX_FILE_SIZE:

        raise HTTPException(
            status_code=400,
            detail="Ukuran file maksimal 20 MB.",
        )

    # ========================================================
    # TARGET
    # ========================================================

    target_bytes = target_kb * 1024

    # ========================================================
    # FILE SUDAH LEBIH KECIL DARI TARGET
    # ========================================================

    if original_size <= target_bytes:

        print("")
        print(
            "[INFO] File original sudah "
            "lebih kecil dari target."
        )

        record_activity(
            user_id=1,
            activity_type="compress-pdf",
            title="Compress PDF",
            filename=file.filename,
            status="success",
            file_size=original_size,
            metadata={
                "original_size": original_size,
                "compressed_size": original_size,
                "reduction": 0.0,
                "compression_level": level,
                "target_kb": target_kb,
                "target_reached": True,
            },
        )

        return StreamingResponse(
            io.BytesIO(contents),

            media_type="application/pdf",

            headers={
                "Content-Disposition": (
                    f'attachment; '
                    f'filename="compressed_'
                    f'{file.filename}"'
                ),

                "Access-Control-Expose-Headers": (
                    "X-Original-Size, "
                    "X-Compressed-Size, "
                    "X-Compression-Reduction, "
                    "X-Compression-Level, "
                    "X-Target-KB, "
                    "X-Target-Reached"
                ),

                "X-Original-Size": str(
                    original_size
                ),

                "X-Compressed-Size": str(
                    original_size
                ),

                "X-Compression-Reduction": "0.00",

                "X-Compression-Level": level,

                "X-Target-KB": str(
                    target_kb
                ),

                "X-Target-Reached": "true",
            },
        )

    # ========================================================
    # TEMP
    # ========================================================

    temp_dir = tempfile.mkdtemp(
        prefix="mr_pdf_"
    )

    input_path = os.path.join(
        temp_dir,
        "original.pdf",
    )

    try:

        with open(
            input_path,
            "wb",
        ) as f:

            f.write(contents)

        # ====================================================
        # COMPRESS
        # ====================================================

        (
            best_path,
            best_size,
            target_reached,
        ) = compress_pdf_smart(
            input_path=input_path,
            original_size=original_size,
            target_bytes=target_bytes,
            level=level,
            temp_dir=temp_dir,
        )

        # ====================================================
        # TIDAK ADA HASIL LEBIH KECIL
        # ====================================================

        if (
            not best_path
            or not os.path.exists(best_path)
            or best_size >= original_size
        ):

            final_bytes = contents
            final_size = original_size
            reduction = 0.0
            target_reached = False

        else:

            with open(
                best_path,
                "rb",
            ) as f:

                final_bytes = f.read()

            final_size = len(
                final_bytes
            )

            # Safety check

            if final_size >= original_size:

                final_bytes = contents
                final_size = original_size
                reduction = 0.0
                target_reached = False

            else:

                reduction = reduction_percent(
                    original_size,
                    final_size,
                )

                target_reached = (
                    final_size <= target_bytes
                )

        # ====================================================
        # FINAL LOG
        # ====================================================

        print("")
        print("=" * 72)
        print("FINAL RESULT")
        print("=" * 72)

        print(
            f"Original   : "
            f"{mb(original_size):.2f} MB"
        )

        print(
            f"Target     : "
            f"{target_kb} KB"
        )

        print(
            f"Compressed : "
            f"{mb(final_size):.2f} MB"
        )

        print(
            f"Reduction  : "
            f"{reduction:.2f}%"
        )

        print(
            "Target     : "
            + (
                "TERCAPAI"
                if target_reached
                else "BELUM TERCAPAI"
            )
        )

        print("=" * 72)

        # ====================================================
        # RECORD HISTORY
        # ====================================================

        record_activity(
            user_id=1,
            activity_type="compress-pdf",
            title="Compress PDF",
            filename=file.filename,
            status="success",
            file_size=final_size,
            metadata={
                "original_size": original_size,
                "compressed_size": final_size,
                "reduction": round(reduction, 2),
                "compression_level": level,
                "target_kb": target_kb,
                "target_reached": target_reached,
            },
        )

        # ====================================================
        # RESPONSE
        # ====================================================

        return StreamingResponse(
            io.BytesIO(final_bytes),

            media_type="application/pdf",

            headers={
                "Content-Disposition": (
                    f'attachment; '
                    f'filename="compressed_'
                    f'{file.filename}"'
                ),

                "Access-Control-Expose-Headers": (
                    "X-Original-Size, "
                    "X-Compressed-Size, "
                    "X-Compression-Reduction, "
                    "X-Compression-Level, "
                    "X-Target-KB, "
                    "X-Target-Reached"
                ),

                "X-Original-Size": str(
                    original_size
                ),

                "X-Compressed-Size": str(
                    final_size
                ),

                "X-Compression-Reduction": (
                    f"{reduction:.2f}"
                ),

                "X-Compression-Level": level,

                "X-Target-KB": str(
                    target_kb
                ),

                "X-Target-Reached": (
                    "true"
                    if target_reached
                    else "false"
                ),
            },
        )

    except HTTPException:
        raise

    except Exception as error:

        # Pastikan FastAPI mengirim detail
        # sebagai STRING, bukan object.

        raise HTTPException(
            status_code=500,
            detail=str(error),
        )

    finally:

        shutil.rmtree(
            temp_dir,
            ignore_errors=True,
        )


