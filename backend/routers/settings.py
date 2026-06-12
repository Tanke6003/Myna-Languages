"""Información del sistema y configuración de modelos (Ollama + Whisper)."""
import json
import os

from fastapi import APIRouter, Body, Form, HTTPException
from fastapi.responses import StreamingResponse

import config
from services import stt, runtime

router = APIRouter(tags=["settings"])


# --- Detección de hardware / catálogo de modelos ---
def _gpu_name():
    try:
        import subprocess
        out = subprocess.run(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
                             capture_output=True, text=True, timeout=4)
        lines = [ln.strip() for ln in out.stdout.splitlines() if ln.strip()]
        return lines[0] if lines else ""
    except Exception:
        return ""


def _gpu_vram_gb():
    try:
        import subprocess
        out = subprocess.run(["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
                             capture_output=True, text=True, timeout=4)
        vals = [int(x.strip()) for x in out.stdout.splitlines() if x.strip().isdigit()]
        if vals:
            return round(max(vals) / 1024, 1)  # MB -> GB
    except Exception:
        pass
    return 0


def _available_models():
    try:
        import ollama
        data = ollama.list()
        models = getattr(data, "models", None)
        if models is None and isinstance(data, dict):
            models = data.get("models", [])
        names = []
        for m in (models or []):
            name = getattr(m, "model", None)
            if name is None and isinstance(m, dict):
                name = m.get("model") or m.get("name")
            if name:
                names.append(name)
        return names
    except Exception:
        return []


# Catálogo por defecto (built-in). Se puede sobreescribir con models_catalog.json o TUTOR_CATALOG_URL.
MODEL_CATALOG = [
    {"name": "qwen2.5:3b", "gb": 3, "label": "Rápido", "family": "qwen"},
    {"name": "qwen2.5:7b", "gb": 5, "label": "Equilibrado", "family": "qwen"},
    {"name": "qwen2.5:14b", "gb": 9, "label": "Calidad alta", "family": "qwen"},
    {"name": "qwen2.5:32b", "gb": 20, "label": "Máxima calidad", "family": "qwen"},
    {"name": "deepseek-r1:1.5b", "gb": 2, "label": "Razonamiento mini (muy ligero)", "family": "deepseek"},
    {"name": "deepseek-r1:7b", "gb": 5, "label": "Razonamiento (lento)", "family": "deepseek"},
    {"name": "deepseek-r1:14b", "gb": 9, "label": "Razonamiento+ (lento)", "family": "deepseek"},
    {"name": "deepseek-r1:32b", "gb": 20, "label": "Razonamiento máx (lento)", "family": "deepseek"},
]

_CATALOG_CACHE = None


def _get_catalog():
    """Catálogo actualizable SIN tocar el código.
    Prioridad: URL remota (env TUTOR_CATALOG_URL) > models_catalog.json local > lista interna.
    """
    global _CATALOG_CACHE
    url = os.environ.get("TUTOR_CATALOG_URL")
    if url:
        if _CATALOG_CACHE is None:
            try:
                import httpx
                data = httpx.get(url, timeout=6).json()
                if isinstance(data, list) and data:
                    _CATALOG_CACHE = data
            except Exception as e:  # noqa: BLE001
                print(f"[catalog] No pude actualizar desde {url}: {e}")
        if _CATALOG_CACHE:
            return _CATALOG_CACHE
    path = os.path.join(config.BASE_DIR, "models_catalog.json")
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list) and data:
                return data
        except Exception:
            pass
    return MODEL_CATALOG


@router.get("/system")
def system_info():
    import psutil
    ram_gb = round(psutil.virtual_memory().total / (1024 ** 3), 1)
    cores = psutil.cpu_count(logical=False) or psutil.cpu_count() or 0
    threads = psutil.cpu_count(logical=True) or 0
    cuda = 0
    try:
        import ctranslate2
        cuda = ctranslate2.get_cuda_device_count()
    except Exception:
        pass
    device = stt.active_device()
    vram = _gpu_vram_gb()
    budget = (vram - 2) if vram > 0 else max(ram_gb - 4, 2)
    avail = set(_available_models())
    cat = _get_catalog()
    catalog = [{**m, "fits": m.get("gb", 0) <= budget, "installed": m.get("name") in avail} for m in cat]
    fitting = [m for m in cat if m.get("gb", 0) <= budget]
    prefer = [m for m in fitting if m.get("family") != "deepseek"] or fitting
    recommended = max(prefer, key=lambda m: m.get("gb", 0))["name"] if prefer else "qwen2.5:3b"
    return {
        "ram_gb": ram_gb,
        "vram_gb": vram,
        "budget_gb": round(budget, 1),
        "cpu_cores": cores,
        "cpu_threads": threads,
        "gpu": {"nvidia": cuda > 0, "count": cuda, "name": _gpu_name() if cuda else ""},
        "whisper_device": device,
        "whisper_model": stt.current_model_name(),
        "whisper_sizes": stt.WHISPER_SIZES,
        "current_model": runtime.get_model(),
        "available_models": _available_models(),
        "recommended_model": recommended,
        "model_catalog": catalog,
    }


@router.post("/settings/model")
def set_active_model(body: dict = Body(...)):
    name = (body.get("model") or "").strip()
    if not name:
        raise HTTPException(400, "Falta el nombre del modelo.")
    runtime.set_model(name)
    return {"current_model": runtime.get_model()}


@router.post("/settings/whisper")
def set_whisper_model(body: dict = Body(...)):
    name = (body.get("model") or "").strip()
    if not name:
        raise HTTPException(400, "Falta el modelo de Whisper.")
    stt.set_model_name(name)
    return {"whisper_model": stt.current_model_name()}


@router.post("/settings/pull")
def pull_model(model: str = Form(...)):
    """Descarga un modelo de Ollama mostrando el progreso (SSE) y lo deja activo."""
    import ollama

    def event(d):
        return "data: " + json.dumps(d, ensure_ascii=False) + "\n\n"

    def gen():
        try:
            for ev in ollama.pull(model, stream=True):
                status = getattr(ev, "status", None)
                completed = getattr(ev, "completed", None)
                total = getattr(ev, "total", None)
                if status is None and isinstance(ev, dict):
                    status, completed, total = ev.get("status"), ev.get("completed"), ev.get("total")
                pct = round(100 * completed / total) if (completed and total) else None
                yield event({"status": status or "", "pct": pct})
            runtime.set_model(model)
            yield event({"status": "done", "model": runtime.get_model()})
        except Exception as e:  # noqa: BLE001
            yield event({"status": "error", "message": str(e)})

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.post("/settings/catalog/refresh")
def refresh_catalog():
    global _CATALOG_CACHE
    _CATALOG_CACHE = None
    return {"ok": True, "count": len(_get_catalog())}


@router.post("/settings/delete")
def delete_model(body: dict = Body(...)):
    import ollama
    name = (body.get("model") or "").strip()
    if not name:
        raise HTTPException(400, "Falta el modelo.")
    if name == runtime.get_model():
        raise HTTPException(400, "No puedes borrar el modelo activo. Cambia a otro primero.")
    try:
        ollama.delete(name)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(500, f"No se pudo borrar: {e}")
    return {"ok": True}
