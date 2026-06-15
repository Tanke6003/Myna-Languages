"""Tests del parseo de las respuestas del LLM (funciones puras, sin llamar a Ollama)."""
from services import llm


def test_parse_fields_basic():
    raw = "REPLY: Hi there\nCORRECTION: I has | I have | concordancia\nTIP: usa el plural"
    f = llm._parse_fields(raw, repeatable=("CORRECTION",))
    assert f["REPLY"] == "Hi there"
    assert f["CORRECTION"] == ["I has | I have | concordancia"]
    assert f["TIP"] == "usa el plural"


def test_parse_fields_ignores_non_key_lines():
    f = llm._parse_fields("hola sin clave\nREPLY: ok")
    assert f["REPLY"] == "ok"
    assert "hola sin clave" not in f


def test_partial_reply_progressive():
    assert llm.partial_reply("REPLY: Hello wor") == "Hello wor"
    assert llm.partial_reply("REPLY: Hello world\nCORRECTION: x | y | z") == "Hello world"
    assert llm.partial_reply("aún no hay reply") == ""


def test_parse_conversation_english_reply():
    raw = ("REPLY: That sounds great! How long have you worked there?\n"
           "CORRECTION: I has | I have | concordancia\n"
           "TIP: di 'I have been working'")
    d = llm.parse_conversation_raw(raw)
    assert d["reply"].startswith("That sounds great")
    assert d["corrections"][0]["original"] == "I has"
    assert d["corrections"][0]["correction"] == "I have"
    assert d["vocab_tip"].startswith("di")


def test_parse_conversation_alternatives_use_o():
    raw = "REPLY: Nice. What's next?\nCORRECTION: a lot of work | a little / lots of work | nota"
    d = llm.parse_conversation_raw(raw)
    assert " o " in d["corrections"][0]["correction"]   # '/' se convierte en ' o '


def test_parse_conversation_no_reply_label_does_not_leak_fields():
    """Si el modelo NO etiqueta REPLY y deja la respuesta suelta, la burbuja debe mostrar SOLO
    esa respuesta, nunca CORRECTION/TIP/SCORE (regresión del volcado crudo)."""
    raw = ("CORRECTION: leave me a peanut noir | I'll get you a Pinot Noir | corrige la frase\n"
           "TIP: Remember to use 'you' with a customer.\n"
           "SCORE: 70\n"
           "I will bring you the Chianti and the Pinot Noir. Enjoy your meal!")
    d = llm.parse_conversation_raw(raw)
    assert d["reply"] == "I will bring you the Chianti and the Pinot Noir. Enjoy your meal!"
    assert "CORRECTION" not in d["reply"] and "SCORE" not in d["reply"] and "TIP" not in d["reply"]
    assert d["score"] == 70
    assert d["corrections"][0]["correction"] == "I'll get you a Pinot Noir"


def test_parse_conversation_inline_field_leak_is_trimmed():
    """Si una etiqueta se cuela en la misma línea de REPLY, se recorta."""
    d = llm.parse_conversation_raw("REPLY: Sure, here you go. CORRECTION: a | b | c\nSCORE: 50")
    assert d["reply"] == "Sure, here you go."
