from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
import os

from app.api.auth import router as auth_router
from app.api.tools import router as tools_router
from app.api.pdf_to_word import router as pdf_to_word_router
from app.api.merge_pdf import router as merge_pdf_router
from app.api.word_to_pdf import router as word_to_pdf_router
from app.api.pdf_to_image import router as pdf_to_image_router
from app.api.profile import router as profile_router
from app.api.history import router as history_router
from app.api.ai import router as ai_router

app = FastAPI(
    title="MR Compress PDF API",
    version="1.0.0"
)

app.mount("/storage", StaticFiles(directory="storage"), name="storage")

app.include_router(auth_router)
app.include_router(tools_router)
app.include_router(pdf_to_word_router)
app.include_router(merge_pdf_router)
app.include_router(word_to_pdf_router)
app.include_router(pdf_to_image_router)
app.include_router(profile_router)
app.include_router(history_router)
app.include_router(ai_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "http://127.0.0.1:8000",
        "http://localhost:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Session diperlukan oleh Authlib OAuth
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv(
        "SESSION_SECRET",
        "mr-compress-pdf-local-session-secret-change-later"
    ),
    same_site="lax",
    https_only=False,
)

@app.get("/")
def root():
    return {
        "status": "online",
        "service": "MR Compress PDF API"
    }



















