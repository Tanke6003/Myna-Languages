"""Meta, gamificación, progreso/historial y sugerencia de subir de nivel."""
from fastapi import APIRouter, Body

import config
from backend import db
from backend.constants import SCENARIOS
from backend.schemas import AwardReq

router = APIRouter(tags=["progress"])

_CEFR_ORDER = ["A1", "A2", "B1", "B2", "C1", "C2"]
_LEVELUP_NEED = 12  # ejercicios mínimos en el nivel


@router.get("/meta")
def meta():
    return {
        "levels": config.LEVELS,
        "default_level": config.DEFAULT_LEVEL,
        "scenarios": list(SCENARIOS.keys()),
    }


@router.get("/stats")
def get_stats():
    return db.get_stats()


@router.post("/stats/award")
def award(req: AwardReq):
    stats = db.award(req.points, req.correct)
    if req.kind:
        db.log_activity(req.kind, req.level or None, req.score, req.correct)
    if req.words:
        db.bump_missed(req.words)
    return stats


@router.post("/stats/reset")
def reset_stats():
    return db.reset_stats()


@router.get("/progress")
def progress():
    return db.get_progress()


@router.get("/progress/export")
def progress_export():
    return db.export_all()


@router.post("/progress/import")
def progress_import(data: dict = Body(...)):
    return db.import_all(data)


def _levelup_data(level):
    st = db.level_stats(level)
    nxt = None
    if level in _CEFR_ORDER:
        i = _CEFR_ORDER.index(level)
        if i < len(_CEFR_ORDER) - 1:
            nxt = _CEFR_ORDER[i + 1]
    ready = bool(nxt) and st["count"] >= _LEVELUP_NEED and (st["avg_score"] or 0) >= 85
    return {"level": level, "next_level": nxt, "ready": ready, "need": _LEVELUP_NEED,
            "count": st["count"], "avg_score": st["avg_score"]}


@router.get("/levelup")
def levelup(level: str):
    return _levelup_data(level)


@router.get("/home")
def home(level: str):
    prog = db.get_progress()
    fc = db.fc_counts()
    return {
        "missed": prog["missed"][:6],
        "missed_count": db.missed_count(),
        "total_activity": prog["total_count"],
        "flashcards_due": fc["due"],
        "flashcards_total": fc["total"],
        "levelup": _levelup_data(level),
    }
