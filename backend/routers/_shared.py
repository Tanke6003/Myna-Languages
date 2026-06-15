"""Helpers compartidos por los routers."""
import os
import shutil
import tempfile

from fastapi import UploadFile

from backend import db


def save_temp(upload: UploadFile) -> str:
    """Guarda un audio subido en un fichero temporal y devuelve su ruta."""
    suffix = os.path.splitext(upload.filename or "")[1] or ".webm"
    fd, path = tempfile.mkstemp(suffix=suffix)
    with os.fdopen(fd, "wb") as f:
        shutil.copyfileobj(upload.file, f)
    return path


def fresh(kind, sig_of, generate, attempts=4):
    """Genera un ejercicio que NO se haya visto ya (para no repetir), y lo marca como visto.

    - kind: identifica el generador (p. ej. 'reading', 'text', 'vocab_synonym', 'concept').
    - sig_of(result) -> str: extrae el texto identificador del resultado (la frase/prompt/pasaje).
    - generate() -> result: produce un ejercicio (puede llamarse varias veces).

    Reintenta hasta `attempts` veces evitando lo ya visto; si la variedad se agota, devuelve
    el último (degradación elegante). Se aplica a todos los módulos menos la conversación.
    """
    seen = db.seen_recent(kind)
    result = None
    for _ in range(attempts):
        result = generate()
        if db._norm_sig(sig_of(result)) not in seen:
            break
    db.seen_add(kind, sig_of(result))
    return result
