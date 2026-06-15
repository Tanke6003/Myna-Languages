"""Conceptos / expresiones: lista personal del usuario y ejercicios para practicarla.

El usuario va guardando expresiones que le gustan (p. ej. 'come up with') y luego practica
con ejercicios generados a partir de SU lista: rellenar el hueco, opción múltiple o escribir
su propia frase (evaluada por la IA).
"""
import random

from fastapi import APIRouter, HTTPException

from services import llm
from backend import db
from backend.routers._shared import fresh
from backend.schemas import (ConceptAddReq, ConceptPracticeReq, ConceptCheckReq,
                             ConceptDeleteReq)

router = APIRouter(tags=["concepts"])

_TYPES = ["gap", "choice", "produce"]


def _state():
    return {"items": db.concept_list(), "count": db.concept_count()}


@router.get("/concepts")
def concepts_list():
    return _state()


@router.post("/concepts/add")
def concepts_add(req: ConceptAddReq):
    phrase = (req.phrase or "").strip()
    if not phrase:
        raise HTTPException(400, "Falta la expresión.")
    try:
        meaning = llm.word_meaning(phrase)
    except Exception:
        meaning = ""
    db.concept_add(phrase, meaning, (req.example or "").strip())
    return _state()


@router.post("/concepts/delete")
def concepts_delete(req: ConceptDeleteReq):
    db.concept_delete(req.id)
    return _state()


@router.post("/concepts/practice")
def concepts_practice(req: ConceptPracticeReq):
    item = db.concept_random()
    if not item:
        return {"empty": True}
    mtype = req.type if req.type in _TYPES else random.choice(_TYPES)
    db.concept_bump(item["id"])  # marca esta expresión como practicada (rota la cobertura)
    base = {"empty": False, "id": item["id"], "phrase": item["phrase"],
            "meaning": item["meaning"], "example": item["example"], "type": mtype}
    # 'gap' y 'choice' generan una frase: la deduplicamos para no repetir (clave por expresión).
    if mtype == "gap":
        ex = fresh(f"concept_gap_{item['id']}", lambda e: e.get("prompt", ""),
                   lambda: llm.concept_gap(item["phrase"], item["meaning"], req.level))
        return {**base, **ex}
    if mtype == "choice":
        ex = fresh(f"concept_choice_{item['id']}", lambda e: e.get("prompt", ""),
                   lambda: llm.concept_choice(item["phrase"], item["meaning"], req.level))
        return {**base, **ex}
    return base  # "produce": el alumno escribe su frase y se evalúa en /concepts/check


@router.post("/concepts/check")
def concepts_check(req: ConceptCheckReq):
    phrase = (req.phrase or "").strip()
    sentence = (req.sentence or "").strip()
    if not phrase or not sentence:
        raise HTTPException(400, "Faltan la expresión o la frase.")
    return llm.concept_check(phrase, sentence)
