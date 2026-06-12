"""Modelo de Ollama activo en tiempo de ejecución (configurable desde la app).

Se persiste en selected_model.txt (el mismo fichero que escribe install.ps1), así
la elección sobrevive a reinicios y es coherente con el instalador.
"""
import os

from config import OLLAMA_MODEL, BASE_DIR

_MODEL_FILE = os.path.join(BASE_DIR, "selected_model.txt")
_current = None


def _load():
    try:
        with open(_MODEL_FILE, "r", encoding="utf-8") as f:
            return f.read().strip() or OLLAMA_MODEL
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
