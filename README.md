# 🐦 Myna — tu tutor de idiomas (local)

> *Myna*: el ave que aprende a imitar el habla humana. La app te ayuda a **imitar,
> repetir y sonar nativo**.

App para practicar idiomas (hoy inglés): **conversa por voz**, mejora tu **pronunciación**
hasta el nivel del **fonema**, haz **ejercicios** de corregir texto, **vocabulario** y un
**traductor** — con puntos y rachas. Todo se procesa en tu PC.

Arquitectura **desacoplada**:
- **Backend** (FastAPI) → expone toda la lógica como API. Reutiliza la capa `services/`
  (Whisper local, Ollama, edge-tts, pronunciación con CMUdict).
- **Frontend** (React + Vite + TypeScript + Tailwind) → UI moderna, tema claro/oscuro.
- **Persistencia**: SQLite (`tutor.db`) para puntos/racha.

> Lo único que usa internet es el audio de las voces (edge-tts). Escucharte (Whisper) y
> la IA (Ollama) son 100% locales.

---

## 📦 Instalar en otra PC (Windows)

### Opción A — Asistente .exe (lo más fácil)
1. En este equipo, genera el instalador:
   ```powershell
   .\packaging\package.ps1                    # empaqueta la app
   & "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe" packaging\installer.iss   # crea el Setup.exe
   ```
   → produce **`dist_installer\Myna-Setup.exe`**.
2. Copia ese `.exe` a la otra PC y **doble clic** → Siguiente → Instalar → Finalizar.
3. La **primera vez que se abre**, instala solo lo necesario (Python, dependencias, Ollama y
   el modelo según GPU/RAM). Se instala en la carpeta del usuario (sin permisos de admin).

> Al ser un instalador sin firmar, Windows SmartScreen puede avisar:
> **"Más información" → "Ejecutar de todas formas"**.

### Opción B — Carpeta + scripts (sin .exe)
1. `.\packaging\package.ps1` → `dist_package\Myna.zip`; copia y descomprime en la otra PC.
2. **Doble clic en `Instalar.bat`** y luego en **`Abrir Myna.bat`** (o en Linux: `./install.sh` y `./run.sh`).

> No necesita Node (frontend precompilado) ni ffmpeg (lo trae `av`).
> Solo requiere internet la primera vez (descargas) y para el audio de las voces.

## Requisitos (para desarrollar aquí)
- **Python 3.13** (el venv ya está en `.venv`).
- **Node 18+** (para compilar el frontend).
- **Ollama** corriendo con un modelo (`ollama list`). Por defecto `qwen2.5:3b`.

## Arrancar (uso normal)
El frontend ya viene compilado en `frontend/dist` y lo sirve el backend:

```powershell
.\run.ps1
```
Abre **http://127.0.0.1:8000**. (O manualmente:
`.\.venv\Scripts\python.exe -m uvicorn backend.main:app --port 8000`.)

## Desarrollo del frontend (recarga en caliente)
En dos terminales:

```powershell
# 1) Backend API
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --port 8000 --reload

# 2) Frontend (Vite, proxia /api al backend)
cd frontend
npm run dev          # http://localhost:5173
```

Cuando termines, recompila para producción:
```powershell
cd frontend; npm run build
```

---

## Estructura

```
english-tutor/
  backend/
    main.py        # FastAPI: lifespan (warmup Whisper), CORS, errores, sirve el SPA
    routes.py      # todos los endpoints /api/*
    db.py          # SQLite (stats/gamificación)
    schemas.py     # modelos Pydantic
    constants.py   # escenarios de conversación
  services/        # stt, tts, llm, pronunciation, runtime
  config.py        # modelos, voces, nivel
  frontend/        # React + Vite + TS + Tailwind
    src/{App,api,ui,modules}.tsx, src/tabs/*.tsx
  models_catalog.json   # catálogo de modelos editable (Ajustes)
  run.ps1 · install.ps1 · Instalar.bat        # ejecutar / instalar (Windows)
  run.sh · install.sh                          # ejecutar / instalar (Linux)
  packaging/   # package.ps1 + installer.iss (build del ZIP y del Setup.exe)
```

## Endpoints principales
| Método | Ruta | Qué hace |
|---|---|---|
| GET  | `/api/meta` · `/api/stats` | niveles/escenarios · puntos |
| POST | `/api/conversation/start` · `/turn` | pregunta inicial · turno (audio→texto+respuesta) |
| POST | `/api/reading/sentence` · `/evaluate` | frase para leer · evaluación de pronunciación |
| POST | `/api/text/new` · `/check` | frase con errores · comprobar corrección |
| POST | `/api/vocab/new` | tiempos verbales / sinónimos |
| POST | `/api/translate` | ES ↔ EN |
| GET  | `/api/tts?text=...&lang=...&slow=...` | audio de una frase (cacheado) |

## Configuración
Edita `config.py` o usa variables de entorno: `TUTOR_OLLAMA_MODEL`, `TUTOR_WHISPER_MODEL`,
`TUTOR_TTS_VOICE`, `TUTOR_TTS_VOICE_ES`.

### Catálogo de modelos (Ajustes)
La lista de modelos sugeridos en **Ajustes** se puede actualizar **sin tocar código**:
- Edita **`models_catalog.json`** (raíz del proyecto) — formato `{"name","gb","label","family"}`.
  Se aplica al instante (se lee en cada consulta, no hace falta reiniciar).
- O define `TUTOR_CATALOG_URL` con una URL a un JSON con el mismo formato (auto-update remoto;
  con *fallback* al archivo local y, si no, a la lista interna).
- `gb` = memoria aprox. (Q4) que ocupa; el app marca **cabe/no cabe** según tu VRAM/RAM real.
- Desde Ajustes puedes **instalar** (con barra de progreso) y **desinstalar** modelos, y cambiar
  el activo al instante.

