<p align="center">
  <img src="frontend/public/myna_wordmark.svg" alt="Myna" width="360" />
</p>

<p align="center">
  <b>Tu tutor de idiomas — 100% en tu PC.</b><br/>
  <em>Myna: el ave que aprende a imitar el habla. Imita, repite y suena nativo.</em>
</p>

<p align="center">
  <a href="https://github.com/Tanke6003/Myna-Languages/releases/latest">
    <img src="https://img.shields.io/badge/⬇%20Descargar-Myna%20Setup.exe-0F9D8C?style=for-the-badge" alt="Descargar Myna" />
  </a>
</p>

---

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

## 🧪 Modelos de IA probados

Pruebas hechas en este equipo para orientar la elección. **No** son benchmarks formales: una sola
tarea representativa del tutor y una valoración de calidad subjetiva.

**Equipo de prueba:** AMD Ryzen 7 3700X (8 núcleos / 16 hilos @ 4.2 GHz) · 32 GB RAM ·
NVIDIA RTX 5060 Ti (8 GB VRAM) · Windows 11 · Whisper `medium.en` en CUDA · Ollama (cuantización Q4).

**Tarea:** un turno de conversación en **B1** corrigiendo una frase con 2 errores claros
(*"Yesterday I go to the park and I eat a sandwich with my friends."*) más generar una frase de
lectura. Latencia **en caliente** (modelo ya cargado). Probado en **GPU** y forzando **CPU**
(`num_gpu=0`), con presupuesto amplio (rienda suelta).

### 🟢 En GPU — NVIDIA RTX 5060 Ti (8 GB VRAM)

| Modelo | Tamaño (Q4) | Latencia | Calidad | Notas |
|---|---|---|---|---|
| qwen2.5:0.5b | ~0.4 GB | 0.5 s | ★★☆☆☆ | Ultrarrápido pero apenas corrige (repite la frase). |
| qwen2.5:1.5b | ~1.0 GB | 0.6 s | ★★☆☆☆ | Rápido; correcciones confusas, se enrolla. |
| qwen2.5:3b | ~1.9 GB | 0.7 s | ★★★☆☆ | Gran relación calidad/velocidad. |
| **qwen2.5:7b** ⭐ | ~4.7 GB | 1.9 s | ★★★★★ | **El mejor:** capta ambos errores, formato limpio. |
| deepseek-llm:7b | ~4.7 GB | 2.4 s | ★★★☆☆ | DeepSeek *chat*. Rápido pero corrige peor. |
| gemma4 | ~9.6 GB | 3.1 s | ★★★☆☆ | Se le escapó un error; enorme, sin ventaja. |
| qwen3.5:9b | ~6.6 GB | 20.2 s | ★★☆☆☆ | No cabe en 8 GB → offload a RAM → lento. |
| qwen2.5:32b | ~20 GB | ✗ | — | **No arranca**: crash de CUDA (20 GB no caben en 8 GB). Solo CPU. |

### 🔵 En CPU — AMD Ryzen 7 3700X (8 núcleos / 16 hilos)

| Modelo | Tamaño (Q4) | Latencia | Calidad | Notas |
|---|---|---|---|---|
| qwen2.5:0.5b | ~0.4 GB | 1.8 s | ★★☆☆☆ | El más ligero; va bien hasta en CPU muy modesta. |
| qwen2.5:1.5b | ~1.0 GB | 4.7 s | ★★☆☆☆ | Aceptable en CPU justa. |
| deepseek-llm:7b | ~4.7 GB | 5.1 s | ★★★☆☆ | Sorprendentemente ligero en CPU. |
| qwen2.5:3b | ~1.9 GB | 5.7 s | ★★★☆☆ | Buen equilibrio en CPU. |
| **qwen2.5:7b** ⭐ | ~4.7 GB | 11.7 s | ★★★★★ | Mejor calidad práctica; ya se nota en CPU. |
| qwen2.5:32b | ~20 GB | 69.7 s | ★★★★★ | **Máxima calidad** (capta ambos errores) pero **~70 s/respuesta**. No práctico. |
| gemma4 | ~9.6 GB | 73.6 s | ★★★☆☆ | Muy lento en CPU. |
| qwen3.5:9b | ~6.6 GB | 125 s | ★★☆☆☆ | Lentísimo en CPU (~2 min/respuesta). |

> `✗` = no arranca · *Latencia = en caliente, modelo ya cargado.*

### ¿GPU o CPU?
- **Si el modelo CABE en la VRAM (≤ ~4.7 GB → hasta 7b):** la **GPU gana claro** — p. ej. `qwen2.5:7b` va **1.9 s en GPU vs 11.7 s en CPU** (~6× más rápido).
- **Si NO cabe (> 8 GB):** la GPU descarga a RAM y **deja de ayudar** (`qwen3.5:9b`: 20 s GPU). Y si es **mucho** más grande que la VRAM (`qwen2.5:32b`, 20 GB), **ni siquiera arranca en GPU** (crash) → toca CPU, donde tarda ~70 s por respuesta.
- **Regla práctica:** usa GPU siempre que el modelo entre en tu VRAM; si no entra, **baja de tamaño** en vez de sufrir el offload (o el crash). En **Ajustes** puedes alternar **GPU/CPU** (por defecto GPU).

**Veredicto de modelo:** con GPU → `qwen2.5:7b`. En CPU → `qwen2.5:3b` (o `1.5b`/`0.5b` si el equipo va muy justo). Como alternativa de DeepSeek (chat, no razonamiento) está `deepseek-llm:7b`.

