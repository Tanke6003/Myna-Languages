"""Ejercicios de práctica: lectura, corregir texto, vocabulario, comprensión y repaso mixto."""
import os
import random

from fastapi import APIRouter, Body, File, Form, UploadFile

from services import stt, llm
from services import pronunciation as pron
from backend import db
from backend.schemas import LevelTopic, LevelReq, VocabReq, TextCheckReq
from backend.routers._shared import save_temp

router = APIRouter(tags=["exercises"])


# --- Lectura / pronunciación ---
@router.post("/reading/sentence")
def reading_sentence(req: LevelTopic):
    sentence = llm.reading_sentence(req.level, req.topic)
    return {"sentence": sentence, "ipa": pron.transcribe_ipa(sentence)}


@router.post("/reading/evaluate")
def reading_evaluate(level: str = Form(...), sentence: str = Form(...), audio: UploadFile = File(...)):
    path = save_temp(audio)
    try:
        rep = pron.assess_reading(sentence, path)
    finally:
        os.remove(path)
    try:
        rep["feedback"] = llm.reading_feedback(
            rep["reference"], rep["heard"], rep["problems"], rep["score"], level)
    except Exception:
        rep["feedback"] = ""
    return rep


# --- Corregir texto ---
@router.post("/text/new")
def text_new(req: LevelReq):
    return {"sentence": llm.text_with_errors(req.level)}


@router.post("/text/check")
def text_check(req: TextCheckReq):
    return llm.check_correction(req.original, req.correction)


# --- Vocabulario ---
@router.post("/vocab/new")
def vocab_new(req: VocabReq):
    return llm.vocab_exercise(req.level, req.kind)


# --- Comprensión auditiva ---
@router.post("/listening/new")
def listening_new(req: LevelReq):
    return llm.listening_exercise(req.level)


# --- Repaso mixto (con tus palabras más falladas) ---
@router.get("/mixed/next")
def mixed_next():
    words = db.missed_top(20)
    if not words:
        return {"empty": True}
    word = random.choice(words)["word"]
    mtype = random.choice(["meaning", "listen", "meaning"])  # más peso a 'meaning'
    if mtype == "listen":
        return {"empty": False, "word": word, "type": "listen", "remaining": len(words)}
    ex = llm.meaning_exercise(word)
    return {"empty": False, "word": word, "type": "meaning", "remaining": len(words), **ex}


@router.post("/mixed/result")
def mixed_result(body: dict = Body(...)):
    word = (body.get("word") or "").strip()
    if word and bool(body.get("correct")):
        db.missed_decrement(word)
    return {"ok": True}
