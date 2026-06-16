"""Reconocimiento de voz local con faster-whisper."""
import os
import threading

from config import WHISPER_MODEL, WHISPER_COMPUTE, BASE_DIR

_model = None
_actual_device = None  # dispositivo real donde cargó el modelo (tras posible fallback)
_load_lock = threading.Lock()   # evita cargar el modelo dos veces en paralelo
_infer_lock = threading.Lock()  # WhisperModel.transcribe no es seguro en paralelo
_WHISPER_FILE = os.path.join(BASE_DIR, "selected_whisper.txt")
# Tamaños disponibles (más grande = más preciso pero más lento)
# Los '.en' (solo inglés) llegan hasta medium. 'large-v3-turbo'/'large-v3' son multilingües y
# más precisos (más pesados y descargan más la 1ª vez); van bien en GPU.
WHISPER_SIZES = ["tiny.en", "base.en", "small.en", "medium.en", "large-v3-turbo", "large-v3"]


def current_model_name():
    try:
        with open(_WHISPER_FILE, "r", encoding="utf-8-sig") as f:
            v = f.read().lstrip("﻿").strip()
            if v:
                return v
    except Exception:
        pass
    return WHISPER_MODEL


def set_model_name(name):
    """Cambia el tamaño de Whisper en caliente (se recarga en la siguiente transcripción)."""
    global _model
    name = (name or "").strip() or WHISPER_MODEL
    try:
        with open(_WHISPER_FILE, "w", encoding="utf-8") as f:
            f.write(name)
    except Exception as e:
        print(f"[STT] No pude guardar el modelo: {e}")
    _model = None  # fuerza recarga
    return name


def _resolve_device():
    """Decide GPU/CPU según la preferencia del usuario (Ajustes).

    'cpu' fuerza CPU. 'gpu' (por defecto) usa CUDA SOLO si hay una NVIDIA disponible;
    ctranslate2 no acelera con AMD/Intel, así que en esos equipos 'gpu' cae a CPU."""
    from services import runtime
    if runtime.get_whisper_device() != "cpu":
        try:
            import ctranslate2
            if ctranslate2.get_cuda_device_count() > 0:
                return "cuda", "float16"
        except Exception:
            pass
    return "cpu", WHISPER_COMPUTE


def _add_cuda_dll_dirs():
    """Hace visibles las DLL de CUDA (cuBLAS/cuDNN) instaladas vía pip (solo Windows)."""
    if not hasattr(os, "add_dll_directory"):
        return
    try:
        import nvidia
        for base in nvidia.__path__:  # namespace package -> usar __path__, no __file__
            for sub in ("cublas", "cudnn", "cuda_nvrtc"):
                d = os.path.join(base, sub, "bin")
                if os.path.isdir(d):
                    os.add_dll_directory(d)
    except Exception:
        pass


def _cuda_works(model):
    """Verifica que la GPU realmente infiere (cuBLAS/cuDNN presentes), no solo que carga."""
    try:
        import numpy as np
        segs, _ = model.transcribe(np.zeros(16000, dtype=np.float32), language="en")
        for _ in segs:
            break
        return True
    except Exception as e:
        print(f"[STT] CUDA carga pero no infiere ({e}); usando CPU.")
        return False


def active_device():
    """Dispositivo real en uso (tras el posible fallback), o el previsto si aún no cargó."""
    return _actual_device or _resolve_device()[0]


def set_device(pref):
    """Cambia el dispositivo de Whisper ('gpu'/'cpu') y fuerza recarga en la próxima
    transcripción (el modelo cargado vive en memoria, hay que soltarlo para cambiar)."""
    global _model, _actual_device
    from services import runtime
    val = runtime.set_whisper_device(pref)
    _model = None
    _actual_device = None
    return val


def get_model():
    """Carga el modelo Whisper una sola vez (la primera vez lo descarga)."""
    global _model, _actual_device
    if _model is not None:
        return _model
    with _load_lock:
        if _model is not None:   # otro hilo lo cargó mientras esperábamos
            return _model
        _add_cuda_dll_dirs()
        from faster_whisper import WhisperModel
        name = current_model_name()
        device, compute = _resolve_device()
        print(f"[STT] Cargando Whisper '{name}' en {device} ({compute}) ...")
        try:
            m = WhisperModel(name, device=device, compute_type=compute)
            if device == "cuda" and not _cuda_works(m):
                raise RuntimeError("cuda-no-inference")
            _model = m
            _actual_device = device
        except Exception as e:
            if device != "cpu":
                print(f"[STT] Cayendo a CPU ({e}).")
                _model = WhisperModel(name, device="cpu", compute_type=WHISPER_COMPUTE)
                _actual_device = "cpu"
            else:
                raise
        print(f"[STT] Modelo listo en {_actual_device}.")
    return _model


def transcribe(audio_path, word_timestamps=False):
    """Transcribe un archivo de audio a texto en inglés.

    Devuelve {"text": str, "words": [{"word", "prob", "start", "end"}, ...]}.
    'prob' es la confianza de Whisper en cada palabra (útil como pista de pronunciación).
    """
    if not audio_path:
        return {"text": "", "words": []}

    model = get_model()
    # La inferencia se ejecuta al iterar 'segments'; serializamos todo el bloque porque
    # WhisperModel.transcribe no es seguro en paralelo sobre la misma instancia.
    with _infer_lock:
        segments, _info = model.transcribe(
            audio_path,
            language="en",
            word_timestamps=word_timestamps,
            vad_filter=True,  # ignora silencios
        )
        text_parts, words = [], []
        for seg in segments:
            text_parts.append(seg.text)
            if word_timestamps and seg.words:
                for w in seg.words:
                    words.append({
                        "word": w.word.strip(),
                        "prob": round(float(w.probability), 3),
                        "start": round(float(w.start), 2),
                        "end": round(float(w.end), 2),
                    })

    return {"text": "".join(text_parts).strip(), "words": words}
