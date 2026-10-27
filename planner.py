"""
planner.py - an exam study timetable made from your subjects and exam date.

Harder subjects get more time. The last day before the exam is a light revision of
every subject. An optional weekly rest day is skipped (never in the last two days).
Pure Python and instant: no AI and no extra downloads.
"""
import csv
import io
import math
from datetime import date, timedelta

BLOCK_MINUTES = 30
DIFFICULTY_LABELS = {1: "Easy", 2: "Medium", 3: "Hard"}


def _clean_subjects(subjects):
    cleaned, seen = [], set()
    for item in subjects or []:
        name = " ".join(str(item.get("name", "")).split())
        if not name or name.lower() in seen:
            continue
        seen.add(name.lower())
        try:
            difficulty = int(item.get("difficulty", 2))
        except (TypeError, ValueError):
            difficulty = 2
        cleaned.append({"name": name, "difficulty": min(3, max(1, difficulty))})
    return cleaned


def _split_blocks(total: int, weights: list) -> list:
    """Share total blocks between subjects by weight (largest remainder method)."""
    weight_sum = sum(weights)
    ideal = [total * w / weight_sum for w in weights]
    shares = [int(x) for x in ideal]
    leftovers = sorted(range(len(weights)), key=lambda i: (ideal[i] - shares[i]), reverse=True)
    for i in leftovers[: total - sum(shares)]:
        shares[i] += 1
    return shares


_DIFFICULTY_WORDS = {
    "hard": 3, "difficult": 3, "3": 3,
    "medium": 2, "normal": 2, "2": 2,
    "easy": 1, "1": 1,
}


def parse_subject_lines(text: str) -> list:
    """Subjects from lines such as 'Physics, hard' or 'English, easy' or just 'Maths'."""
    subjects = []
    for line in (text or "").splitlines():
        parts = [p.strip() for p in line.split(",") if p.strip()]
        if not parts:
            continue
        difficulty = 2
        for word in parts[1:]:
            if word.lower() in _DIFFICULTY_WORDS:
                difficulty = _DIFFICULTY_WORDS[word.lower()]
        subjects.append({"name": parts[0], "difficulty": difficulty})
    return subjects


def make_plan(subjects, exam_date: date, start: date = None, hours_per_day: float = 2.0,
              rest_weekday=None) -> dict:
    """Build a day-by-day plan.

    subjects: [{"name": "Physics", "difficulty": 1..3}, ...]
    rest_weekday: 0 = Monday ... 6 = Sunday, or None for no rest day.
    Returns {"days": [...], "per_subject": {...}, "warnings": [...]}.
    Raises ValueError for input that cannot make a plan.
    """
    subjects = _clean_subjects(subjects)
    if not subjects:
        raise ValueError("Add at least one subject.")
    start = start or date.today()
    if exam_date <= start:
        raise ValueError("The exam date must be after today.")
    if not 0.5 <= hours_per_day <= 12:
        raise ValueError("Study hours per day must be between 0.5 and 12.")

    names = [s["name"] for s in subjects]
    weights = [s["difficulty"] for s in subjects]
    blocks_per_day = max(1, round(hours_per_day * 60 / BLOCK_MINUTES))
    warnings = []

    # Calendar: every day from today to the day before the exam, then the exam.
    calendar = []
    day = start
    while day < exam_date:
        calendar.append(day)
        day += timedelta(days=1)

    revision_day = calendar[-1]
    plan_days, study_days = [], []
    for d in calendar:
        is_last_two = d >= exam_date - timedelta(days=2)
        if d == revision_day:
            kind = "revision"
        elif rest_weekday is not None and d.weekday() == rest_weekday and not is_last_two:
            kind = "rest"
        else:
            kind = "study"
        entry = {"date": d, "kind": kind, "items": []}
        plan_days.append(entry)
        if kind == "study":
            study_days.append(entry)

    # Revision day: every subject gets an equal share of the day.
    revision = plan_days[-1]
    each = max(5, int(hours_per_day * 60 / len(names) // 5 * 5))
    revision["items"] = [(n, each) for n in names]

    # Study days: split the available blocks by difficulty, then deal them out.
    if study_days:
        total_blocks = len(study_days) * blocks_per_day
        if total_blocks < len(names):
            warnings.append(
                "There is not enough time to cover every subject before the exam. "
                "Add study hours or reduce the number of subjects."
            )
            ranked = sorted(range(len(names)), key=lambda i: -weights[i])
            remaining = [0] * len(names)
            for i in ranked[:total_blocks]:
                remaining[i] = 1
        else:
            remaining = _split_blocks(total_blocks, weights)

        quota = [max(1, r) for r in remaining]
        done = [0] * len(names)

        for index, entry in enumerate(study_days):
            cap = max(1, math.ceil(blocks_per_day / 2))
            used = [0] * len(names)
            for _ in range(blocks_per_day):
                options = [i for i in range(len(names)) if remaining[i] > 0 and used[i] < cap]
                if not options:
                    options = [i for i in range(len(names)) if remaining[i] > 0]
                if not options:
                    break
                # Give the next block to the subject that is furthest behind its
                # share, so every subject comes up regularly instead of in lumps.
                pick = min(options, key=lambda i: ((done[i] + 0.5) / quota[i], (i - index) % len(names)))
                remaining[pick] -= 1
                done[pick] += 1
                used[pick] += 1
            entry["items"] = [(names[i], used[i] * BLOCK_MINUTES) for i in range(len(names)) if used[i]]
            entry["items"].sort(key=lambda item: -item[1])
    else:
        warnings.append("Only one day is left, so the plan is a single revision day.")

    plan_days.append({"date": exam_date, "kind": "exam", "items": []})

    per_subject = {n: 0 for n in names}
    for entry in plan_days:
        for name, minutes in entry["items"]:
            per_subject[name] += minutes

    return {"days": plan_days, "per_subject": per_subject, "warnings": warnings}


def _label(entry) -> str:
    return entry["date"].strftime("%a %d %b")


def _describe(entry) -> str:
    if entry["kind"] == "exam":
        return "Exam day. Good luck!"
    if entry["kind"] == "rest":
        return "Rest day"
    prefix = "Revise: " if entry["kind"] == "revision" else ""
    return prefix + ", ".join(f"{name} {minutes} min" for name, minutes in entry["items"])


def plan_to_markdown(plan: dict, title: str = "Study plan") -> str:
    """The plan as Markdown. Pass title=None to leave the heading out."""
    lines = [f"# {title}", ""] if title else []
    for entry in plan["days"]:
        lines.append(f"- **{_label(entry)}**: {_describe(entry)}")
    lines += ["", "## Time per subject"]
    for name, minutes in plan["per_subject"].items():
        lines.append(f"- {name}: {minutes / 60:.1f} hours")
    return "\n".join(lines) + "\n"


def plan_to_csv(plan: dict) -> str:
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(["Date", "Type", "Plan"])
    for entry in plan["days"]:
        writer.writerow([entry["date"].isoformat(), entry["kind"], _describe(entry)])
    return out.getvalue()
