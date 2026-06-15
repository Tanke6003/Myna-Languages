"""Routers por feature (un router por responsabilidad — SRP)."""
from backend.routers import (
    conversation, exercises, translate, tts, progress, flashcards, concepts, settings,
)

# main.py incluye todos estos bajo el prefijo /api
ALL = [conversation, exercises, translate, tts, progress, flashcards, concepts, settings]
