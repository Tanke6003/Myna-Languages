"""Meta, gamificación, progreso/historial y sugerencia de subir de nivel."""
from fastapi import APIRouter, Body

import config
from backend import db
from backend.constants import SCENARIOS
from backend.schemas import AwardReq

router = APIRouter(tags=["progress"])

_CEFR_ORDER = ["A1", "A2", "B1", "B2", "C1", "C2"]
_LEVELUP_NEED = 12  # ejercicios mínimos en el nivel (techo de calidad global)

# Áreas de destreza (CEFR): para subir de nivel hay que practicar TODAS, no solo una.
# Evita que se suba de nivel haciendo, p. ej., solo "Corregir texto". Cada área agrupa varios
# módulos (kind) y exige un mínimo de práctica y una media decente.
_SKILL_AREAS = {
    "speak":  ("conversation", "reading", "shadowing"),
    "listen": ("listening", "dictation"),
    "write":  ("text",),
    "vocab":  ("vocab",),
}
_AREA_NEED = 3      # ejercicios mínimos por área
_AREA_FLOOR = 80    # media mínima por área


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


def _area_breakdown(level):
    """Cobertura por área de destreza en un nivel: lista de áreas (con media y si cumplen) y un
    booleano de si TODAS cumplen el mínimo (reps + media). Cada área agrupa varios 'kind'."""
    ks = db.level_kind_stats(level)
    areas, areas_ok = [], True
    for area, kinds in _SKILL_AREAS.items():
        count = sum(ks.get(k, {}).get("count", 0) for k in kinds)
        ssum = sum(ks.get(k, {}).get("score_sum", 0) for k in kinds)
        scored = sum(ks.get(k, {}).get("scored", 0) for k in kinds)
        avg = round(ssum / scored) if scored else None
        ok = count >= _AREA_NEED and (avg or 0) >= _AREA_FLOOR
        areas_ok = areas_ok and ok
        areas.append({"area": area, "count": count, "avg": avg,
                      "need": _AREA_NEED, "floor": _AREA_FLOOR, "ok": ok})
    return areas, areas_ok


def _global_ok(st):
    return st["count"] >= _LEVELUP_NEED and (st["avg_score"] or 0) >= 85


def _mastered(level):
    """¿El usuario DOMINA el nivel? (cumple el global Y todas las áreas). Para las medallas."""
    if not _global_ok(db.level_stats(level)):
        return False
    _areas, areas_ok = _area_breakdown(level)
    return areas_ok


def _levelup_data(level):
    st = db.level_stats(level)
    nxt = None
    if level in _CEFR_ORDER:
        i = _CEFR_ORDER.index(level)
        if i < len(_CEFR_ORDER) - 1:
            nxt = _CEFR_ORDER[i + 1]
    areas, areas_ok = _area_breakdown(level)
    ready = bool(nxt) and _global_ok(st) and areas_ok
    return {"level": level, "next_level": nxt, "ready": ready, "need": _LEVELUP_NEED,
            "count": st["count"], "avg_score": st["avg_score"], "areas": areas}


@router.get("/levelup")
def levelup(level: str):
    return _levelup_data(level)


@router.get("/medals")
def medals():
    """Medallas por nivel CEFR. Se gana al DOMINAR el nivel; dominar uno otorga los de abajo."""
    highest_idx = -1
    for i, lv in enumerate(_CEFR_ORDER):
        if _mastered(lv):
            highest_idx = i
    earned = set(_CEFR_ORDER[:highest_idx + 1]) if highest_idx >= 0 else set()
    return {
        "levels": [{"level": lv, "earned": lv in earned} for lv in _CEFR_ORDER],
        "highest": _CEFR_ORDER[highest_idx] if highest_idx >= 0 else None,
    }


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
