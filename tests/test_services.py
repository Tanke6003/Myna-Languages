"""Tests de detección de idioma (TTS) y fonemas (pronunciación) — sin red ni modelos."""
from services import tts
from services import pronunciation as pron


def test_detect_lang_spanish():
    assert tts.detect_lang("Hola, ¿cómo estás?") == "es"
    assert tts.detect_lang("necesitas usar el pasado para esto") == "es"


def test_detect_lang_english():
    assert tts.detect_lang("I went to the store yesterday") == "en"
    assert tts.detect_lang("reliable") == "en"


def test_phonemes_known_word():
    p = pron.phonemes("hello")
    assert p is not None
    assert p["ipa"].startswith("/") and p["ipa"].endswith("/")
    assert "HH" in p["arpabet"] or "AH" in p["arpabet"]


def test_phonemes_unknown_word():
    assert pron.phonemes("zxqwv") is None


def test_transcribe_ipa_sentence():
    ipa = pron.transcribe_ipa("the cat")
    assert ipa.startswith("/") and ipa.endswith("/") and len(ipa) > 4


def test_phoneme_diff_th_to_s():
    # Clásico del hispanohablante: "think" /θ/ pronunciado como "sink" /s/.
    d = pron.phoneme_diff("think", "sink")
    assert d is not None
    subs = {(s["expected"], s["heard"]) for s in d["subs"]}
    assert ("/θ/", "/s/") in subs
    assert d["heard_ipa"] == "/sɪŋk/"
    assert d["score"] == 75          # 3 de 4 fonemas correctos


def test_phoneme_diff_no_data():
    assert pron.phoneme_diff("zxqwv", "anything") is None
    assert pron.phoneme_diff("think", "zxqwv") is None
