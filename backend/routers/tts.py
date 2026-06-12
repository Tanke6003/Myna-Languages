"""Texto a voz (servido como audio, con caché por hash en services/tts.py)."""
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from services import tts as tts_service

router = APIRouter(tags=["tts"])


@router.get("/tts")
def tts_endpoint(text: str, lang: str = "", slow: bool = False):
    path = tts_service.synthesize(text, lang=(lang or None), slow=slow)
    if not path:
        raise HTTPException(503, "Audio no disponible (¿sin internet para edge-tts?).")
    media = "audio/wav" if path.endswith(".wav") else "audio/mpeg"
    return FileResponse(path, media_type=media)
