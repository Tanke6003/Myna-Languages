"""Ejercicios de práctica: lectura, corregir texto, vocabulario, comprensión y repaso mixto."""
import os
import random

from fastapi import APIRouter, Body, File, Form, UploadFile

from services import stt, llm
from services import pronunciation as pron
from backend import db
from backend.schemas import LevelTopic, LevelReq, VocabReq, TextCheckReq, WritingNewReq, WritingCheckReq
from backend.routers._shared import save_temp, fresh

router = APIRouter(tags=["exercises"])


# --- Lectura / pronunciación ---
@router.post("/reading/sentence")
def reading_sentence(req: LevelTopic):
    # 'reading' lo comparten Pronunciación, Shadowing y Dictado: una frase ya vista no se repite.
    sentence = fresh("reading", lambda s: s, lambda: llm.reading_sentence(req.level, req.topic))
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
    return {"sentence": fresh("text", lambda s: s, lambda: llm.text_with_errors(req.level))}


@router.post("/text/check")
def text_check(req: TextCheckReq):
    return llm.check_correction(req.original, req.correction)


# --- Escritura (reescribir / traducir / completar / redacción) ---
@router.post("/writing/new")
def writing_new(req: WritingNewReq):
    avoid = db.seen_recent(f"writing_{req.kind}", 20)
    return fresh(f"writing_{req.kind}", lambda e: e.get("prompt", ""),
                 lambda: llm.writing_exercise(req.level, req.kind, avoid=avoid), attempts=6)


@router.post("/writing/check")
def writing_check(req: WritingCheckReq):
    return llm.writing_check(req.kind, req.prompt, req.instruction, req.answer, req.level)


# --- Vocabulario ---
@router.post("/vocab/new")
def vocab_new(req: VocabReq):
    kind = f"vocab_{req.kind}"
    avoid = db.seen_recent(kind, 20)  # últimas palabras/frases objetivo, para que el modelo varíe
    return fresh(kind, lambda e: e.get("prompt", ""),
                 lambda: llm.vocab_exercise(req.level, req.kind, avoid=avoid), attempts=6)


# --- Comprensión auditiva ---
@router.post("/listening/new")
def listening_new(req: LevelReq):
    return fresh("listening", lambda e: e.get("passage", ""),
                 lambda: llm.listening_exercise(req.level))


# --- Sonidos parecidos (pares mínimos) ---
@router.post("/minimal/new")
def minimal_new(req: LevelReq):
    avoid = db.seen_recent("minimal", 20)
    ex = fresh("minimal", lambda e: e.get("answer", ""),
               lambda: llm.minimal_pairs_exercise(req.level, avoid=avoid), attempts=6)
    # IPA por opción (CMUdict local) para mostrar el contraste tras responder.
    ex["ipa"] = {o: (pron.phonemes(o) or {}).get("ipa", "") for o in ex.get("options", [])}
    return ex


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
