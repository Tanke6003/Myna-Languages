"""Información del sistema y configuración de modelos (Ollama + Whisper)."""
import json
import os

import httpx
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


def _cpu_info():
    """(nombre, GHz) del CPU — best-effort multiplataforma."""
    name, ghz = "", 0.0
    try:
        import psutil
        f = psutil.cpu_freq()
        if f and (f.max or f.current):
            ghz = round((f.max or f.current) / 1000, 1)
    except Exception:
        pass
    try:
        import platform
        sysname = platform.system()
        if sysname == "Windows":
            import winreg
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                r"HARDWARE\DESCRIPTION\System\CentralProcessor\0") as k:
                name = winreg.QueryValueEx(k, "ProcessorNameString")[0].strip()
                if not ghz:
                    ghz = round(winreg.QueryValueEx(k, "~MHz")[0] / 1000, 1)
        elif sysname == "Linux":
            with open("/proc/cpuinfo", encoding="utf-8") as fh:
                for line in fh:
                    if line.lower().startswith("model name"):
                        name = line.split(":", 1)[1].strip()
                        break
        if not name:
            name = platform.processor()
    except Exception:
        pass
    return name, ghz


def _cpu_cap_gb(cores, ghz):
    """Tope razonable de tamaño de modelo cuando se corre SOLO en CPU (sin GPU).
    La inferencia en CPU depende sobre todo de núcleos físicos y frecuencia."""
    if cores >= 8:
        return 5                                   # 7B va bien
    if cores >= 6:
        return 5 if ghz >= 3.0 else 3
    if cores >= 4:
        return 3 if ghz >= 2.4 else 2              # 3B / 1.5B
    if cores >= 2:
        return 2 if ghz >= 2.2 else 1              # 1.5B / 0.5B
    return 1                                        # 0.5B


def _available_models():
    try:
        import ollama
        # Timeout corto: si el daemon está ocupado, /system no se cuelga (devuelve []).
        data = ollama.Client(timeout=httpx.Timeout(5.0, connect=3.0)).list()
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
    {"name": "qwen2.5:0.5b", "gb": 1, "label": "Ultraligero (mínimo usable)", "family": "qwen"},
    {"name": "qwen2.5:1.5b", "gb": 2, "label": "Muy ligero (CPU modesta)", "family": "qwen"},
    {"name": "qwen2.5:3b", "gb": 3, "label": "Rápido", "family": "qwen"},
    {"name": "qwen2.5:7b", "gb": 5, "label": "Equilibrado (recomendado)", "family": "qwen"},
    {"name": "qwen2.5:14b", "gb": 9, "label": "Calidad alta", "family": "qwen"},
    {"name": "qwen2.5:32b", "gb": 20, "label": "Máxima calidad", "family": "qwen"},
    {"name": "deepseek-llm:7b", "gb": 5, "label": "Alternativa chat (DeepSeek)", "family": "deepseek"},
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


_HW_CACHE = None


def _hardware():
    """Hardware fijo de la máquina (RAM, CPU, GPU). Se calcula UNA vez por proceso:
    nvidia-smi y el registro son caros y no cambian en caliente."""
    global _HW_CACHE
    if _HW_CACHE is None:
        import psutil
        cuda = 0
        try:
            import ctranslate2
            cuda = ctranslate2.get_cuda_device_count()
        except Exception:
            pass
        cpu_name, cpu_ghz = _cpu_info()
        _HW_CACHE = {
            "ram_gb": round(psutil.virtual_memory().total / (1024 ** 3), 1),
            "cores": psutil.cpu_count(logical=False) or psutil.cpu_count() or 0,
            "threads": psutil.cpu_count(logical=True) or 0,
            "cpu_name": cpu_name,
            "cpu_ghz": cpu_ghz,
            "cuda": cuda,
            "vram": _gpu_vram_gb(),
            "gpu_name": _gpu_name() if cuda else "",
        }
    return _HW_CACHE


@router.get("/system")
def system_info():
    hw = _hardware()
    ram_gb, cores, vram = hw["ram_gb"], hw["cores"], hw["vram"]
    # Con GPU NVIDIA manda la VRAM. Sin ella, el límite real lo pone el CPU (núcleos+GHz),
    # acotado además por la RAM disponible.
    if vram > 0:
        budget = vram - 2
    else:
        budget = min(max(ram_gb - 4, 2), _cpu_cap_gb(cores, hw["cpu_ghz"]))
    avail_list = _available_models()          # una sola llamada a Ollama
    avail = set(avail_list)
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
        "cpu_threads": hw["threads"],
        "cpu_name": hw["cpu_name"],
        "cpu_ghz": hw["cpu_ghz"],
        "gpu": {"nvidia": hw["cuda"] > 0, "count": hw["cuda"], "name": hw["gpu_name"]},
        "whisper_device": stt.active_device(),
        "whisper_model": stt.current_model_name(),
        "whisper_sizes": stt.WHISPER_SIZES,
        "current_model": runtime.get_model(),
        "available_models": avail_list,
        "recommended_model": recommended,
        "model_catalog": catalog,
        "llm_device": runtime.get_device(),
        "gpu_available": hw["cuda"] > 0,
    }


@router.post("/settings/model")
def set_active_model(body: dict = Body(...)):
    name = (body.get("model") or "").strip()
    if not name:
        raise HTTPException(400, "Falta el nombre del modelo.")
    runtime.set_model(name)
    return {"current_model": runtime.get_model()}


@router.post("/settings/device")
def set_llm_device(body: dict = Body(...)):
    """Cambia el dispositivo del LLM: 'gpu' (usa GPU si puede) o 'cpu' (forzado)."""
    device = runtime.set_device(body.get("device", "gpu"))
    return {"llm_device": device}


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
