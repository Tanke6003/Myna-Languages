"""Helpers compartidos por los routers."""
import os
import shutil
import tempfile

from fastapi import UploadFile


def save_temp(upload: UploadFile) -> str:
    """Guarda un audio subido en un fichero temporal y devuelve su ruta."""
    suffix = os.path.splitext(upload.filename or "")[1] or ".webm"
    fd, path = tempfile.mkstemp(suffix=suffix)
    with os.fdopen(fd, "wb") as f:
        shutil.copyfileobj(upload.file, f)
    return path
