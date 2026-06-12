# 📋 Myna (tutor de idiomas) — Estado y tareas

Arquitectura: **FastAPI (backend) + React/Vite/TS/Tailwind (frontend)**, 100% local.
(La versión antigua con Gradio se eliminó; queda solo lo bueno.)

---

## ✅ Hecho

### Arquitectura
- [x] Backend FastAPI reutilizando `services/` (STT, TTS, LLM, pronunciación)
- [x] Frontend React + Vite + TypeScript + Tailwind (servido por FastAPI en producción)
- [x] SQLite (`tutor.db`): puntos, racha, historial de actividad, palabras falladas
- [x] Interceptor global de errores → toasts; warmup de Whisper al arrancar
- [x] Un solo comando: `run.ps1` (uvicorn sirve API + SPA en :8000)

### Funcionalidades (paridad + extras)
- [x] **Conversación** por voz: escenarios, manos libres, correcciones, análisis, pronunciación
- [x] **Editar lo que se entendió y reenviar** ("rebatir" errores de transcripción, p. ej. Jabil)
- [x] **Pronunciación/Lectura**: evaluación palabra a palabra, fonemas, audio modelo
- [x] **Dictado**: escuchas y escribes; corrección por palabras (LCS)
- [x] **Corregir texto** · **Vocabulario** (tiempos/sinónimos) · **Traductor**
- [x] **Traductor**: dirección ES↔EN, "rebatir/ajustar" con nota, audio; arreglada la fiabilidad (few-shot)
- [x] **Progreso**: medias por actividad, reciente, palabras a repasar, reinicio

### UI/UX
- [x] **Iconos SVG** (lucide) en lugar de emojis
- [x] **Reproductor de audio propio** (play/pausa + barra) en vez del nativo
- [x] Tema **claro/oscuro** con botón, paleta cálida, layout de 2 columnas en escritorio
- [x] Gamificación: puntos, nivel, racha (persistentes)

### Aprendizaje
- [x] Niveles **CEFR (A1–C2)**; dificultad calibrada al extremo alto de cada nivel
- [x] Tutor **exigente** (no consiente; feedback honesto orientado a mejorar)
- [x] El tutor **no corrige nombres propios**; el traductor respeta empresas/marcas
- [x] **Evitar auto-traducción del navegador** (`notranslate`) para no romper el inglés

---

## ✅ Distribución / hardware (nuevo)
- [x] **`install.ps1`**: detecta **GPU NVIDIA y RAM**, elige el modelo (GPU/16GB+ → 7B, si no → 3B),
      instala **Ollama** + el modelo, prepara Python y crea acceso directo.
- [x] **`package.ps1`**: genera `dist_package/EnglishTutor.zip` para copiar a otra PC (laptop).
- [x] **`run.ps1`**: abre en **modo app** (ventana sin pestañas) y usa el modelo elegido.
- [x] **Whisper auto-GPU**: usa CUDA si hay GPU, con *fallback* a CPU (verificado en cuda).
- [x] Más ejercicios de vocabulario: **antónimos, preposiciones, phrasal verbs**.
- [x] **Exportar / importar progreso** (lleva tu avance entre PCs).
- [x] **Modelo configurable en runtime** + pestaña **Ajustes** (RAM, CPU, GPU, Whisper, selector de modelo).
- [x] **Primer arranque**: revisa/instala Ollama y elige el mejor modelo según GPU/RAM.
- [x] Ejercicio de **listening comprehension** (audio + pregunta).
- [x] **Gráfica** de evolución de puntuaciones en Progreso.
- [x] **Traductor con sinónimos y ejemplos** sencillos (con audio y su español).
- [x] **Significado oculto tras un 👁** (ojito) en Pronunciación y Vocabulario.
- [x] **Shadowing** (escucha y repite imitando; texto oculto).
- [x] **Flashcards** con repetición espaciada (SM-2): añadir, repasar (Otra vez/Bien/Fácil),
      sembrar desde tus palabras falladas; reverso = significado en español.
- [x] **Streaming SSE** en la conversación: la respuesta del tutor aparece token a token.
- [x] **Fix Whisper-GPU**: verifica que CUDA realmente infiere (cuBLAS/cuDNN) y cae a CPU si no.

## ✅ Más hecho (UX + tutoreo + distribución)
- [x] **Navegación rediseñada**: barra lateral por categorías + pantalla de **Inicio** con tarjetas y descripción de cada módulo.
- [x] **Onboarding** la primera vez + **recomendaciones personalizadas** en Inicio.
- [x] Módulo **Repaso mixto** (tus palabras más falladas) y **Flashcards** con ayuda.
- [x] **Sugerencia de subir de nivel** (≥12 ejercicios con media ≥85 en el nivel).
- [x] **Instalador asistente .exe** (Inno Setup) `Myna-Setup.exe` + scripts Windows/Linux.

## ⏳ Aplazado (con motivo)
- [x] ~~App de escritorio nativa (Tauri)~~ → **RESUELTO de otra forma**: el asistente .exe + modo app
      ya dan experiencia de app instalable, sin necesidad de Tauri/Rust. **No hace falta.**
- [x] **GPU para Whisper — ¡ACTIVADA!** En equipos con NVIDIA, el instalador instala
      `nvidia-cublas-cu12` + `nvidia-cudnn-cu12` y Whisper corre en **GPU** (`medium.en` a ~0.3 s
      en caliente, antes ~5–14 s en CPU). Sin GPU compatible, *fallback* automático a CPU.

---

## 🌍 Diseño: modo multi-idioma (aprender varios idiomas) — PENDIENTE

**Objetivo:** poder aprender varios idiomas (inglés, francés, alemán, italiano, portugués…),
cada uno con su **progreso separado**.
**Ojo — son dos cosas distintas:** el *idioma de la interfaz* (i18n ES/EN, ya hecho) es
independiente del *idioma que se aprende* (esto es lo nuevo).
**Decisión tomada:** IPA en TODOS los idiomas con `phonemizer` + **espeak-ng** (lo añade el instalador).

### Núcleo: config de idiomas
En `config.py`, un mapa `LANGUAGES`:
```python
LANGUAGES = {
  "en": {"name": "English", "whisper": "en", "voice": "en-US-AriaNeural",  "espeak": "en-us"},
  "fr": {"name": "French",  "whisper": "fr", "voice": "fr-FR-DeniseNeural", "espeak": "fr"},
  # de, it, pt...
}
DEFAULT_TARGET = "en"
```
Idioma activo configurable en runtime (como el modelo): `services/runtime.py` →
`get_target()/set_target()`, persistido en `selected_target.txt`.

### Cambios por capa
- **LLM** (`services/llm.py`): pasar `target_lang`; sustituir "English" por `LANGUAGES[t]["name"]`
  en los prompts (conversación, ejercicios, traductor, significados); el few-shot del traductor por idioma.
- **STT** (`services/stt.py`): usar Whisper **multilingüe** (`small`/`medium`, no `.en`) cuando
  target≠en, y `transcribe(..., language=LANGUAGES[t]["whisper"])`.
- **TTS** (`services/tts.py`): `synthesize(text, lang=target)` elige la voz del mapa.
- **Traductor**: generalizar ES↔EN a **ES↔(idioma)**.
- **Pronunciación** (`services/pronunciation.py`): sustituir CMUdict por `phonemizer`(espeak-ng)
  para IPA en cualquier idioma; la comparación palabra-a-palabra ya es agnóstica.
- **DB** (`backend/db.py`): añadir columna `lang` a `stats`, `activity`, `missed`, `flashcards`
  y filtrar por el idioma activo. Migración: lo existente → `lang='en'`.
- **Backend** (`routers/*`): leer el idioma activo (runtime) y pasarlo a los services.
- **Frontend**: selector de "idioma a aprender" (junto al de nivel); Progreso por idioma.

### Dependencias nuevas
- `phonemizer` (pip) + **espeak-ng** (binario): el instalador lo añade
  (`winget install espeak-ng` / `apt install espeak-ng`).

### Plan por fases (sin romper lo actual; default = inglés)
1. **Núcleo**: `LANGUAGES` + `runtime.get_target()` + parametrizar LLM/STT/TTS/traductor.
2. **Progreso por idioma**: columna `lang` + migración + filtros.
3. **Frontend**: selector de idioma + progreso separado.
4. **IPA multi-idioma**: `phonemizer`+espeak en `pronunciation.py`; instalador añade espeak-ng.

### Archivos a tocar
`config.py` · `services/{runtime,llm,stt,tts,pronunciation}.py` · `backend/db.py` ·
`backend/routers/*` · `frontend/src/{api.ts,App.tsx,tabs/*}` · `install.ps1`/`install.sh` ·
`requirements.txt`.

---

## ⚠️ Nota sobre calidad del modelo
`qwen2.5:3b` es rápido pero comete fallos (alguna corrección/traducción rara). La arquitectura
es correcta; para **más calidad** sin perder mucha velocidad: `ollama pull qwen2.5:7b` y en
`config.py` `OLLAMA_MODEL = "qwen2.5:7b"`.
