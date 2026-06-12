"""FastAPI: API del tutor + servir el frontend compilado (React).

Arrancar (desde E:\\english-tutor):
    .venv\\Scripts\\python.exe -m uvicorn backend.main:app --port 8000
"""
import os
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from config import BASE_DIR
from backend import db
from backend.logging_setup import setup_logging, log
from backend.routers import ALL as ROUTERS

setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    # Precarga el modelo Whisper en segundo plano para que la 1ª petición no espere.
    def _warmup():
        try:
            from services.stt import get_model
            get_model()
        except Exception as e:  # noqa: BLE001
            log.warning("Whisper no precargado: %s", e)
    threading.Thread(target=_warmup, daemon=True).start()
    yield


app = FastAPI(title="Myna API", lifespan=lifespan)

# CORS solo necesario en desarrollo (Vite en :5173). En producción es mismo origen.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_error_handler(request: Request, exc: Exception):
    """Interceptor global: convierte cualquier fallo en un JSON con mensaje amigable."""
    log.exception("Error no controlado en %s", request.url.path)
    s = str(exc).lower()
    if any(k in s for k in ("connection", "refused", "max retries", "11434", "connect")):
        msg = "No pude conectar con Ollama. Comprueba que está abierto (app de Ollama o `ollama serve`)."
    elif "model" in s and ("not found" in s or "pull" in s or "no such" in s):
        msg = "El modelo de Ollama no está disponible. Ejecuta `ollama pull qwen2.5:3b`."
    else:
        msg = f"Ups, algo falló: {exc}"
    return JSONResponse(status_code=500, content={"detail": msg})


for _module in ROUTERS:
    app.include_router(_module.router, prefix="/api")


@app.get("/api/health")
def health():
    return {"ok": True}


# Sirve el frontend compilado (si existe). Debe ir al final (catch-all).
_DIST = os.path.join(BASE_DIR, "frontend", "dist")
if os.path.isdir(_DIST):
    app.mount("/", StaticFiles(directory=_DIST, html=True), name="spa")
else:
    print(f"[INFO] No hay build del frontend en {_DIST}. Usa Vite en dev (npm run dev).")
