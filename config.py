"""Configuración central de Myna (tutor de idiomas).

Cambia aquí los modelos, la voz o el nivel por defecto sin tocar el resto del código.
"""
import os

# --- Carpetas ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AUDIO_DIR = os.path.join(BASE_DIR, "_audio_cache")  # audios TTS generados


# --- Versión de la app (fuente única de verdad: el fichero VERSION en la raíz) ---
# La leen también el instalador (installer.iss) y la UI (vía /api/system).
def _read_version():
    try:
        # utf-8-sig: tolera el BOM que pueda meter un editor en Windows.
        with open(os.path.join(BASE_DIR, "VERSION"), "r", encoding="utf-8-sig") as f:
            return f.read().strip() or "0.0.0"
    except Exception:
        return "0.0.0"


APP_VERSION = _read_version()

# --- Modelo de IA (Ollama, local) ---
# Ejecuta `ollama list` para ver los que tienes. qwen3.5:9b o gemma4 funcionan bien.
OLLAMA_MODEL = os.environ.get("TUTOR_OLLAMA_MODEL", "qwen2.5:3b")

# --- Reconocimiento de voz (faster-whisper, local) ---
# Tamaños: tiny.en / base.en / small.en / medium.en  (más grande = más preciso pero más lento)
WHISPER_MODEL = os.environ.get("TUTOR_WHISPER_MODEL", "small.en")
# "auto" usa la GPU NVIDIA si está disponible y cae a CPU si no. También: "cuda" / "cpu".
WHISPER_DEVICE = os.environ.get("TUTOR_WHISPER_DEVICE", "auto")
WHISPER_COMPUTE = os.environ.get("TUTOR_WHISPER_COMPUTE", "int8")  # int8 = rápido en CPU

# --- Texto a voz (edge-tts, gratis, requiere internet) ---
# Voces nativas: en-US-AriaNeural, en-US-GuyNeural, en-GB-SoniaNeural, en-GB-RyanNeural
TTS_VOICE = os.environ.get("TUTOR_TTS_VOICE", "en-US-AriaNeural")
# Voz para el texto en español (correcciones, explicaciones, etc.)
TTS_VOICE_ES = os.environ.get("TUTOR_TTS_VOICE_ES", "es-MX-DaliaNeural")

# --- Velocidad de respuesta de Ollama ---
# keep_alive: cuánto tiempo se queda el modelo cargado en RAM (evita recargarlo cada vez).
OLLAMA_KEEP_ALIVE = os.environ.get("TUTOR_OLLAMA_KEEP_ALIVE", "20m")
# num_predict: máximo de tokens por respuesta (menor = más rápido).
OLLAMA_NUM_PREDICT = int(os.environ.get("TUTOR_OLLAMA_NUM_PREDICT", "400"))

# --- Nivel por defecto ---
# Niveles según el Marco Común Europeo (CEFR)
DEFAULT_LEVEL = "B1"
LEVELS = ["A1", "A2", "B1", "B2", "C1", "C2"]
