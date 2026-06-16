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
   → produce **`dist_installer\Myna-Setup-<versión>.exe`** (p. ej. `Myna-Setup-1.3.0.exe`,
   tomando el número de la versión del fichero `VERSION` de la raíz).
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

### 🔴 GPU AMD / Radeon (p. ej. RX 6600)

> ⚠️ **No probado.** No tengo una GPU AMD a mano para verificarlo; el soporte está implementado
> según la documentación de Ollama/ROCm pero **falta confirmarlo en una Radeon real**. Si lo
> pruebas, dime qué tal y lo marco como verificado.

El tutor usa la GPU para dos cosas, y **AMD no sirve igual para ambas**:

- **LLM (Ollama):** sí puede usar la Radeon vía **ROCm**. La detección de hardware (Ajustes →
  *Tu sistema*) ahora reconoce AMD/Intel además de NVIDIA, muestra su **nombre y VRAM**, y usa esa
  VRAM para recomendar el modelo (una RX 6600 de 8 GB → recomienda **`qwen2.5:7b`**).
- **Whisper (voz→texto):** la librería (`faster-whisper`/`ctranslate2`) es **solo CUDA/NVIDIA**, así
  que en AMD **siempre va por CPU**. Por eso en Ajustes el dispositivo de Ollama y el de Whisper son
  **independientes**: en una AMD puedes poner Ollama en GPU y Whisper queda en CPU (no hay otra).

**Override de ROCm (automático):** la RX 6600 es `gfx1032`, que **no** está en la lista oficial de
ROCm de Ollama. El instalador detecta una AMD RDNA2 (serie RX 6000) y fija de forma persistente:

```
HSA_OVERRIDE_GFX_VERSION = 10.3.0
```

con lo que Ollama la trata como una `gfx1030` soportada y la usa. (Las RX 7000 ya van nativas; no
necesitan override. En Linux hace falta tener **ROCm instalado** en el sistema; en Windows lo trae
el propio Ollama.)

**Si tras instalar Ollama sigue yendo por CPU:**
1. Cierra Ollama y vuelve a abrirlo (o **reinicia una vez**): la variable se aplica al **arrancar** el
   servidor, así que si ya estaba abierto no la toma hasta reiniciarlo.
2. Comprueba con:
   ```powershell
   ollama ps      # debe indicar 100% GPU; si dice CPU, no la está usando
   ```
3. Si tu Radeon **no** es de la serie RX 6000, puede necesitar otro valor de
   `HSA_OVERRIDE_GFX_VERSION` (búscalo para tu modelo) o no estar soportada por ROCm.

