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


def _chat(messages, temperature=0.7, num_predict=None):
    options = {"temperature": temperature}
    options["num_predict"] = num_predict or OLLAMA_NUM_PREDICT
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
    "TIP: <one short vocabulary tip in Spanish, or leave blank>\n\n"
    "Add one CORRECTION line for each real grammar/vocabulary mistake in the learner's last message "
    "(max 3); write no CORRECTION line if there were none. The explanations are in Spanish but the "
    "REPLY stays in English. NEVER treat proper nouns, people's names, places, or company/brand "
    "names as mistakes (leave them exactly as the learner said them). "
    "Never use double quotes; join two options with ' o '.\n\n"
    "Example:\n"
    "REPLY: That sounds great! How long have you been working there?\n"
    "CORRECTION: I have work | I have worked | Usa el presente perfecto para hablar de experiencia.\n"
    "TIP: Puedes decir 'I've been working as a developer for 3 years'."
)


def _conv_messages(history_msgs, user_text, level, scenario=""):
    scen = (scenario + " ") if scenario else ""
    messages = [{"role": "system", "content": _CONV_SYSTEM.format(level=level, scenario=scen)}]
    messages += history_msgs[-12:]
    messages.append({"role": "user", "content": user_text})
    return messages


def parse_conversation_raw(raw):
    """Convierte la salida cruda del modelo en {reply, corrections, vocab_tip}."""
    fields = _parse_fields(raw, repeatable=("CORRECTION",))
    reply = fields.get("REPLY") or raw.strip() or "Could you say that again, please?"

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
    return {"reply": reply, "corrections": corrections, "vocab_tip": fields.get("TIP", "")}


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
    options = {"temperature": 0.7, "num_predict": OLLAMA_NUM_PREDICT}
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
# Calibración de dificultad por nivel CEFR (apuntando al extremo alto del nivel)
_CEFR_READING = {
    "A1": "6-8 words, simple present, very high-frequency words",
    "A2": "9-12 words, everyday topics, common past or future tense",
    "B1": "13-16 words, including a subordinate clause and some less common vocabulary",
    "B2": "16-20 words, complex structure and varied, precise vocabulary",
    "C1": "20-25 words, sophisticated structures and idiomatic, low-frequency vocabulary",
    "C2": "22-28 words, near-native: nuanced, idiomatic and stylistically rich",
}
_CEFR_ERRORS = {"A1": "1", "A2": "1-2", "B1": "2-3", "B2": "3", "C1": "3-4", "C2": "4"}

# Temas para dar variedad (evita que se repitan siempre las mismas frases)
_THEMES = ["travel", "food", "work", "family", "technology", "sports", "weather", "shopping",
           "health", "music", "nature", "daily routine", "movies", "science", "history", "animals",
           "city life", "hobbies", "friendship", "the future", "education", "money", "cooking",
           "the ocean", "space", "art", "gardening", "festivals", "transport", "the news"]


def _theme(topic):
    return topic.strip() if (topic and topic.strip()) else random.choice(_THEMES)


def reading_sentence(level, topic=""):
    """Genera una frase en inglés para leer en voz alta, calibrada al nivel CEFR."""
    diff = _CEFR_READING.get(level, _CEFR_READING["B2"])
    theme = _theme(topic)
    messages = [
        {"role": "system", "content": "You generate ONE English sentence for a learner to read "
                                       f"aloud, calibrated to CEFR level {level}: make it {diff}. "
                                       f"The topic is {theme}. Aim for the HARDER end of the level — "
                                       "never make it easier than the level. Be creative and avoid "
                                       "clichés. Reply with ONLY the sentence, no quotes."},
        {"role": "user", "content": f"Give me a {level} sentence about {theme}."},
    ]
    return _chat(messages, temperature=1.0, num_predict=80).strip().strip('"')


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
        {"role": "system", "content": f"Write ONE English sentence about {theme} at CEFR level "
                                       f"{level} that contains exactly {n} deliberate, realistic "
                                       "mistakes (verb tense, agreement, articles, prepositions, "
                                       "word order or collocations). At higher levels the mistakes "
                                       "must be SUBTLE, not obvious. Use vocabulary and structures "
                                       f"true to the level — do not make it easier than {level}. "
                                       "Be varied. Reply with ONLY the incorrect sentence, no quotes."},
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


def vocab_exercise(level, kind):
    """Genera un ejercicio de vocabulario de opción múltiple del tipo indicado."""
    s = _VOCAB_SPECS.get(kind, _VOCAB_SPECS["synonym"])
    system = (
        f"{s['intro']} calibrated to CEFR level {level}; make it genuinely challenging for that "
        "level (non-obvious, plausible distractors), not trivial. "
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
    return _multiple_choice(system, "Generate the exercise.")


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


def listening_exercise(level):
    """Genera un pasaje corto en inglés (para escuchar) y una pregunta de comprensión."""
    system = (
        f"Create a short English listening-comprehension exercise calibrated to CEFR level {level}; "
        "make it genuinely at that level, not trivial. "
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


