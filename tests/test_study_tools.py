"""Tests for flashcards, progress, exporters and the planner. Run: python tests/test_study_tools.py"""
import csv
import io
import json
import os
import sys
import tempfile
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import exporters  # noqa: E402
import flashcards  # noqa: E402
import planner  # noqa: E402
import progress  # noqa: E402

DAY = flashcards.DAY
QUESTIONS = [
    {"question": "Ohm's law says V = _____ R", "answer": "I", "kind": "formula"},
    {"question": "The unit of resistance is the _____", "answer": "ohm", "kind": "blank"},
]


# ---------------- flashcards ----------------

def test_adding_cards_skips_duplicates_and_blanks():
    deck = flashcards.Deck()
    assert deck.add_questions(QUESTIONS, "ohms_law.txt", now=0) == 2
    assert deck.add_questions(QUESTIONS, "ohms_law.txt", now=0) == 0
    assert deck.add("", "x") is False and deck.add("x", "") is False
    assert len(deck.cards) == 2


def test_new_cards_are_due_and_grading_moves_boxes():
    deck = flashcards.Deck()
    deck.add("Capital of France?", "Paris", now=1000)
    card = deck.next_card(now=1000)
    assert card["box"] == 1

    assert deck.grade(card["id"], True, now=1000)
    assert deck.cards[0]["box"] == 2
    assert deck.next_card(now=1000) is None                       # box 2 waits one day
    assert deck.next_card(now=1000 + DAY)["id"] == card["id"]

    deck.grade(card["id"], True, now=1000 + DAY)                  # box 3
    deck.grade(card["id"], True, now=1000 + 4 * DAY)              # box 4
    deck.grade(card["id"], True, now=1000 + 12 * DAY)             # box 5
    deck.grade(card["id"], True, now=1000 + 30 * DAY)             # stays at 5
    assert deck.cards[0]["box"] == 5

    deck.grade(card["id"], False, now=2000 + 40 * DAY)            # a miss goes back to 1, due now
    assert deck.cards[0]["box"] == 1 and deck.cards[0]["lapses"] == 1
    assert deck.next_card(now=2000 + 40 * DAY) is not None
    assert deck.grade("no-such-card", True) is False


def test_missed_cards_come_first():
    deck = flashcards.Deck()
    deck.add("A?", "a", now=0)
    deck.add("B?", "b", now=0)
    first, second = deck.cards
    deck.grade(first["id"], True, now=0)
    deck.grade(first["id"], True, now=2 * DAY)                    # box 3, due in 3 days
    deck.grade(second["id"], False, now=0)                        # box 1, due now
    assert deck.next_card(now=3 * DAY)["id"] == second["id"]      # lowest box first


def test_stats_and_waiting_message():
    deck = flashcards.Deck()
    assert deck.seconds_until_next() is None and deck.stats()["total"] == 0
    deck.add("Q1?", "a", now=0)
    deck.add("Q2?", "b", now=0)
    deck.grade(deck.cards[0]["id"], True, now=0)
    stats = deck.stats(now=0)
    assert stats == {"total": 2, "due": 1, "learned": 0, "boxes": {1: 1, 2: 1, 3: 0, 4: 0, 5: 0}}
    deck.grade(deck.cards[1]["id"], True, now=0)
    assert deck.seconds_until_next(now=0) == DAY
    assert flashcards.describe_wait(0) == "now"
    assert flashcards.describe_wait(1800) == "in 30 minutes"
    assert flashcards.describe_wait(3 * 3600) == "in 3 hours"
    assert flashcards.describe_wait(2 * DAY) == "in 2 days"
    assert flashcards.describe_wait(None) == ""


def test_deck_survives_save_and_damaged_data():
    deck = flashcards.Deck()
    deck.add_questions(QUESTIONS, "ohms_law.txt", now=5)
    deck.grade(deck.cards[0]["id"], True, now=5)
    restored = flashcards.Deck.from_list(json.loads(json.dumps(deck.to_list())))
    assert restored.to_list() == deck.to_list()

    messy = flashcards.Deck.from_list([
        {"front": "ok?", "back": "yes", "box": 99, "due": "oops", "reviews": "many"},
        {"front": "", "back": "no front"}, "not a dict", None,
    ])
    assert len(messy.cards) == 1 and messy.cards[0]["box"] == 1
    assert messy.cards[0]["due"] == 0 and messy.cards[0]["reviews"] == 0
    assert flashcards.Deck.from_list("garbage").cards == []


def test_csv_export_has_no_header_and_handles_commas():
    deck = flashcards.Deck()
    deck.add('Define "force", please', "Push or pull, in newtons", "physics.txt")
    rows = list(csv.reader(io.StringIO(deck.to_csv())))
    assert rows == [['Define "force", please', "Push or pull, in newtons", "physics.txt"]]


# ---------------- progress ----------------

def test_quiz_history_and_summary():
    history = []
    assert progress.summary(history)["attempts"] == 0
    history = progress.record_quiz(history, "ohms_law.txt", 4, 5, when=1)
    history = progress.record_quiz(history, "kinematics.txt", 2, 5, when=2)
    assert progress.record_quiz(history, "x", 0, 0) == history     # nothing to record
    info = progress.summary(history)
    assert info["attempts"] == 2 and info["average"] == 60 and info["best"] == 80
    assert info["last"][-1] == {"doc": "kinematics.txt", "score": "2/5", "percent": 40, "when": 2}

    many = []
    for n in range(250):
        many = progress.record_quiz(many, "d", 1, 2, when=n)
    assert len(many) == progress.MAX_HISTORY and many[-1]["when"] == 249


def test_saving_and_loading_user_data():
    with tempfile.TemporaryDirectory() as folder:
        os.environ["STUDY_DATA_DIR"] = os.path.join(folder, "nested", "user_data")
        try:
            assert progress.load("cards", []) == []                # nothing saved yet
            assert progress.save("cards", [{"front": "é?", "back": "ü"}])
            assert progress.load("cards", []) == [{"front": "é?", "back": "ü"}]
            leftovers = [f for f in os.listdir(os.environ["STUDY_DATA_DIR"]) if f.endswith(".tmp")]
            assert leftovers == []

            with open(os.path.join(os.environ["STUDY_DATA_DIR"], "cards.json"), "w") as f:
                f.write("{ this is not json")                      # damaged file
            assert progress.load("cards", ["default"]) == ["default"]
        finally:
            del os.environ["STUDY_DATA_DIR"]


# ---------------- exporters ----------------

def test_chat_export_lists_sources_and_pages():
    history = [
        {"role": "user", "content": "What is Ohm's law?"},
        {"role": "assistant", "content": "V = I R.", "meta": {
            "origin": "notes", "sources": [{"filename": "ohms_law.txt", "page": 2}, {"filename": "ohms_law.txt", "page": 2}]}},
        {"role": "assistant", "content": "36", "meta": {"origin": "calc"}},
    ]
    text = exporters.chat_to_markdown(history, "My chat")
    assert text.startswith("# My chat")
    assert "**You:** What is Ohm's law?" in text and "**Assistant:** V = I R." in text
    assert "sources: ohms_law.txt p.2" in text and text.count("ohms_law.txt p.2") == 1
    assert "from exact calculator" in text
    assert exporters.chat_to_markdown([]).strip() == "# Study chat"


def test_quiz_export_with_and_without_answers():
    text = exporters.quiz_to_text(QUESTIONS, "ohms_law.txt")
    assert text.startswith("Quiz: ohms_law.txt") and "1. Ohm's law says V = _____ R" in text
    assert "Answer key" in text and "1. I" in text and "2. ohm" in text
    plain = exporters.quiz_to_text(QUESTIONS, answers=False)
    assert "Answer key" not in plain


# ---------------- planner ----------------

SUBJECTS = [
    {"name": "Physics", "difficulty": 3},
    {"name": "English", "difficulty": 1},
    {"name": "Maths", "difficulty": 2},
]


def test_plan_covers_every_day_and_ends_with_exam():
    plan = planner.make_plan(SUBJECTS, date(2026, 11, 10), start=date(2026, 11, 1), hours_per_day=2)
    days = plan["days"]
    assert days[0]["date"] == date(2026, 11, 1) and days[-1]["date"] == date(2026, 11, 10)
    assert days[-1]["kind"] == "exam" and days[-2]["kind"] == "revision"
    assert [d["date"] for d in days] == sorted(d["date"] for d in days)
    assert len(days) == 10
    revised = {name for name, _ in days[-2]["items"]}
    assert revised == {"Physics", "English", "Maths"}
    assert plan["warnings"] == []


def test_study_days_use_the_full_time_and_harder_gets_more():
    plan = planner.make_plan(SUBJECTS, date(2026, 11, 10), start=date(2026, 11, 1), hours_per_day=2)
    study = [d for d in plan["days"] if d["kind"] == "study"]
    assert len(study) == 8
    for d in study:
        assert sum(m for _, m in d["items"]) == 120                 # 2 hours every study day
    totals = {name: 0 for name in plan["per_subject"]}
    for d in study:
        for name, minutes in d["items"]:
            totals[name] += minutes
    assert totals["Physics"] > totals["Maths"] > totals["English"]
    assert sum(totals.values()) == 8 * 120


def test_every_subject_comes_up_early_and_regularly():
    plan = planner.make_plan(SUBJECTS, date(2026, 11, 10), start=date(2026, 11, 1), hours_per_day=2)
    study = [d for d in plan["days"] if d["kind"] == "study"]
    first_three = {name for d in study[:3] for name, _ in d["items"]}
    assert first_three == {"Physics", "English", "Maths"}       # nothing is left to the end
    for name in ("Physics", "English", "Maths"):
        days_with = sum(any(n == name for n, _ in d["items"]) for d in study)
        assert days_with >= 3, (name, days_with)


def test_rest_day_is_skipped_but_never_just_before_the_exam():
    # 1 Nov 2026 is a Sunday; the exam is on Sunday 15 Nov, so Saturday the 14th is the day before.
    plan = planner.make_plan(SUBJECTS, date(2026, 11, 15), start=date(2026, 11, 1), hours_per_day=2, rest_weekday=6)
    rest = [d["date"] for d in plan["days"] if d["kind"] == "rest"]
    assert rest == [date(2026, 11, 1), date(2026, 11, 8)]
    assert all(d["items"] == [] for d in plan["days"] if d["kind"] == "rest")

    # Saturday rest on the day before the exam is ignored: that day is revision.
    plan = planner.make_plan(SUBJECTS, date(2026, 11, 15), start=date(2026, 11, 1), rest_weekday=5)
    assert plan["days"][-2]["date"] == date(2026, 11, 14) and plan["days"][-2]["kind"] == "revision"


def test_too_little_time_warns():
    many = [{"name": f"Subject {n}", "difficulty": 2} for n in range(8)]
    plan = planner.make_plan(many, date(2026, 11, 4), start=date(2026, 11, 1), hours_per_day=0.5)
    assert plan["warnings"]

    tomorrow = planner.make_plan(SUBJECTS, date(2026, 11, 2), start=date(2026, 11, 1))
    assert [d["kind"] for d in tomorrow["days"]] == ["revision", "exam"]
    assert tomorrow["warnings"]


def test_bad_input_is_rejected_and_names_are_cleaned():
    for bad in (
        lambda: planner.make_plan([], date(2026, 11, 10), start=date(2026, 11, 1)),
        lambda: planner.make_plan([{"name": "  "}], date(2026, 11, 10), start=date(2026, 11, 1)),
        lambda: planner.make_plan(SUBJECTS, date(2026, 11, 1), start=date(2026, 11, 1)),
        lambda: planner.make_plan(SUBJECTS, date(2026, 10, 1), start=date(2026, 11, 1)),
        lambda: planner.make_plan(SUBJECTS, date(2026, 11, 10), start=date(2026, 11, 1), hours_per_day=0),
    ):
        try:
            bad()
            raise AssertionError("expected ValueError")
        except ValueError:
            pass

    plan = planner.make_plan(
        [{"name": " Physics ", "difficulty": 9}, {"name": "physics", "difficulty": 1}, {"name": "Art", "difficulty": "x"}],
        date(2026, 11, 10), start=date(2026, 11, 1))
    assert list(plan["per_subject"]) == ["Physics", "Art"]


def test_subject_lines_are_understood():
    text = "Physics, hard\n\n  Maths  \nEnglish, easy\nChemistry, 3\nBiology, whatever\n,\n"
    assert planner.parse_subject_lines(text) == [
        {"name": "Physics", "difficulty": 3},
        {"name": "Maths", "difficulty": 2},
        {"name": "English", "difficulty": 1},
        {"name": "Chemistry", "difficulty": 3},
        {"name": "Biology", "difficulty": 2},
    ]
    assert planner.parse_subject_lines("") == [] and planner.parse_subject_lines(None) == []


def test_plan_exports():
    plan = planner.make_plan(SUBJECTS, date(2026, 11, 10), start=date(2026, 11, 1))
    markdown = planner.plan_to_markdown(plan, "My plan")
    assert markdown.startswith("# My plan") and "Exam day" in markdown and "Time per subject" in markdown
    rows = list(csv.reader(io.StringIO(planner.plan_to_csv(plan))))
    assert rows[0] == ["Date", "Type", "Plan"] and len(rows) == 1 + len(plan["days"])
    assert rows[-1][0] == "2026-11-10" and rows[-1][1] == "exam"
    assert not planner.plan_to_markdown(plan, None).startswith("#")


if __name__ == "__main__":
    test_adding_cards_skips_duplicates_and_blanks()
    test_new_cards_are_due_and_grading_moves_boxes()
    test_missed_cards_come_first()
    test_stats_and_waiting_message()
    test_deck_survives_save_and_damaged_data()
    test_csv_export_has_no_header_and_handles_commas()
    test_quiz_history_and_summary()
    test_saving_and_loading_user_data()
    test_chat_export_lists_sources_and_pages()
    test_quiz_export_with_and_without_answers()
    test_plan_covers_every_day_and_ends_with_exam()
    test_study_days_use_the_full_time_and_harder_gets_more()
    test_every_subject_comes_up_early_and_regularly()
    test_rest_day_is_skipped_but_never_just_before_the_exam()
    test_too_little_time_warns()
    test_bad_input_is_rejected_and_names_are_cleaned()
    test_subject_lines_are_understood()
    test_plan_exports()
    print("All study tool tests passed.")
