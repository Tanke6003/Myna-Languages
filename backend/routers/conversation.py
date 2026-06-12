"""Conversación con el tutor (incluye streaming SSE token a token)."""
import json
import os
import string

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from services import stt, llm
from backend import db
from backend.constants import SCENARIOS, LOW_CONF
from backend.schemas import ConversationTextReq
from backend.routers._shared import save_temp

router = APIRouter(tags=["conversation"])


def _scenario_instruction(scenario, detail):
    """Combina el escenario con un detalle libre del usuario (puesto, sitio, lugar...)."""
    scen = SCENARIOS.get(scenario, "")
    detail = (detail or "").strip()
    if detail:
        scen = (scen + " " if scen else "") + f"Specific context to use in the role-play: {detail}."
    return scen


def _low_conf_words(words):
    low, seen = [], set()
    for w in words:
        token = w["word"].strip(string.punctuation + "¿¡").lower()
        if len(token) > 2 and w["prob"] < LOW_CONF and token not in seen:
            seen.add(token)
            low.append(token)
    return low[:5]


@router.post("/conversation/start")
def conversation_start(level: str = Form(...), scenario: str = Form(""), detail: str = Form("")):
    return {"reply": llm.opening_question(level, _scenario_instruction(scenario, detail))}


@router.post("/conversation/turn")
def conversation_turn(
    level: str = Form(...),
    scenario: str = Form(""),
    detail: str = Form(""),
    history: str = Form("[]"),
    audio: UploadFile = File(...),
):
    hist = json.loads(history or "[]")
    path = save_temp(audio)
    try:
        result = stt.transcribe(path, word_timestamps=True)
    finally:
        os.remove(path)

    user_text = result["text"]
    if not user_text:
        raise HTTPException(422, "No te entendí. Inténtalo otra vez.")

    scen = _scenario_instruction(scenario, detail)
    data = llm.conversation_turn(hist, user_text, level, scen)
    pron_words = _low_conf_words(result["words"])
    db.bump_missed(pron_words)  # la actividad/puntuación la registra el cliente (award) con SCORE
    return {
        "user_text": user_text,
        "reply": data["reply"],
        "corrections": data["corrections"],
        "vocab_tip": data["vocab_tip"],
        "pron_words": pron_words,
        "score": data["score"],
    }


@router.post("/conversation/turn_stream")
def conversation_turn_stream(
    level: str = Form(...),
    scenario: str = Form(""),
    detail: str = Form(""),
    history: str = Form("[]"),
    audio: UploadFile = File(...),
):
    """Igual que /turn pero emite la respuesta en streaming (SSE)."""
    hist = json.loads(history or "[]")
    path = save_temp(audio)
    try:
        result = stt.transcribe(path, word_timestamps=True)
    finally:
        os.remove(path)
    user_text = result["text"]
    scen = _scenario_instruction(scenario, detail)
    pron_words = _low_conf_words(result["words"])

    def event(d):
        return "data: " + json.dumps(d, ensure_ascii=False) + "\n\n"

    def gen():
        if not user_text:
            yield event({"type": "error", "message": "No te entendí. Inténtalo otra vez."})
            return
        yield event({"type": "user", "text": user_text})
        raw, last = "", ""
        try:
            for tok in llm.conversation_turn_stream(hist, user_text, level, scen):
                raw += tok
                partial = llm.partial_reply(raw)
                if partial and partial != last:
                    last = partial
                    yield event({"type": "partial", "reply": partial})
            db.bump_missed(pron_words)  # las palabras flojas no necesitan el parse
            # El parseo va DENTRO del try: si falla, el cliente recibe 'error' y no se cuelga.
            # La actividad/puntuación la registra el cliente (award) con el SCORE del parse.
            data = llm.parse_conversation_raw(raw)
            yield event({"type": "done", "reply": data["reply"], "corrections": data["corrections"],
                         "vocab_tip": data["vocab_tip"], "pron_words": pron_words,
                         "score": data["score"]})
        except Exception as e:  # noqa: BLE001
            yield event({"type": "error", "message": str(e)})

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.post("/conversation/turn_text")
def conversation_turn_text(req: ConversationTextReq):
    """Reenvía un turno con el texto corregido por el usuario (sin audio)."""
    scen = _scenario_instruction(req.scenario, req.detail)
    data = llm.conversation_turn(req.history, req.user_text, req.level, scen)
    return {
        "user_text": req.user_text,
        "reply": data["reply"],
        "corrections": data["corrections"],
        "vocab_tip": data["vocab_tip"],
        "pron_words": [],
        "score": data["score"],
    }
