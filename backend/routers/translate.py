"""Traductor: traducción ES↔EN + sinónimos y ejemplos."""
from fastapi import APIRouter

from services import llm
from backend.schemas import TranslateReq, DetailsReq

router = APIRouter(tags=["translate"])


@router.post("/translate")
def translate(req: TranslateReq):
    return {"translation": llm.translate(req.text, req.direction, req.note)}


@router.post("/translate/details")
def translate_details(req: DetailsReq):
    return llm.translation_details(req.text)
