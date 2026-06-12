"""Evaluación de pronunciación local (aproximada, sin nube).

Idea: comparamos lo que el alumno *quería* decir (frase de referencia) con lo que
Whisper *entendió*. Si Whisper entiende bien la palabra, la pronunciación fue
inteligible; si la confunde o no la oye, suele indicar un problema de pronunciación.
Para cada palabra problemática mostramos sus fonemas (ARPAbet + IPA aproximado) para
que el alumno sepa cómo debería sonar, y la app genera el audio correcto.
"""
import difflib
import re
import string

from services.stt import transcribe

# --- Fonemas vía CMUdict (datos incluidos en el paquete, sin descargas) ---
_CMU = None


def _cmu():
    global _CMU
    if _CMU is None:
        try:
            import cmudict
            _CMU = cmudict.dict()
        except Exception as e:
            print(f"[PRON] cmudict no disponible ({e}); se omitirán los fonemas.")
            _CMU = {}
    return _CMU


# ARPAbet -> IPA (aproximado) para mostrar la pronunciación de forma legible.
_ARPA_IPA = {
    "AA": "ɑ", "AE": "æ", "AH": "ʌ", "AO": "ɔ", "AW": "aʊ", "AY": "aɪ",
    "B": "b", "CH": "tʃ", "D": "d", "DH": "ð", "EH": "ɛ", "ER": "ɝ",
    "EY": "eɪ", "F": "f", "G": "ɡ", "HH": "h", "IH": "ɪ", "IY": "i",
    "JH": "dʒ", "K": "k", "L": "l", "M": "m", "N": "n", "NG": "ŋ",
    "OW": "oʊ", "OY": "ɔɪ", "P": "p", "R": "ɹ", "S": "s", "SH": "ʃ",
    "T": "t", "TH": "θ", "UH": "ʊ", "UW": "u", "V": "v", "W": "w",
    "Y": "j", "Z": "z", "ZH": "ʒ",
}


def phonemes(word):
    """Devuelve {"arpabet": "...", "ipa": "..."} o None si la palabra no está en el diccionario."""
    entries = _cmu().get(word.lower())
    if not entries:
        return None
    arpa = entries[0]
    ipa = "".join(_ARPA_IPA.get(re.sub(r"\d", "", p), "") for p in arpa)
    return {"arpabet": " ".join(arpa), "ipa": f"/{ipa}/"}


def _arpa(word):
    """Lista de fonemas ARPAbet (sin marcas de acento) de una palabra, o None."""
    entries = _cmu().get(word.lower())
    if not entries:
        return None
    return [re.sub(r"\d", "", p) for p in entries[0]]


def _arpa_chunk(text):
    """Fonemas ARPAbet de una secuencia de palabras (lo que oyó Whisper)."""
    seq = []
    for w in _normalize(text):
        ph = _arpa(w)
        if ph:
            seq.extend(ph)
    return seq


def _ipa_sym(arpa_phon):
    """Un fonema ARPAbet -> su símbolo IPA (sin barras)."""
    return _ARPA_IPA.get(arpa_phon, arpa_phon.lower())


def phoneme_diff(ref_word, heard_text):
    """Alinea los fonemas que el alumno *debía* decir con los que Whisper *entendió*.

    Devuelve un dict con la alineación sonido a sonido, los sustituciones concretas a
    corregir (en IPA) y un % de acierto fonético; o None si no hay datos para comparar.
    """
    target = _arpa(ref_word)
    heard = _arpa_chunk(heard_text)
    if not target or not heard:
        return None

    matcher = difflib.SequenceMatcher(a=target, b=heard, autojunk=False)
    steps, subs, matched = [], [], 0
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for k in range(i1, i2):
                steps.append({"status": "ok", "expected": _ipa_sym(target[k]), "heard": _ipa_sym(target[k])})
            matched += (i2 - i1)
        elif tag == "replace":
            for off in range(max(i2 - i1, j2 - j1)):
                exp = target[i1 + off] if i1 + off < i2 else None
                got = heard[j1 + off] if j1 + off < j2 else None
                exp_i = _ipa_sym(exp) if exp else ""
                got_i = _ipa_sym(got) if got else ""
                steps.append({"status": "sub", "expected": exp_i, "heard": got_i})
                if exp:
                    subs.append({"expected": f"/{exp_i}/", "heard": f"/{got_i}/" if got_i else "—"})
        elif tag == "delete":          # sonidos que faltaron
            for k in range(i1, i2):
                steps.append({"status": "missing", "expected": _ipa_sym(target[k]), "heard": ""})
                subs.append({"expected": f"/{_ipa_sym(target[k])}/", "heard": "—"})
        elif tag == "insert":          # sonidos de más
            for k in range(j1, j2):
                steps.append({"status": "extra", "expected": "", "heard": _ipa_sym(heard[k])})

    score = round(100 * matched / max(len(target), 1))
    heard_ipa = "/" + "".join(_ipa_sym(p) for p in heard) + "/"
    return {"score": score, "heard_ipa": heard_ipa, "steps": steps, "subs": subs}


def transcribe_ipa(text):
    """Transcripción fonética IPA aproximada de una frase completa (para subtítulos)."""
    out = []
    for w in (text or "").split():
        clean = w.strip(string.punctuation + "¿¡“”‘’")
        ph = phonemes(clean) if clean else None
        out.append(ph["ipa"].strip("/") if ph else clean)
    return "/" + " ".join(out) + "/" if out else ""


def _normalize(text):
    out = []
    for w in (text or "").split():
        w = w.strip(string.punctuation + "¿¡“”‘’").lower()
        if w:
            out.append(w)
    return out


def assess_reading(reference, audio_path):
    """Compara la frase de referencia con la lectura del alumno.

    Devuelve un dict con la puntuación, lo que se entendió, el estado palabra a palabra
    y la lista de palabras problemáticas con sus fonemas.
    """
    result = transcribe(audio_path, word_timestamps=True)
    heard = result["text"]

    ref_words = _normalize(reference)
    hyp_words = _normalize(heard)

    matcher = difflib.SequenceMatcher(a=ref_words, b=hyp_words, autojunk=False)
    word_status = []
    matched = 0

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for k in range(i1, i2):
                word_status.append({"word": ref_words[k], "status": "ok"})
            matched += (i2 - i1)
        elif tag == "replace":
            heard_chunk = " ".join(hyp_words[j1:j2])
            for k in range(i1, i2):
                word_status.append({"word": ref_words[k], "status": "wrong", "heard": heard_chunk})
        elif tag == "delete":
            for k in range(i1, i2):
                word_status.append({"word": ref_words[k], "status": "missing"})
        # 'insert' = palabras de más que dijo el alumno; no penalizan la frase objetivo

    total = max(len(ref_words), 1)
    score = round(100 * matched / total)

    problems = [w for w in word_status if w["status"] != "ok"]
    for w in problems:
        w["phonemes"] = phonemes(w["word"])
        # Diff fonético: qué sonido concreto cambió respecto a lo que se entendió.
        w["sound_diff"] = phoneme_diff(w["word"], w.get("heard", "")) if w.get("heard") else None

    return {
        "score": score,
        "reference": reference,
        "heard": heard,
        "words": word_status,
        "problems": problems,
    }
