"""Información del sistema y configuración de modelos (Ollama + Whisper)."""
import json
import os
import platform
import re
import subprocess

import httpx
from fastapi import APIRouter, Body, Form, HTTPException
from fastapi.responses import StreamingResponse

import config
from services import stt, runtime

router = APIRouter(tags=["settings"])


# --- Detección de hardware / catálogo de modelos ---
# Fabricantes PCI relevantes para GPU (campo VEN_xxxx del ID del dispositivo).
_GPU_VENDORS = {"10de": "nvidia", "1002": "amd", "8086": "intel"}


def _nvidia_smi_gpus():
    """GPUs NVIDIA vía nvidia-smi: [{name, vendor, vram_gb}, ...]. Vacío si no hay NVIDIA.
    Es la fuente más fiable de nombre y VRAM para NVIDIA."""
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=4)
        gpus = []
        for ln in out.stdout.splitlines():
            parts = [p.strip() for p in ln.split(",")]
            if len(parts) >= 2 and parts[1].isdigit():
                gpus.append({"name": parts[0], "vendor": "nvidia",
                             "vram_gb": round(int(parts[1]) / 1024, 1)})  # MB -> GB
        return gpus
    except Exception:
        return []


def _vram_bytes(v):
    """qwMemorySize del registro puede venir como entero (REG_QWORD) o bytes (REG_BINARY)."""
    if isinstance(v, int):
        return v
    if isinstance(v, (bytes, bytearray)):
        return int.from_bytes(v, "little")
    return 0


def _gpus_windows():
    """GPUs vía el registro de Windows (clase 'Display'): nombre, fabricante (VEN_xxxx) y
    VRAM real en GB. Usa HardwareInformation.qwMemorySize (la VRAM real), NO el AdapterRAM
    de WMI, que es un DWORD de 32 bits y se topa en ~4 GB."""
    gpus = []
    try:
        import winreg
        base = r"SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc8-08002be10318}"
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, base) as cls:
            i = 0
            while True:
                try:
                    sub = winreg.EnumKey(cls, i)
                except OSError:
                    break
                i += 1
                if not sub.isdigit():            # 0000, 0001... (ignora "Properties", etc.)
                    continue
                try:
                    with winreg.OpenKey(cls, sub) as k:
                        def _val(name):
                            try:
                                return winreg.QueryValueEx(k, name)[0]
                            except OSError:
                                return None
                        match = str(_val("MatchingDeviceId") or "").upper()
                        m = re.search(r"VEN_([0-9A-F]{4})", match)
                        if not m:                # sin VEN_ no es PCI (Basic Render, RDP...)
                            continue
                        vendor = _GPU_VENDORS.get(m.group(1).lower(), "other")
                        vram = round(_vram_bytes(_val("HardwareInformation.qwMemorySize")) / (1024 ** 3), 1)
                        gpus.append({"name": str(_val("DriverDesc") or "").strip(),
                                     "vendor": vendor, "vram_gb": vram})
                except OSError:
                    continue
    except Exception:
        pass
    return gpus


def _gpus_linux():
    """GPUs vía sysfs: fabricante y (en AMD) VRAM. Nombre best-effort con lspci."""
    import glob
    names = {}
    try:                                          # mapa 'bus PCI -> nombre' desde lspci, si está
        out = subprocess.run(["lspci", "-D"], capture_output=True, text=True, timeout=4)
        for ln in out.stdout.splitlines():
            if re.search(r"VGA|3D|Display", ln):
                bus, _, desc = ln.partition(" ")
                names[bus] = desc.split(":", 1)[-1].strip()
    except Exception:
        pass
    gpus = []
    for dev in glob.glob("/sys/class/drm/card[0-9]*/device"):
        try:
            with open(os.path.join(dev, "vendor")) as f:
                vid = f.read().strip().lower().replace("0x", "")
            vendor = _GPU_VENDORS.get(vid, "other")
            vram = 0
            mem = os.path.join(dev, "mem_info_vram_total")     # lo expone el driver AMD
            if os.path.exists(mem):
                with open(mem) as f:
                    vram = round(int(f.read().strip()) / (1024 ** 3), 1)
            bus = os.path.basename(os.path.realpath(dev))
            gpus.append({"name": names.get(bus, vendor.upper() + " GPU"),
                         "vendor": vendor, "vram_gb": vram})
        except Exception:
            continue
    return gpus


def _detect_gpus():
    """Todas las GPUs (NVIDIA/AMD/Intel) con fabricante y VRAM. Multiplataforma, best-effort.
    nvidia-smi manda para NVIDIA (nombre y VRAM más fiables que el registro/sysfs)."""
    gpus = _gpus_windows() if platform.system() == "Windows" else _gpus_linux()
    smi = _nvidia_smi_gpus()
    if smi:
        gpus = [g for g in gpus if g["vendor"] != "nvidia"] + smi
    return gpus


def _best_gpu(gpus):
    """La GPU 'principal' para acelerar: la usable (NVIDIA/AMD) con más VRAM. Así, en un
    equipo con iGPU + tarjeta discreta, se queda con la discreta (más VRAM)."""
    usable = [g for g in gpus if g["vendor"] in ("nvidia", "amd")]
    if not usable:
        return None
    rank = {"nvidia": 2, "amd": 1}               # a igual VRAM, prioriza NVIDIA
    return max(usable, key=lambda g: (g["vram_gb"], rank.get(g["vendor"], 0)))


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

# Voces TTS (edge-tts) que le hablan al usuario. Curado: acento + sexo. Etiqueta neutra de idioma.
VOICE_CATALOG = [
    {"id": "en-US-AriaNeural", "label": "Aria — US (♀)"},
    {"id": "en-US-JennyNeural", "label": "Jenny — US (♀)"},
    {"id": "en-US-GuyNeural", "label": "Guy — US (♂)"},
    {"id": "en-US-EricNeural", "label": "Eric — US (♂)"},
    {"id": "en-GB-SoniaNeural", "label": "Sonia — UK (♀)"},
    {"id": "en-GB-RyanNeural", "label": "Ryan — UK (♂)"},
    {"id": "en-AU-NatashaNeural", "label": "Natasha — AU (♀)"},
    {"id": "en-AU-WilliamNeural", "label": "William — AU (♂)"},
    {"id": "en-HK-YanNeural", "label": "Yan — Hong Kong 🇭🇰 (♀)"},
    {"id": "en-HK-SamNeural", "label": "Sam — Hong Kong 🇭🇰 (♂)"},
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
            import ctranslate2     # solo NVIDIA/CUDA; sirve para saber si Whisper puede ir en GPU
            cuda = ctranslate2.get_cuda_device_count()
        except Exception:
            pass
        cpu_name, cpu_ghz = _cpu_info()
        gpus = _detect_gpus()
        best = _best_gpu(gpus)
        _HW_CACHE = {
            "ram_gb": round(psutil.virtual_memory().total / (1024 ** 3), 1),
            "cores": psutil.cpu_count(logical=False) or psutil.cpu_count() or 0,
            "threads": psutil.cpu_count(logical=True) or 0,
            "cpu_name": cpu_name,
            "cpu_ghz": cpu_ghz,
            "cuda": cuda,
            "gpus": gpus,
            "gpu_name": best["name"] if best else "",
            "gpu_vendor": best["vendor"] if best else "",
            "vram": best["vram_gb"] if best else 0,
        }
    return _HW_CACHE


@router.get("/system")
def system_info():
    hw = _hardware()
    ram_gb, cores, vram = hw["ram_gb"], hw["cores"], hw["vram"]
    vendor = hw["gpu_vendor"]
    nvidia = vendor == "nvidia" or hw["cuda"] > 0
    amd = any(g["vendor"] == "amd" for g in hw["gpus"])
    # El LLM (Ollama) puede usar GPU NVIDIA o AMD (vía ROCm). Whisper SOLO NVIDIA/CUDA.
    gpu_available = nvidia or amd
    # Con una GPU usable (NVIDIA o AMD) y VRAM conocida, manda su VRAM. Sin ella (solo CPU,
    # o AMD sin VRAM detectada), el límite lo pone el CPU (núcleos+GHz), acotado por la RAM.
    if vram > 0 and vendor in ("nvidia", "amd"):
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
        "version": config.APP_VERSION,
        "ram_gb": ram_gb,
        "vram_gb": vram,
        "budget_gb": round(budget, 1),
        "cpu_cores": cores,
        "cpu_threads": hw["threads"],
        "cpu_name": hw["cpu_name"],
        "cpu_ghz": hw["cpu_ghz"],
        "gpu": {"nvidia": nvidia, "amd": amd, "vendor": vendor,
                "count": hw["cuda"], "name": hw["gpu_name"]},
        "whisper_device": stt.active_device(),
        "whisper_device_pref": runtime.get_whisper_device(),
        "whisper_gpu_available": hw["cuda"] > 0,   # ctranslate2 es solo NVIDIA
        "whisper_model": stt.current_model_name(),
        "whisper_sizes": stt.WHISPER_SIZES,
        "current_model": runtime.get_model(),
        "available_models": avail_list,
        "recommended_model": recommended,
        "model_catalog": catalog,
        "llm_device": runtime.get_device(),
        "gpu_available": gpu_available,
        "tts_voice": runtime.get_voice(),
        "tts_voices": VOICE_CATALOG,
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


@router.post("/settings/voice")
def set_tts_voice(body: dict = Body(...)):
    """Fija la voz inglesa que le habla al usuario (se persiste en selected_voice.txt)."""
    voice = (body.get("voice") or "").strip()
    if not voice:
        raise HTTPException(400, "Falta la voz.")
    runtime.set_voice(voice)
    return {"tts_voice": runtime.get_voice()}


@router.post("/settings/whisper")
def set_whisper_model(body: dict = Body(...)):
    name = (body.get("model") or "").strip()
    if not name:
        raise HTTPException(400, "Falta el modelo de Whisper.")
    stt.set_model_name(name)
    return {"whisper_model": stt.current_model_name()}


@router.post("/settings/whisper-device")
def set_whisper_device(body: dict = Body(...)):
    """Dispositivo de Whisper: 'gpu' (CUDA si hay NVIDIA) o 'cpu'. Independiente del LLM."""
    stt.set_device(body.get("device", "gpu"))
    return {"whisper_device_pref": runtime.get_whisper_device()}


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


# ----------------------------------------------------------------------------
# Recordatorio diario (notificación del sistema; funciona con la app cerrada)
# ----------------------------------------------------------------------------
_REMINDER_FILE = os.path.join(config.BASE_DIR, "reminder.json")
_TIME_RE = re.compile(r"^[0-2]?\d:[0-5]\d$")


def _read_reminder():
    try:
        with open(_REMINDER_FILE, encoding="utf-8-sig") as f:
            d = json.load(f)
        t = d.get("time") or "19:00"
        return {"enabled": bool(d.get("enabled")), "time": t if _TIME_RE.match(t) else "19:00"}
    except Exception:
        return {"enabled": False, "time": "19:00"}


def _apply_reminder(enabled, time):
    """Registra/quita la tarea del SO: Tarea Programada en Windows, systemd --user en Linux.
    Best-effort: si el script no existe o falla, no se rompe la petición."""
    action = "enable" if enabled else "disable"
    if platform.system() == "Windows":
        script = os.path.join(config.BASE_DIR, "scripts", "reminder_setup.ps1")
        if os.path.exists(script):
            subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                            "-File", script, "-Action", action, "-Time", time],
                           capture_output=True, timeout=30)
    else:
        script = os.path.join(config.BASE_DIR, "scripts", "reminder_setup.sh")
        if os.path.exists(script):
            subprocess.run(["bash", script, action, time], capture_output=True, timeout=30)


@router.get("/settings/reminder")
def get_reminder():
    return _read_reminder()


@router.post("/settings/reminder")
def set_reminder(body: dict = Body(...)):
    enabled = bool(body.get("enabled"))
    time = (body.get("time") or "19:00").strip()
    if not _TIME_RE.match(time):
        time = "19:00"
    try:
        _apply_reminder(enabled, time)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(500, f"No se pudo programar el recordatorio: {e}")
    try:
        with open(_REMINDER_FILE, "w", encoding="utf-8") as f:
            json.dump({"enabled": enabled, "time": time}, f)
    except Exception:
        pass
    return {"enabled": enabled, "time": time}
