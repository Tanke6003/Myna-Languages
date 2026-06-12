"""Persistencia ligera (SQLite) para la gamificación: puntos, racha y récord."""
import os
import sqlite3

from config import BASE_DIR

DB_PATH = os.path.join(BASE_DIR, "tutor.db")


def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _conn() as c:
        c.execute(
            "CREATE TABLE IF NOT EXISTS stats ("
            " id INTEGER PRIMARY KEY CHECK (id = 1),"
            " points INTEGER NOT NULL DEFAULT 0,"
            " streak INTEGER NOT NULL DEFAULT 0,"
            " best INTEGER NOT NULL DEFAULT 0)"
        )
        c.execute("INSERT OR IGNORE INTO stats (id, points, streak, best) VALUES (1, 0, 0, 0)")
        c.execute(
            "CREATE TABLE IF NOT EXISTS activity ("
            " id INTEGER PRIMARY KEY AUTOINCREMENT,"
            " ts TEXT NOT NULL,"
            " kind TEXT NOT NULL,"
            " level TEXT,"
            " score INTEGER,"
            " correct INTEGER)"
        )
        c.execute(
            "CREATE TABLE IF NOT EXISTS missed ("
            " word TEXT PRIMARY KEY,"
            " count INTEGER NOT NULL DEFAULT 0,"
            " last_ts TEXT)"
        )
        c.execute(
            "CREATE TABLE IF NOT EXISTS flashcards ("
            " id INTEGER PRIMARY KEY AUTOINCREMENT,"
            " front TEXT UNIQUE NOT NULL,"
            " back TEXT,"
            " ease REAL NOT NULL DEFAULT 2.5,"
            " interval REAL NOT NULL DEFAULT 0,"
            " reps INTEGER NOT NULL DEFAULT 0,"
            " due TEXT NOT NULL)"
        )


def _row_to_stats(row):
    points = row["points"]
    return {
        "points": points,
        "streak": row["streak"],
        "best": row["best"],
        "level": points // 100 + 1,
    }


def get_stats():
    with _conn() as c:
        row = c.execute("SELECT points, streak, best FROM stats WHERE id = 1").fetchone()
    return _row_to_stats(row)


def award(points, correct):
    """Suma puntos y actualiza la racha. Devuelve las stats actualizadas."""
    with _conn() as c:
        row = c.execute("SELECT points, streak, best FROM stats WHERE id = 1").fetchone()
        new_points = row["points"] + int(points)
        if correct:
            new_streak = row["streak"] + 1
            new_best = max(row["best"], new_streak)
        else:
            new_streak = 0
            new_best = row["best"]
        c.execute(
            "UPDATE stats SET points = ?, streak = ?, best = ? WHERE id = 1",
            (new_points, new_streak, new_best),
        )
        row = c.execute("SELECT points, streak, best FROM stats WHERE id = 1").fetchone()
    return _row_to_stats(row)


def reset_stats():
    with _conn() as c:
        c.execute("UPDATE stats SET points = 0, streak = 0, best = 0 WHERE id = 1")
        c.execute("DELETE FROM activity")
        c.execute("DELETE FROM missed")
    return get_stats()


# --- Historial / progreso ---
def log_activity(kind, level=None, score=None, correct=None):
    from datetime import datetime
    with _conn() as c:
        c.execute(
            "INSERT INTO activity (ts, kind, level, score, correct) VALUES (?, ?, ?, ?, ?)",
            (datetime.now().isoformat(timespec="seconds"), kind, level, score,
             None if correct is None else int(bool(correct))),
        )


def bump_missed(words):
    from datetime import datetime
    ts = datetime.now().isoformat(timespec="seconds")
    with _conn() as c:
        for w in words or []:
            w = (w or "").strip().lower()
            if not w:
                continue
            c.execute(
                "INSERT INTO missed (word, count, last_ts) VALUES (?, 1, ?) "
                "ON CONFLICT(word) DO UPDATE SET count = count + 1, last_ts = excluded.last_ts",
                (w, ts),
            )


def missed_top(n=20):
    with _conn() as c:
        rows = c.execute("SELECT word, count FROM missed ORDER BY count DESC, last_ts DESC "
                         "LIMIT ?", (n,)).fetchall()
    return [dict(r) for r in rows]


def missed_count():
    with _conn() as c:
        return c.execute("SELECT COUNT(*) AS n FROM missed").fetchone()["n"]


def missed_decrement(word):
    """Al acertar una palabra fallada en el repaso, baja su contador (y la quita si llega a 0)."""
    word = (word or "").strip().lower()
    with _conn() as c:
        c.execute("UPDATE missed SET count = count - 1 WHERE word = ?", (word,))
        c.execute("DELETE FROM missed WHERE count <= 0")


def get_progress():
    with _conn() as c:
        totals = [dict(r) for r in c.execute(
            "SELECT kind, COUNT(*) AS count, "
            " CAST(ROUND(AVG(score)) AS INTEGER) AS avg_score "
            "FROM activity GROUP BY kind ORDER BY count DESC").fetchall()]
        recent = [dict(r) for r in c.execute(
            "SELECT ts, kind, level, score, correct FROM activity "
            "ORDER BY id DESC LIMIT 15").fetchall()]
        missed = [dict(r) for r in c.execute(
            "SELECT word, count FROM missed ORDER BY count DESC, last_ts DESC LIMIT 15").fetchall()]
        total_count = c.execute("SELECT COUNT(*) AS n FROM activity").fetchone()["n"]
    return {"stats": get_stats(), "totals": totals, "recent": recent,
            "missed": missed, "total_count": total_count}


# --- Flashcards (repetición espaciada, SM-2 simplificado) ---
def _now_iso():
    from datetime import datetime
    return datetime.now().isoformat(timespec="seconds")


def fc_add(front, back=""):
    front = (front or "").strip()
    if not front:
        return
    with _conn() as c:
        c.execute("INSERT OR IGNORE INTO flashcards (front, back, due) VALUES (?, ?, ?)",
                  (front, back or "", _now_iso()))


def fc_existing_fronts():
    with _conn() as c:
        return {r["front"].lower() for r in c.execute("SELECT front FROM flashcards").fetchall()}


def fc_counts():
    now = _now_iso()
    with _conn() as c:
        total = c.execute("SELECT COUNT(*) AS n FROM flashcards").fetchone()["n"]
        due = c.execute("SELECT COUNT(*) AS n FROM flashcards WHERE due <= ?", (now,)).fetchone()["n"]
    return {"total": total, "due": due}


def fc_next():
    now = _now_iso()
    with _conn() as c:
        row = c.execute("SELECT id, front, back FROM flashcards WHERE due <= ? "
                        "ORDER BY due LIMIT 1", (now,)).fetchone()
    return dict(row) if row else None


def fc_review(card_id, grade):
    from datetime import datetime, timedelta
    with _conn() as c:
        row = c.execute("SELECT ease, interval, reps FROM flashcards WHERE id = ?",
                        (card_id,)).fetchone()
        if not row:
            return
        ease, interval, reps = row["ease"], row["interval"], row["reps"]
        if grade == "again":
            ease = max(1.3, ease - 0.2)
            interval, reps = 0, 0
            due = datetime.now()  # reaparece en esta sesión
        elif grade == "easy":
            reps += 1
            ease += 0.1
            interval = 4 if interval < 1 else round(interval * ease * 1.3)
            due = datetime.now() + timedelta(days=interval)
        else:  # good
            reps += 1
            interval = 1 if reps == 1 else (3 if reps == 2 else round(interval * ease))
            due = datetime.now() + timedelta(days=interval)
        c.execute("UPDATE flashcards SET ease = ?, interval = ?, reps = ?, due = ? WHERE id = ?",
                  (ease, interval, reps, due.isoformat(timespec="seconds"), card_id))


def level_stats(level):
    """Cuántos ejercicios y media de puntuación en un nivel (para sugerir subir de nivel)."""
    with _conn() as c:
        row = c.execute("SELECT COUNT(*) AS n, CAST(AVG(score) AS INTEGER) AS avg "
                        "FROM activity WHERE level = ?", (level,)).fetchone()
    return {"count": row["n"] or 0, "avg_score": row["avg"]}


def level_kind_stats(level):
    """Por tipo de ejercicio en un nivel: nº de ejercicios, suma y conteo de puntuaciones.
    Sirve para medir la COBERTURA por área de destreza (hablar/escuchar/escribir/vocabulario)
    al sugerir subir de nivel. Se devuelve suma+conteo (no la media) para poder promediar
    varios 'kind' dentro de un área con el peso correcto."""
    with _conn() as c:
        rows = c.execute(
            "SELECT kind, COUNT(*) AS n, SUM(score) AS s, COUNT(score) AS ns "
            "FROM activity WHERE level = ? GROUP BY kind", (level,)).fetchall()
    return {r["kind"]: {"count": r["n"] or 0, "score_sum": r["s"] or 0, "scored": r["ns"] or 0}
            for r in rows}


def export_all():
    with _conn() as c:
        st = c.execute("SELECT points, streak, best FROM stats WHERE id = 1").fetchone()
        activity = [dict(r) for r in c.execute(
            "SELECT ts, kind, level, score, correct FROM activity").fetchall()]
        missed = [dict(r) for r in c.execute(
            "SELECT word, count, last_ts FROM missed").fetchall()]
        flashcards = [dict(r) for r in c.execute(
            "SELECT front, back, ease, interval, reps, due FROM flashcards").fetchall()]
    return {"stats": dict(st), "activity": activity, "missed": missed, "flashcards": flashcards}


def import_all(data):
    s = data.get("stats") or {}
    with _conn() as c:
        c.execute("UPDATE stats SET points = ?, streak = ?, best = ? WHERE id = 1",
                  (int(s.get("points", 0)), int(s.get("streak", 0)), int(s.get("best", 0))))
        c.execute("DELETE FROM activity")
        c.execute("DELETE FROM missed")
        c.execute("DELETE FROM flashcards")
        for a in data.get("activity", []):
            c.execute("INSERT INTO activity (ts, kind, level, score, correct) VALUES (?, ?, ?, ?, ?)",
                      (a.get("ts"), a.get("kind"), a.get("level"), a.get("score"), a.get("correct")))
        for m in data.get("missed", []):
            c.execute("INSERT OR REPLACE INTO missed (word, count, last_ts) VALUES (?, ?, ?)",
                      (m.get("word"), int(m.get("count", 0)), m.get("last_ts")))
        for f in data.get("flashcards", []):
            c.execute("INSERT OR REPLACE INTO flashcards (front, back, ease, interval, reps, due) "
                      "VALUES (?, ?, ?, ?, ?, ?)",
                      (f.get("front"), f.get("back", ""), float(f.get("ease", 2.5)),
                       float(f.get("interval", 0)), int(f.get("reps", 0)),
                       f.get("due") or _now_iso()))
    return get_progress()
