"""Flashcards con repetición espaciada (SM-2)."""
from fastapi import APIRouter, Body, HTTPException

from services import llm
from backend import db

router = APIRouter(tags=["flashcards"])


@router.get("/flashcards")
def flashcards():
    return {**db.fc_counts(), "card": db.fc_next()}


@router.post("/flashcards/add")
def flashcards_add(body: dict = Body(...)):
    front = (body.get("front") or "").strip()
    if not front:
        raise HTTPException(400, "Falta la palabra.")
    try:
        back = llm.word_meaning(front)
    except Exception:
        back = ""
    db.fc_add(front, back)
    return {**db.fc_counts(), "card": db.fc_next()}


@router.post("/flashcards/review")
def flashcards_review(body: dict = Body(...)):
    cid = body.get("id")
    if cid is None:
        raise HTTPException(400, "Falta el id.")
    db.fc_review(int(cid), (body.get("grade") or "good"))
    return {**db.fc_counts(), "card": db.fc_next()}


@router.post("/flashcards/seed")
def flashcards_seed():
    existing = db.fc_existing_fronts()
    added = 0
    for m in db.get_progress()["missed"]:
        w = m["word"]
        if w.lower() in existing:
            continue
        try:
            back = llm.word_meaning(w)
        except Exception:
            back = ""
        db.fc_add(w, back)
        added += 1
        if added >= 20:
            break
    return {"added": added, **db.fc_counts(), "card": db.fc_next()}
