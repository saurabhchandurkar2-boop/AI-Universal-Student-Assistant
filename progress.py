"""
progress.py - quiz score history, plus saving study data on your own computer.

Your flashcards and scores are saved as small JSON files in the "user_data"
folder (or the folder named by STUDY_DATA_DIR) so they are still there the next
time you start the app. The free online demo does not save anything: each visitor
keeps their data only for the current session.
"""
import json
import os
import tempfile
import time

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
MAX_HISTORY = 200


def data_dir() -> str:
    return os.getenv("STUDY_DATA_DIR") or os.path.join(PROJECT_ROOT, "user_data")


def load(name: str, default):
    """Read user_data/<name>.json. Returns default if missing or damaged."""
    try:
        with open(os.path.join(data_dir(), name + ".json"), "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def save(name: str, data) -> bool:
    """Write user_data/<name>.json safely. Returns False instead of raising."""
    try:
        folder = data_dir()
        os.makedirs(folder, exist_ok=True)
        handle, temp_path = tempfile.mkstemp(dir=folder, suffix=".tmp")
        with os.fdopen(handle, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        os.replace(temp_path, os.path.join(folder, name + ".json"))
        return True
    except Exception:
        return False


def record_quiz(history, doc: str, correct: int, total: int, when=None) -> list:
    """Return a new history list with this quiz result added."""
    if total <= 0:
        return list(history or [])
    entry = {
        "doc": doc,
        "correct": int(correct),
        "total": int(total),
        "when": time.time() if when is None else when,
    }
    return (list(history or []) + [entry])[-MAX_HISTORY:]


def summary(history) -> dict:
    """Attempts, average and best score (as percentages) and the last five results."""
    items = [h for h in history or [] if isinstance(h, dict) and h.get("total")]
    if not items:
        return {"attempts": 0, "average": 0, "best": 0, "last": []}
    percents = [round(100 * h["correct"] / h["total"]) for h in items]
    return {
        "attempts": len(items),
        "average": round(sum(percents) / len(percents)),
        "best": max(percents),
        "last": [
            {"doc": h["doc"], "score": f"{h['correct']}/{h['total']}", "percent": p, "when": h["when"]}
            for h, p in list(zip(items, percents))[-5:]
        ],
    }
