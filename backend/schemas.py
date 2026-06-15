"""Modelos Pydantic para los cuerpos de petición JSON (los de audio usan multipart)."""
from pydantic import BaseModel


class LevelTopic(BaseModel):
    level: str
    topic: str = ""


class LevelReq(BaseModel):
    level: str


class VocabReq(BaseModel):
    level: str
    kind: str  # "Tiempos verbales" | "Sinónimos"


class TextCheckReq(BaseModel):
    original: str
    correction: str


class WritingNewReq(BaseModel):
    level: str
    kind: str  # "rewrite" | "translate" | "complete" | "paragraph"


class WritingCheckReq(BaseModel):
    kind: str
    prompt: str
    instruction: str = ""
    answer: str
    level: str = ""


class TranslateReq(BaseModel):
    text: str
    direction: str = "Auto"  # "Auto" | "ES→EN" | "EN→ES"
    note: str = ""           # instrucción extra del usuario para rebatir/ajustar


class DetailsReq(BaseModel):
    text: str                # palabra/frase en inglés para sinónimos + ejemplos


class ConversationTextReq(BaseModel):
    level: str
    scenario: str = ""
    detail: str = ""
    history: list[dict] = []
    user_text: str           # texto (posiblemente corregido por el usuario) a reenviar


class ConceptAddReq(BaseModel):
    phrase: str
    example: str = ""


class ConceptPracticeReq(BaseModel):
    level: str
    type: str = ""   # "gap" | "choice" | "produce" | "" (aleatorio)


class ConceptCheckReq(BaseModel):
    phrase: str
    sentence: str


class ConceptDeleteReq(BaseModel):
    id: int


class AwardReq(BaseModel):
    points: int
    correct: bool
    kind: str = ""              # 'reading' | 'text' | 'vocab' | 'dictation'
    level: str = ""
    score: int | None = None
    words: list[str] = []       # palabras falladas a registrar
