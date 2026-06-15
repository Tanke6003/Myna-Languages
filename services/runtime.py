"""Modelo de Ollama activo en tiempo de ejecución (configurable desde la app).

Se persiste en selected_model.txt (el mismo fichero que escribe install.ps1), así
la elección sobrevive a reinicios y es coherente con el instalador.
"""
import os

from config import OLLAMA_MODEL, BASE_DIR, TTS_VOICE

_MODEL_FILE = os.path.join(BASE_DIR, "selected_model.txt")
_DEVICE_FILE = os.path.join(BASE_DIR, "selected_device.txt")
_VOICE_FILE = os.path.join(BASE_DIR, "selected_voice.txt")
_current = None
_device = None  # "gpu" (Ollama usa GPU si puede) o "cpu" (fuerza CPU)
_voice = None   # voz TTS inglesa que habla al usuario (configurable en Ajustes)


def _load():
    try:
        # utf-8-sig + lstrip: tolera el BOM que escribe PowerShell 5.1 (Set-Content -Encoding utf8).
        with open(_MODEL_FILE, "r", encoding="utf-8-sig") as f:
            return f.read().lstrip("﻿").strip() or OLLAMA_MODEL
    except Exception:
        return OLLAMA_MODEL


def get_model():
    global _current
    if _current is None:
        _current = _load()
    return _current


def set_model(name):
    global _current
    _current = (name or "").strip() or OLLAMA_MODEL
    try:
        with open(_MODEL_FILE, "w", encoding="utf-8") as f:
            f.write(_current)
    except Exception as e:
        print(f"[runtime] No pude guardar el modelo: {e}")
    return _current


def get_device():
    """'gpu' (por defecto; Ollama usa GPU si está disponible) o 'cpu' (forzado)."""
    global _device
    if _device is None:
        try:
            with open(_DEVICE_FILE, "r", encoding="utf-8-sig") as f:
                _device = f.read().strip().lower()
        except Exception:
            _device = "gpu"
    return _device if _device in ("gpu", "cpu") else "gpu"


def set_device(d):
    global _device
    _device = "cpu" if str(d).strip().lower() == "cpu" else "gpu"
    try:
        with open(_DEVICE_FILE, "w", encoding="utf-8") as f:
            f.write(_device)
    except Exception as e:
        print(f"[runtime] No pude guardar el dispositivo: {e}")
    return _device


def get_voice():
    """Voz TTS inglesa activa (la que le habla al usuario). Por defecto, la de config."""
    global _voice
    if _voice is None:
        try:
            with open(_VOICE_FILE, "r", encoding="utf-8-sig") as f:
                _voice = f.read().strip() or TTS_VOICE
        except Exception:
            _voice = TTS_VOICE
    return _voice or TTS_VOICE


def set_voice(name):
    global _voice
    _voice = (name or "").strip() or TTS_VOICE
    try:
        with open(_VOICE_FILE, "w", encoding="utf-8") as f:
            f.write(_voice)
    except Exception as e:
        print(f"[runtime] No pude guardar la voz: {e}")
    return _voice
