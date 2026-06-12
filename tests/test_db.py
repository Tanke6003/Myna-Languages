"""Tests de la capa de datos / lógica de gamificación y repetición espaciada."""
import pytest

from backend import db


@pytest.fixture
def fresh_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test.db"))
    db.init_db()
    return db


def test_award_points_and_streak(fresh_db):
    s = fresh_db.award(10, True)
    assert (s["points"], s["streak"], s["best"]) == (10, 1, 1)
    s = fresh_db.award(5, True)
    assert (s["points"], s["streak"], s["best"]) == (15, 2, 2)
    s = fresh_db.award(0, False)          # fallo: rompe la racha, mantiene récord
    assert (s["points"], s["streak"], s["best"]) == (15, 0, 2)
    assert s["level"] == 1                 # 15 pts -> nivel 1


def test_level_increases_every_100(fresh_db):
    fresh_db.award(250, True)
    assert fresh_db.get_stats()["level"] == 3   # 250 // 100 + 1


def test_missed_words(fresh_db):
    fresh_db.bump_missed(["the", "cat", "the"])   # 'the' x2, 'cat' x1
    assert fresh_db.missed_count() == 2
    fresh_db.missed_decrement("the")
    fresh_db.missed_decrement("the")              # llega a 0 -> se borra
    words = {m["word"] for m in fresh_db.missed_top()}
    assert "the" not in words and "cat" in words


def test_flashcards_spaced_repetition(fresh_db):
    fresh_db.fc_add("hello", "hola")
    assert fresh_db.fc_counts() == {"total": 1, "due": 1}
    card = fresh_db.fc_next()
    assert card["front"] == "hello" and card["back"] == "hola"

    fresh_db.fc_review(card["id"], "good")        # se reprograma a futuro
    assert fresh_db.fc_counts()["due"] == 0
    assert fresh_db.fc_next() is None

    fresh_db.fc_add("dog", "perro")
    again = fresh_db.fc_next()
    fresh_db.fc_review(again["id"], "again")      # vuelve a estar pendiente
    assert fresh_db.fc_counts()["due"] >= 1


def test_level_stats(fresh_db):
    fresh_db.log_activity("reading", "B1", 90, True)
    fresh_db.log_activity("reading", "B1", 80, True)
    st = fresh_db.level_stats("B1")
    assert st["count"] == 2 and st["avg_score"] == 85


def test_export_import_roundtrip(fresh_db):
    fresh_db.award(20, True)
    fresh_db.bump_missed(["stubborn"])
    data = fresh_db.export_all()

    fresh_db.reset_stats()
    assert fresh_db.get_stats()["points"] == 0
    assert fresh_db.missed_count() == 0

    fresh_db.import_all(data)
    assert fresh_db.get_stats()["points"] == 20
    assert fresh_db.missed_count() == 1
