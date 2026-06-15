"""Texto a voz. Primario: edge-tts (voces neuronales nativas, gratis, online).
Reserva: pyttsx3 (offline, voz de Windows) si no hay internet y está instalado.

La voz se elige según el idioma: inglés con voz inglesa, español con voz española.
"""
import asyncio
import hashlib
import os
import re

from config import TTS_VOICE, TTS_VOICE_ES, AUDIO_DIR

os.makedirs(AUDIO_DIR, exist_ok=True)


def prune_cache(max_files=600, max_mb=200):
    """Limita el caché de audio: borra los más viejos si se pasa de tope (archivos o MB)."""
    try:
        files = []
        total = 0
        for name in os.listdir(AUDIO_DIR):
            p = os.path.join(AUDIO_DIR, name)
            if os.path.isfile(p):
                st = os.stat(p)
                files.append((st.st_mtime, st.st_size, p))
                total += st.st_size
        files.sort()  # más antiguos primero
        limit = max_mb * 1024 * 1024
        i = 0
        while files and (len(files) - i > max_files or total > limit):
            _, size, p = files[i]
            try:
                os.remove(p)
                total -= size
            except OSError:
                pass
            i += 1
    except Exception:
        pass


prune_cache()  # poda al arrancar (barato salvo que haya miles de ficheros)

# Pistas de que un texto está en español
_ES_ACCENTS = re.compile(r"[áéíóúñ¿¡]", re.IGNORECASE)
_ES_WORDS = re.compile(
    r"\b(que|los|las|una|para|pero|con|cuando|porque|tienes|puedes|necesitas|"
    r"deberías|estás|está|frase|palabra|correcto|incorrecto|usar|decir)\b",
    re.IGNORECASE,
)


def detect_lang(text):
    """Devuelve 'es' si el texto parece español, 'en' en caso contrario."""
    if _ES_ACCENTS.search(text):
        return "es"
    if len(_ES_WORDS.findall(text)) >= 2:
        return "es"
    return "en"


def _cache_path(text, voice, rate, ext):
    key = hashlib.md5(f"{text}|{voice}|{rate}".encode("utf-8")).hexdigest()
    return os.path.join(AUDIO_DIR, f"{key}.{ext}")


def synthesize(text, lang=None, slow=False, voice=None):
    """Genera audio del texto y devuelve la ruta del archivo (o None si falla).

    lang: "en", "es" o None (detección automática del idioma).
    slow=True habla más despacio (útil para aprender la pronunciación).
    voice: fuerza una voz concreta (p. ej. para previsualizarla en Ajustes); si no se da,
           se usa la voz inglesa activa (configurable) o la española según el idioma.
    """
    text = (text or "").strip()
    if not text:
        return None

    lang = lang or detect_lang(text)
    if not voice:
        from services import runtime
        voice = TTS_VOICE_ES if lang == "es" else runtime.get_voice()
    rate = "-30%" if slow else "+0%"
    path = _cache_path(text, voice, rate, "mp3")
    if os.path.exists(path):
        return path

    # --- Intento 1: edge-tts (mejor calidad) ---
    try:
        import edge_tts

        async def _run():
            communicate = edge_tts.Communicate(text, voice, rate=rate)
            await communicate.save(path)

        asyncio.run(_run())
        if os.path.exists(path) and os.path.getsize(path) > 0:
            return path
    except Exception as e:
        print(f"[TTS] edge-tts no disponible ({e}); intento voz offline.")

    # --- Intento 2: pyttsx3 (offline) ---
    try:
        import pyttsx3

        wav_path = _cache_path(text, voice, rate, "wav")
        engine = pyttsx3.init()
        if slow:
            engine.setProperty("rate", int(engine.getProperty("rate") * 0.75))
        engine.save_to_file(text, wav_path)
        engine.runAndWait()
        if os.path.exists(wav_path) and os.path.getsize(wav_path) > 0:
            return wav_path
    except Exception as e:
        print(f"[TTS] Voz offline tampoco disponible ({e}).")

    return None
