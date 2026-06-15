"""Cerebro del tutor: conversación, correcciones y ejercicios con Ollama (local).

Usamos un formato de texto por líneas (CLAVE: valor) en lugar de JSON: es más
robusto (el modelo no necesita escapar comillas) y más rápido de generar.
"""
import random
import re

import httpx
import ollama

from config import OLLAMA_KEEP_ALIVE, OLLAMA_NUM_PREDICT
from services import runtime

# Cliente con timeout: si el daemon de Ollama está caído o colgado, fallamos rápido
# en vez de quedarnos esperando para siempre. connect corto; read amplio (la generación
# en CPU puede tardar). NO se usa para pull (descarga larga), que va por el cliente normal.
_client = ollama.Client(timeout=httpx.Timeout(300.0, connect=10.0))

_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)


def _strip_think(text):
    """Quita bloques de razonamiento <think>...</think> que añaden algunos modelos."""
    return _THINK_RE.sub("", text or "").strip()


def _device_options(options):
    """Si el usuario forzó CPU en Ajustes, le decimos a Ollama que no use GPU."""
    if runtime.get_device() == "cpu":
        options["num_gpu"] = 0
    return options


def _chat(messages, temperature=0.7, num_predict=None):
    options = {"temperature": temperature}
    options["num_predict"] = num_predict or OLLAMA_NUM_PREDICT
    _device_options(options)
    kwargs = {
        "model": runtime.get_model(),  # modelo activo (configurable en runtime)
        "messages": messages,
        "options": options,
        "keep_alive": OLLAMA_KEEP_ALIVE,  # mantiene el modelo cargado (más rápido)
    }
    try:
        resp = _client.chat(think=False, **kwargs)  # qwen3: no "pensar en voz alta"
    except TypeError:
        # Cliente de ollama antiguo sin el parámetro `think`: reintenta sin él.
        resp = _client.chat(**kwargs)
    return _strip_think(resp["message"]["content"])


def _parse_fields(raw, repeatable=()):
    """Convierte 'CLAVE: valor' por líneas en un dict. Las claves en 'repeatable'
    se acumulan en una lista."""
    data = {}
    for line in (raw or "").splitlines():
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        key = key.strip().upper()
        val = val.strip()
        if not key:
            continue
        if key in repeatable:
            data.setdefault(key, []).append(val)
        else:
            data[key] = val
    return data


# ----------------------------------------------------------------------------
# 1) CONVERSACIÓN
# ----------------------------------------------------------------------------
_CONV_SYSTEM = (
    "You are a friendly but demanding English conversation tutor for a Spanish-speaking learner at "
    "CEFR level {level}. The learner wants to improve, so use vocabulary and structures appropriate "
    "to that level (do NOT oversimplify) and correct thoroughly. "
    "{scenario}"
    "Your REPLY must be written in ENGLISH (you are teaching English); keep it natural and short and "
    "end it with one follow-up question.\n\n"
    "Reply using EXACTLY this format, with these ENGLISH labels, one per line and nothing else:\n"
    "REPLY: <your English answer, ending with a question>\n"
    "CORRECTION: <wrong phrase> | <correct phrase> | <short explanation in SPANISH>\n"
    "TIP: <one short vocabulary tip in Spanish, or leave blank>\n"
    "SCORE: <integer 0-100 rating the learner's last message>\n\n"
    "Add one CORRECTION line for each real grammar/vocabulary mistake in the learner's last message "
    "(max 3); write no CORRECTION line if there were none. The explanations are in Spanish but the "
    "REPLY stays in English. NEVER treat proper nouns, people's names, places, or company/brand "
    "names as mistakes (leave them exactly as the learner said them). "
    "Never use double quotes; join two options with ' o '.\n\n"
    "For SCORE, rate the learner's LAST message from 0 to 100 for CEFR level {level}: reward effort, "
    "length and ambition, and judge by how SERIOUS the mistakes are, not how many. A longer attempt "
    "with small slips must score HIGHER than a short, safe one-word answer. A near-empty, off-topic "
    "or unintelligible message scores under 40; most genuine attempts land between 70 and 95.\n\n"
    "Example:\n"
    "REPLY: That sounds great! How long have you been working there?\n"
    "CORRECTION: I have work | I have worked | Usa el presente perfecto para hablar de experiencia.\n"
    "TIP: Puedes decir 'I've been working as a developer for 3 years'.\n"
    "SCORE: 82"
)


def _conv_messages(history_msgs, user_text, level, scenario=""):
    scen = (scenario + " ") if scenario else ""
    messages = [{"role": "system", "content": _CONV_SYSTEM.format(level=level, scenario=scen)}]
    messages += history_msgs[-12:]
    messages.append({"role": "user", "content": user_text})
    return messages


_CONV_FIELDS = ("REPLY", "CORRECTION", "TIP", "SCORE", "PRON", "VOCAB")


def _is_field_line(line):
    """¿La línea es un campo estructurado (REPLY:, CORRECTION:, ...) y no parte de la respuesta?"""
    head = line.split(":", 1)[0].strip().upper()
    return ":" in line and head in _CONV_FIELDS


def _clean_reply(text):
    """Corta cualquier etiqueta de campo que se haya colado en la MISMA línea de la respuesta
    (p. ej. 'I'll bring it. CORRECTION: ...') para no mostrar nunca la salida cruda."""
    up = text.upper()
    cut = len(text)
    for key in ("CORRECTION:", "TIP:", "SCORE:", "PRON:", "VOCAB:"):
        i = up.find(key)
        if i >= 0:
            cut = min(cut, i)
    return text[:cut].strip().strip('"').strip()


def parse_conversation_raw(raw):
    """Convierte la salida cruda del modelo en {reply, corrections, vocab_tip}."""
    fields = _parse_fields(raw, repeatable=("CORRECTION",))
    reply = _clean_reply(fields.get("REPLY", ""))
    if not reply:
        # El modelo no etiquetó la respuesta (o la dejó suelta tras los campos): toma SOLO las
        # líneas que NO son campos conocidos, para no volcar CORRECTION/TIP/SCORE en la burbuja.
        leftover = [ln.strip() for ln in (raw or "").splitlines()
                    if ln.strip() and not _is_field_line(ln)]
        reply = _clean_reply(" ".join(leftover))
    reply = reply or "Could you say that again, please?"

    # Red de seguridad: el tutor SIEMPRE responde en inglés.
    from services.tts import detect_lang
    if detect_lang(reply) == "es":
        reply = translate(reply, "ES→EN")

    corrections = []
    for c in fields.get("CORRECTION", []):
        parts = [p.strip() for p in c.split("|")]
        if len(parts) >= 2 and parts[0] and parts[1]:
            corrections.append({
                "original": parts[0],
                "correction": parts[1].replace(" / ", " o ").replace("/", " o "),
                "explanation": parts[2] if len(parts) > 2 else "",
            })
    score = None
    m = re.search(r"\d{1,3}", fields.get("SCORE", ""))
    if m:
        score = max(0, min(100, int(m.group())))
    return {"reply": reply, "corrections": corrections,
            "vocab_tip": fields.get("TIP", ""), "score": score}


def partial_reply(raw):
    """Extrae el texto del REPLY a medida que llega (para el streaming)."""
    i = raw.find("REPLY:")
    if i < 0:
        return ""
    rest = raw[i + 6:]
    nl = rest.find("\n")
    return (rest if nl < 0 else rest[:nl]).strip()


def conversation_turn(history_msgs, user_text, level, scenario=""):
    """Versión no-streaming: devuelve dict con reply/corrections/tip."""
    raw = _chat(_conv_messages(history_msgs, user_text, level, scenario), temperature=0.7)
    return parse_conversation_raw(raw)


def conversation_turn_stream(history_msgs, user_text, level, scenario=""):
    """Generador que produce el texto del modelo token a token (para SSE)."""
    messages = _conv_messages(history_msgs, user_text, level, scenario)
    options = _device_options({"temperature": 0.7, "num_predict": OLLAMA_NUM_PREDICT})
    kwargs = {"model": runtime.get_model(), "messages": messages, "options": options,
              "keep_alive": OLLAMA_KEEP_ALIVE, "stream": True}
    try:
        stream = _client.chat(think=False, **kwargs)
    except TypeError:
        stream = _client.chat(**kwargs)
    for chunk in stream:
        try:
            content = chunk["message"]["content"]
        except Exception:
            content = ""
        if content:
            yield content


def opening_question(level, scenario=""):
    """Una pregunta inicial para arrancar la conversación (opcionalmente en un escenario)."""
    scen = (scenario + " ") if scenario else ""
    messages = [
        {"role": "system", "content": f"You are an English tutor for a {level} Spanish-speaking "
                                       f"learner. {scen}Reply with ONE short, friendly opening "
                                       "question in English to start the conversation. "
                                       "Only the question, nothing else."},
        {"role": "user", "content": "Start the conversation."},
    ]
    return _chat(messages, temperature=0.9, num_predict=60).strip().strip('"')


# ----------------------------------------------------------------------------
# 2) EJERCICIO DE LECTURA / PRONUNCIACIÓN
# ----------------------------------------------------------------------------
# Calibración de dificultad por nivel CEFR. Cada descriptor marca tanto el suelo
# (no trivial) como el TECHO del nivel (qué NO usar), para que el modelo no se pase
# (p. ej. dar una frase C1 cuando pediste B1).
_CEFR_GUIDE = {
    "A1": "8-10 words. Present simple only, the ~1000 most frequent words, concrete everyday topics. "
          "AVOID past/perfect/conditional tenses, subordinate clauses, and any abstract or technical word.",
    "A2": "10-13 words. Simple past and 'going to' future, basic connectors (and, but, because), "
          "everyday concrete topics. AVOID perfect/conditional tenses and low-frequency or technical vocabulary.",
    "B1": "12-16 words. At most one subordinate clause; present perfect and simple conditionals are OK. "
          "Use common, everyday vocabulary. AVOID academic/technical terms, low-frequency words and heavy "
          "noun phrases or nominalizations (e.g. 'the discovery of X greatly expands our understanding of Y' "
          "is B2/C1, NOT B1).",
    "B2": "16-20 words. Complex sentences, passive voice, a good range of connectors, more abstract topics, "
          "precise but still general vocabulary. AVOID rare, literary or highly specialized terms.",
    "C1": "18-24 words. Sophisticated structures, idiomatic and lower-frequency vocabulary, abstract and "
          "nuanced ideas.",
    "C2": "20-28 words. Near-native: nuanced, idiomatic, stylistically rich and precise.",
}
_CEFR_ERRORS = {"A1": "1", "A2": "1-2", "B1": "2-3", "B2": "3", "C1": "3-4", "C2": "4"}


def _cefr_guide(level):
    """Instrucción de calibración: apunta a la parte ALTA del nivel sin SOBREPASARLO."""
    g = _CEFR_GUIDE.get(level, _CEFR_GUIDE["B2"])
    return (f"Target CEFR level {level} precisely: {g} "
            f"Stay WITHIN {level}: do not exceed it (no vocabulary or grammar above {level}) and do not "
            f"trivialize it (aim for the upper part of {level}, not the lower).")

# Temas para dar variedad (evita que se repitan siempre las mismas frases)
_THEMES = ["travel", "food", "work", "family", "technology", "sports", "weather", "shopping",
           "health", "music", "nature", "daily routine", "movies", "science", "history", "animals",
           "city life", "hobbies", "friendship", "the future", "education", "money", "cooking",
           "the ocean", "space", "art", "gardening", "festivals", "transport", "the news"]


def _theme(topic):
    return topic.strip() if (topic and topic.strip()) else random.choice(_THEMES)


def reading_sentence(level, topic=""):
    """Genera una frase en inglés para leer en voz alta, calibrada al nivel CEFR."""
    theme = _theme(topic)
    messages = [
        {"role": "system", "content": "You generate ONE English sentence for a learner to read aloud. "
                                       + _cefr_guide(level) +
                                       f" The topic is {theme}. Be creative and avoid clichés. "
                                       "Reply with ONLY the sentence, no quotes."},
        {"role": "user", "content": f"Give me a {level} sentence about {theme}."},
    ]
    return _chat(messages, temperature=0.9, num_predict=80).strip().strip('"')


def reading_feedback(reference, heard, problem_words, score, level):
    """Comentario breve, honesto y exigente (en español) sobre la lectura del alumno."""
    parts = []
    for w in problem_words:
        sd = w.get("sound_diff") or {}
        subs = sd.get("subs") or []
        if subs:
            detail = "; ".join(f"{s['expected']}→{s['heard']}" for s in subs[:3])
            parts.append(f"{w['word']} (sonidos {detail})")
        else:
            parts.append(w["word"])
    problems = ", ".join(parts) or "ninguna"
    messages = [
        {"role": "system", "content": "You are a demanding but supportive English pronunciation "
                                       f"coach for a Spanish speaker at CEFR level {level}. The "
                                       "learner wants to IMPROVE, so be honest: if it was easy or "
                                       "below their level, say so and push them higher; never "
                                       "over-praise. Point out a concrete thing to work on. Reply "
                                       "in Spanish, max 3 sentences."},
        {"role": "user", "content": f"Frase objetivo: '{reference}'.\nLo que se entendió: "
                                     f"'{heard}'.\nPuntuación: {score}/100. Palabras con problemas: "
                                     f"{problems}. Da un comentario honesto y un consejo concreto."},
    ]
    return _chat(messages, temperature=0.5, num_predict=160)


# ----------------------------------------------------------------------------
# 3) EJERCICIO DE CORREGIR TEXTO
# ----------------------------------------------------------------------------
def text_with_errors(level):
    """Genera una frase en inglés con errores para corregir, calibrada al nivel CEFR."""
    n = _CEFR_ERRORS.get(level, "3")
    theme = _theme("")
    messages = [
        {"role": "system", "content": f"Write ONE English sentence about {theme} that contains exactly "
                                       f"{n} deliberate, realistic mistakes (verb tense, agreement, "
                                       "articles, prepositions, word order or collocations). At higher "
                                       "levels the mistakes must be SUBTLE, not obvious. "
                                       + _cefr_guide(level) +
                                       " Be varied. Reply with ONLY the incorrect sentence, no quotes."},
        {"role": "user", "content": f"Give me a {level} sentence about {theme} with mistakes."},
    ]
    return _chat(messages, temperature=1.0, num_predict=80).strip().strip('"')


def check_correction(original_with_errors, user_correction):
    """Evalúa la corrección que escribió el alumno."""
    messages = [
        {"role": "system", "content": "You check a learner's correction of an English sentence. "
                                       "Reply using EXACTLY this format, no quotes, no extra text:\n"
                                       "RESULT: correct OR incorrect\n"
                                       "FIXED: <the fully correct sentence>\n"
                                       "FEEDBACK: <explanation in SPANISH>"},
        {"role": "user", "content": f"Original (with mistakes): {original_with_errors}\n"
                                     f"Learner's correction: {user_correction}"},
    ]
    raw = _chat(messages, temperature=0.3, num_predict=200)
    f = _parse_fields(raw)
    result = f.get("RESULT", "").lower()
    return {
        "correct": result.startswith("correct") or "correcto" in result,
        "fixed": f.get("FIXED", ""),
        "feedback": f.get("FEEDBACK", raw),
    }


# ----------------------------------------------------------------------------
# 4) EJERCICIOS DE VOCABULARIO / GRAMÁTICA (opción múltiple)
# ----------------------------------------------------------------------------
def _multiple_choice(system, user, temperature=0.8):
    raw = _chat([{"role": "system", "content": system}, {"role": "user", "content": user}],
                temperature=temperature, num_predict=250)
    f = _parse_fields(raw)
    options = [o.strip() for o in f.get("OPTIONS", "").split("|") if o.strip()]
    answer = f.get("ANSWER", "").strip()
    if answer and answer not in options:
        options.append(answer)
    if len(options) > 4:  # salvaguarda: como máximo 4, garantizando la respuesta
        keep = [o for o in options if o == answer][:1]
        for o in options:
            if len(keep) >= 4:
                break
            if o not in keep:
                keep.append(o)
        options = keep
    return {
        "prompt": f.get("PROMPT", ""),
        "question": f.get("QUESTION", ""),
        "options": options,
        "answer": answer,
        "explain": f.get("EXPLAIN", ""),
    }


# Especificaciones de cada tipo de ejercicio de vocabulario (opción múltiple, en inglés)
_VOCAB_SPECS = {
    "tense": {
        "intro": "Create a verb-tense identification exercise",
        "prompt": "<an English sentence that clearly uses one verb tense>",
        "question": "Which verb tense is the main verb in?",
        "extra": "Use ENGLISH tense names (Present Simple, Past Simple, Present Continuous, Past "
                 "Continuous, Future Simple, Present Perfect, Past Perfect).",
    },
    "synonym": {
        "intro": "Create an English synonym exercise",
        "prompt": "<one English target word>",
        "question": "Choose the correct synonym",
        "extra": "The target word must NOT appear in OPTIONS. Exactly one option is a real synonym; "
                 "the other three are plausible distractors that are NOT synonyms.",
    },
    "antonym": {
        "intro": "Create an English antonym (opposite) exercise",
        "prompt": "<one English target word>",
        "question": "Choose the correct antonym (opposite)",
        "extra": "The target word must NOT appear in OPTIONS. Exactly one option is a real opposite; "
                 "the other three are NOT opposites.",
    },
    "preposition": {
        "intro": "Create an English preposition gap-fill exercise",
        "prompt": "<an English sentence with one blank shown as ___ where a preposition is missing>",
        "question": "Choose the correct preposition for the blank",
        "extra": "Each option is a single preposition and only one is correct in the sentence.",
    },
    "phrasal": {
        "intro": "Create an English phrasal-verb gap-fill exercise",
        "prompt": "<an English sentence with one blank shown as ___ where a phrasal verb is missing>",
        "question": "Choose the phrasal verb that best fits the blank",
        "extra": "Each option is a phrasal verb and only one fits the meaning.",
    },
}


def vocab_exercise(level, kind, avoid=()):
    """Genera un ejercicio de vocabulario de opción múltiple del tipo indicado.

    avoid: palabras/frases objetivo recientes a NO reutilizar (las pasa el router a partir de
    lo ya visto). Junto con un tema aleatorio evita que salgan SIEMPRE las mismas palabras
    (un modelo pequeño tiende a las más comunes si no se le empuja a variar).
    """
    s = _VOCAB_SPECS.get(kind, _VOCAB_SPECS["synonym"])
    theme = _theme("")
    variety = (f"Base the exercise on the topic of {theme} to keep it VARIED (do not always reuse "
               "the same few common words; prefer fresh, less predictable target words). ")
    if avoid:
        variety += ("Do NOT use any of these recent target words — pick a clearly different one: "
                    + ", ".join(list(avoid)[:20]) + ". ")
    system = (
        f"{s['intro']} {_cefr_guide(level)} {variety}Make the distractors non-obvious and plausible. "
        "Reply using EXACTLY this format, no quotes, no extra text:\n"
        f"PROMPT: {s['prompt']}\n"
        f"QUESTION: {s['question']}\n"
        "OPTIONS: <opt1> | <opt2> | <opt3> | <opt4>\n"
        "ANSWER: <the correct option, exactly as in OPTIONS>\n"
        "EXPLAIN: <short explanation in Spanish>\n"
        "All OPTIONS are written in English. OPTIONS must contain EXACTLY 4 items separated by "
        "' | '. ANSWER must be one of those 4 and must be the truly correct one, consistent with "
        "EXPLAIN. " + s["extra"]
    )
    return _multiple_choice(system, f"Generate the exercise about {theme}.")


def meaning_exercise(word):
    """Opción múltiple: ¿qué significa (en español) la palabra/frase inglesa dada?"""
    system = (
        "Create a 'what does this English word mean in Spanish?' multiple-choice question. "
        "Reply EXACTLY like this, nothing else:\n"
        "OPTIONS: <correct Spanish meaning> | <wrong> | <wrong> | <wrong>\n"
        "ANSWER: <the correct one, exactly as in OPTIONS>\n"
        "EXPLAIN: <short Spanish explanation>\n"
        "OPTIONS must have EXACTLY 4 short Spanish meanings (1-3 words) separated by ' | '; "
        "only one is correct.\n\n"
        "Example for 'reliable':\n"
        "OPTIONS: fiable | ruidoso | barato | lejano\n"
        "ANSWER: fiable\n"
        "EXPLAIN: 'reliable' significa fiable o de confianza."
    )
    raw = _chat([{"role": "system", "content": system}, {"role": "user", "content": word}],
                temperature=0.6, num_predict=200)
    f = _parse_fields(raw)
    options = [o.strip() for o in f.get("OPTIONS", "").split("|") if o.strip()]
    answer = f.get("ANSWER", "").strip()
    if answer and answer not in options:
        options.append(answer)
    if len(options) > 4:
        keep = [answer] if answer else []
        for o in options:
            if len(keep) >= 4:
                break
            if o not in keep:
                keep.append(o)
        options = keep
    random.shuffle(options)
    return {"options": options, "answer": answer, "explain": f.get("EXPLAIN", "")}


def minimal_pairs_exercise(level, avoid=()):
    """Pares mínimos: una palabra objetivo + palabras que suenan parecido (p. ej. lived/left/live).

    Se reproduce el audio de la palabra objetivo y el alumno elige cuál era entre opciones
    fácilmente confundibles por sonido. avoid: palabras objetivo recientes a no repetir.
    """
    theme = _theme("")
    extra = f"Loosely relate the target word to the topic of {theme} for variety. "
    if avoid:
        extra += "Do NOT use any of these recent target words: " + ", ".join(list(avoid)[:20]) + ". "
    level_hint = ("Use very common, short words" if level in ("A1", "A2")
                  else "Common words are best; less frequent ones are fine at C1/C2")
    system = (
        "Create a minimal-pair LISTENING exercise for a Spanish-speaking English learner. "
        "Pick ONE English target word, then 3 OTHER real English words that sound very similar and "
        "are easily confused with it (differ by a single vowel or consonant sound — e.g. "
        "lived/left/leave/leaf, ship/sheep/cheap/chip, bad/bed/bat/bet). "
        f"{level_hint} for CEFR {level}. {extra}"
        "Reply using EXACTLY this format, no quotes, no extra text:\n"
        "WORD: <the target word that will be played as audio>\n"
        "OPTIONS: <opt1> | <opt2> | <opt3> | <opt4>\n"
        "EXPLAIN: <short explanation in SPANISH of the sound contrast and how to tell them apart>\n"
        "OPTIONS must contain EXACTLY 4 real, distinct English words INCLUDING the target word, "
        "separated by ' | '. Every option must be genuinely confusable by sound with the target."
    )
    raw = _chat([{"role": "system", "content": system},
                 {"role": "user", "content": f"Generate the exercise about {theme}."}],
                temperature=0.9, num_predict=160)
    f = _parse_fields(raw)
    word = f.get("WORD", "").strip().strip('"')
    word = word.split()[0] if word else ""
    options = [o.strip().strip('"') for o in f.get("OPTIONS", "").split("|")]
    options = [o for o in options if o]
    lower = [o.lower() for o in options]
    if word and word.lower() not in lower:  # garantiza que la palabra objetivo esté entre opciones
        options.insert(0, word)
    if len(options) > 4:  # recorta a 4 conservando la palabra objetivo
        keep = [word] if word else []
        for o in options:
            if len(keep) >= 4:
                break
            if o.lower() not in [k.lower() for k in keep]:
                keep.append(o)
        options = keep
    if not word and options:
        word = options[0]
    random.shuffle(options)
    return {"word": word, "options": options, "answer": word, "explain": f.get("EXPLAIN", "")}


def listening_exercise(level):
    """Genera un pasaje corto en inglés (para escuchar) y una pregunta de comprensión."""
    system = (
        "Create a short English listening-comprehension exercise. "
        f"{_cefr_guide(level)} The passage and question must match that level. "
        "Reply using EXACTLY this format, no quotes, no extra text:\n"
        "PASSAGE: <2-3 natural English sentences to be read aloud>\n"
        "QUESTION: <one comprehension question in English about the passage>\n"
        "OPTIONS: <opt1> | <opt2> | <opt3> | <opt4>\n"
        "ANSWER: <the correct option, exactly as in OPTIONS>\n"
        "EXPLAIN: <short explanation in Spanish>\n"
        "QUESTION, OPTIONS and ANSWER are ALL in English. OPTIONS must contain EXACTLY 4 items "
        "separated by ' | '. ANSWER must be one of them."
    )
    raw = _chat([{"role": "system", "content": system},
                 {"role": "user", "content": "Generate the exercise."}],
                temperature=0.8, num_predict=400)
    f = _parse_fields(raw)
    options = [o.strip(" |,\t") for o in f.get("OPTIONS", "").split("|")]
    options = [o for o in options if o]
    answer = f.get("ANSWER", "").strip(" |,\t")
    if answer and answer not in options:
        options.append(answer)
    if len(options) > 4:
        keep = [o for o in options if o == answer][:1]
        for o in options:
            if len(keep) >= 4:
                break
            if o not in keep:
                keep.append(o)
        options = keep
    return {"passage": f.get("PASSAGE", ""), "question": f.get("QUESTION", ""),
            "options": options, "answer": answer, "explain": f.get("EXPLAIN", "")}


# ----------------------------------------------------------------------------
# 4b) CONCEPTOS / EXPRESIONES (practicar TU lista de expresiones)
# ----------------------------------------------------------------------------
def _concept_tag(phrase, meaning):
    """Etiqueta legible de la expresión con su significado (si lo hay), para el prompt."""
    return f"'{phrase}'" + (f" (meaning: {meaning})" if meaning else "")


def concept_gap(phrase, meaning, level):
    """Frase NUEVA con un hueco (___) donde va la expresión; el alumno la escribe."""
    system = (
        f"Create a gap-fill exercise to practice the English expression {_concept_tag(phrase, meaning)}. "
        "Write ONE natural English sentence in a FRESH context that uses the expression, then replace "
        "ONLY the expression with ___ (a single blank). " + _cefr_guide(level) +
        " Reply using EXACTLY this format, no quotes, no extra text:\n"
        "PROMPT: <the sentence with one ___ where the expression goes>\n"
        "ANSWER: <only the words that fill the blank: the expression, inflected/conjugated to fit>\n"
        "EXPLAIN: <short explanation in SPANISH of its meaning and how it is used>\n"
        "The blank ___ must stand exactly where the expression belongs and appear once. "
        "ANSWER is ONLY the missing words, never the whole sentence."
    )
    raw = _chat([{"role": "system", "content": system},
                 {"role": "user", "content": "Generate the exercise."}],
                temperature=0.8, num_predict=220)
    f = _parse_fields(raw)
    prompt = f.get("PROMPT", "").strip()
    answer = f.get("ANSWER", "").strip().strip('"') or phrase
    if "___" not in prompt:  # red de seguridad: si el modelo no dejó el hueco, no es usable
        prompt = f"___ — {prompt}".strip(" —") or f"Use the expression: ___"
    return {"prompt": prompt, "answer": answer, "explain": f.get("EXPLAIN", "")}


def concept_choice(phrase, meaning, level):
    """Opción múltiple: frase con hueco + 4 opciones (la expresión + 3 distractores)."""
    system = (
        f"Create a multiple-choice gap-fill to practice the English expression "
        f"{_concept_tag(phrase, meaning)}. Write ONE natural English sentence with a single blank ___ "
        "where the expression fits, and 4 options where EXACTLY ONE is correct (the target expression, "
        "correctly inflected) and the other 3 are plausible but wrong similar expressions or phrasal "
        "verbs. " + _cefr_guide(level) +
        " Reply using EXACTLY this format, no quotes, no extra text:\n"
        "PROMPT: <the sentence with one ___>\n"
        "QUESTION: Which option best fits the blank?\n"
        "OPTIONS: <opt1> | <opt2> | <opt3> | <opt4>\n"
        "ANSWER: <the correct option, exactly as in OPTIONS>\n"
        "EXPLAIN: <short explanation in SPANISH>\n"
        "OPTIONS must contain EXACTLY 4 items separated by ' | '. ANSWER must be one of them and must "
        "be the target expression."
    )
    return _multiple_choice(system, "Generate the exercise.")


def concept_check(phrase, sentence):
    """Evalúa una frase escrita por el alumno que debe usar la expresión dada."""
    system = (
        f"You check whether a learner correctly used the English expression '{phrase}' in their own "
        "sentence. Reply using EXACTLY this format, no quotes, no extra text:\n"
        "RESULT: correct OR incorrect\n"
        "BETTER: <a corrected or more natural version of their sentence (or the same if already good)>\n"
        "FEEDBACK: <short explanation in SPANISH: did they use the expression well, and what to improve>\n"
        "Mark it incorrect if the expression is missing, misused, or the sentence is ungrammatical."
    )
    raw = _chat([{"role": "system", "content": system},
                 {"role": "user", "content": f"Expression: {phrase}\nLearner's sentence: {sentence}"}],
                temperature=0.3, num_predict=220)
    f = _parse_fields(raw)
    result = f.get("RESULT", "").lower()
    # Confiamos en el juicio del modelo (ya tiene orden de marcar incorrecto si falta la
    # expresión); no comparamos por substring porque la expresión suele ir conjugada
    # (p. ej. 'come up with' → 'came up with') y daría falsos negativos.
    correct = result.startswith("correct") or "correcto" in result
    return {"correct": correct, "better": f.get("BETTER", ""),
            "feedback": f.get("FEEDBACK", raw)}


# ----------------------------------------------------------------------------
# 4d) ESCRITURA (reescribir / traducir / completar / redacción)
# ----------------------------------------------------------------------------
def _writing_variety(theme, avoid):
    s = f"Center it on the topic of {theme} to keep it varied. "
    if avoid:
        s += "Do NOT reuse any of these recent ones: " + " / ".join(list(avoid)[:12]) + ". "
    return s


def writing_exercise(level, kind, avoid=()):
    """Genera un ejercicio de escritura: rewrite / translate / complete / paragraph."""
    theme = _theme("")
    var = _writing_variety(theme, avoid)
    if kind == "translate":
        system = ("Create a Spanish-to-English translation writing exercise. Write ONE natural "
                  f"SPANISH sentence for a {level} learner to translate into English. "
                  + _cefr_guide(level) + " " + var +
                  "Reply with EXACTLY one line:\nSENTENCE: <the Spanish sentence>")
    elif kind == "complete":
        system = ("Create a sentence-completion writing exercise. Write the BEGINNING of an English "
                  "sentence that the learner must finish (conditionals, linkers, time clauses, etc.). "
                  f"Target CEFR {level}. " + var +
                  "Reply with EXACTLY one line:\nSENTENCE: <the sentence beginning, ending where the "
                  "learner continues, e.g. 'If I had more time, '>")
    elif kind == "paragraph":
        system = ("Create a short-writing prompt. Give ONE clear topic or question for a "
                  f"{level} learner to write 2-3 English sentences about. " + var +
                  "Reply with EXACTLY one line:\nTOPIC: <the topic or question in English>")
    else:  # rewrite
        kind = "rewrite"
        system = ("Create an English sentence-transformation exercise. Write ONE correct English "
                  "sentence and an instruction to rewrite it keeping the SAME meaning (use a given "
                  "linker like despite/although/however, change to passive voice, use 'used to', make "
                  "it more formal, or a key-word transformation). " + _cefr_guide(level) + " " + var +
                  "Reply with EXACTLY two lines:\n"
                  "SENTENCE: <the original English sentence>\n"
                  "INSTRUCTION: <short instruction in SPANISH on how to rewrite it; put any English "
                  "keyword in quotes>")
    raw = _chat([{"role": "system", "content": system},
                 {"role": "user", "content": f"Generate the exercise about {theme}."}],
                temperature=0.9, num_predict=160)
    f = _parse_fields(raw)
    prompt = (f.get("SENTENCE") or f.get("TOPIC") or f.get("PROMPT") or "").strip()
    instruction = f.get("INSTRUCTION", "").strip()
    if not prompt:
        # El modelo a veces ignora el prefijo "SENTENCE:/TOPIC:" y devuelve el enunciado
        # directo (a veces con un '>' que se cuela de la plantilla <...>). Usamos como
        # enunciado la primera línea con contenido para no dejar el ejercicio vacío.
        for line in (raw or "").splitlines():
            cand = line.strip()
            if cand.upper().startswith("INSTRUCTION"):
                continue
            cand = re.sub(r"^(SENTENCE|TOPIC|PROMPT)\s*:", "", cand, flags=re.I).strip()
            cand = cand.strip("<>").strip().strip('"').strip()
            if cand:
                prompt = cand
                break
    prompt = prompt.strip('"').strip()
    return {"kind": kind, "prompt": prompt, "instruction": instruction}


def writing_check(kind, prompt, instruction, answer, level=""):
    """Evalúa lo que escribió el alumno. Devuelve {correct, score, better, feedback}."""
    fmt = ("Reply using EXACTLY this format, no extra text:\n"
           "RESULT: correct OR incorrect\n"
           "SCORE: <integer 0-100>\n"
           "BETTER: <a correct, natural model version>\n"
           "FEEDBACK: <short explanation in SPANISH>")
    if kind == "translate":
        system = ("You check a Spanish-to-English translation. Judge whether the ENGLISH is a correct "
                  "and natural translation of the SPANISH. " + fmt)
        user = f"SPANISH: {prompt}\nLEARNER (English): {answer}"
    elif kind == "complete":
        system = ("You check a sentence the learner completed. Judge whether the FULL sentence is "
                  "grammatical, natural and meaningful (it must start with the given BEGINNING). " + fmt)
        user = f"BEGINNING: {prompt}\nLEARNER (full sentence): {answer}"
    elif kind == "paragraph":
        system = (f"You evaluate a short piece of writing (2-3 sentences) on the TOPIC for CEFR {level}. "
                  "Judge grammar, vocabulary and whether it answers the topic. " + fmt +
                  " FEEDBACK should include the main correction(s) and one tip.")
        user = f"TOPIC: {prompt}\nLEARNER: {answer}"
    else:  # rewrite
        system = ("You check a sentence-transformation. The learner rewrote the ORIGINAL following the "
                  "INSTRUCTION. It must keep the SAME meaning, follow the instruction and be correct. " + fmt)
        user = f"ORIGINAL: {prompt}\nINSTRUCTION: {instruction}\nLEARNER: {answer}"
    raw = _chat([{"role": "system", "content": system}, {"role": "user", "content": user}],
                temperature=0.3, num_predict=260)
    f = _parse_fields(raw)
    result = f.get("RESULT", "").lower()
    correct = result.startswith("correct") or "correcto" in result
    score = None
    m = re.search(r"\d{1,3}", f.get("SCORE", ""))
    if m:
        score = max(0, min(100, int(m.group())))
    return {"correct": correct, "score": score, "better": f.get("BETTER", ""),
            "feedback": f.get("FEEDBACK", raw)}


# ----------------------------------------------------------------------------
# 5) TRADUCTOR
# ----------------------------------------------------------------------------
def translate(text, direction="Auto", note=""):
    """Traduce entre español e inglés. direction: 'Auto', 'ES→EN' o 'EN→ES'.

    note: instrucción extra del usuario para rebatir/ajustar (p. ej. "Jabil es un
    nombre de empresa, no lo traduzcas").
    """
    if direction == "ES→EN":
        system = "You are a translator. Translate the user's message into English. Output ONLY the English translation."
        shot = ("Trabajo en Microsoft como ingeniero", "I work at Microsoft as an engineer.")
    elif direction == "EN→ES":
        system = "You are a translator. Translate the user's message into Spanish. Output ONLY the Spanish translation."
        shot = ("I work at Microsoft as an engineer", "Trabajo en Microsoft como ingeniero.")
    else:
        system = ("You are a translator between Spanish and English. If the message is Spanish, "
                  "output its English translation; if it is English, output its Spanish "
                  "translation. Output ONLY the translation.")
        shot = ("Trabajo en Microsoft como ingeniero", "I work at Microsoft as an engineer.")
    system += " Keep names of people, places and companies unchanged."
    if note and note.strip():
        system += f" Note about specific words (translate everything else normally): {note.strip()}"
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": shot[0]},
        {"role": "assistant", "content": shot[1]},
        {"role": "user", "content": text},
    ]
    return _chat(messages, temperature=0.2, num_predict=300).strip().strip('"')


def word_meaning(word):
    """Significado en español de una palabra/frase inglesa (para el reverso de flashcards)."""
    msgs = [
        {"role": "system", "content": "You give the Spanish meaning of an English word or phrase. "
                                       "Output ONLY the Spanish meaning (1-4 words), nothing else."},
        {"role": "user", "content": "reliable"},
        {"role": "assistant", "content": "fiable, confiable"},
        {"role": "user", "content": "to give up"},
        {"role": "assistant", "content": "rendirse, abandonar"},
        {"role": "user", "content": word},
    ]
    return _chat(msgs, temperature=0.2, num_predict=40).strip().strip('"')


def translation_details(english_text):
    """Para una palabra/frase EN inglés: sinónimos y ejemplos sencillos (con su español)."""
    system = (
        "Give synonyms and example sentences for the English word or phrase. "
        "Reply EXACTLY like this, one item per line, nothing else:\n"
        "SYNONYMS: word1, word2, word3\n"
        "EX: <one simple English sentence> | <its Spanish translation>\n"
        "EX: <another simple English sentence> | <its Spanish translation>\n\n"
        "Example for the word 'happy':\n"
        "SYNONYMS: glad, cheerful, content\n"
        "EX: She felt happy at the party. | Se sintió feliz en la fiesta.\n"
        "EX: They are happy together. | Están felices juntos."
    )
    raw = _chat([{"role": "system", "content": system},
                 {"role": "user", "content": english_text}], temperature=0.4, num_predict=220)
    f = _parse_fields(raw, repeatable=("EX",))
    synonyms = [s.strip() for s in f.get("SYNONYMS", "").replace("|", ",").split(",")]
    synonyms = list(dict.fromkeys(s for s in synonyms if s and s != "-"))  # sin duplicados
    examples = []
    for e in f.get("EX", []):
        en, es = e, ""
        for sep in (" | ", "::", " = ", "|"):
            if sep in e:
                en, es = e.split(sep, 1)
                break
        en, es = en.strip(), es.strip()
        if en:
            examples.append({"en": en, "es": es})
    return {"word": english_text, "synonyms": synonyms, "examples": examples}


