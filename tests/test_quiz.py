"""Tests for the quiz generator. Run: python tests/test_quiz.py"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import quiz  # noqa: E402


def _notes(name):
    with open(os.path.join(ROOT, "documents_to_import", name), encoding="utf-8") as f:
        return f.read()


def test_blank_questions_from_prose_and_formulas():
    text = _notes("ohms_law.txt")
    questions = quiz.make_cloze(text, 6, seed=1)
    assert len(questions) >= 4
    kinds = {q["kind"] for q in questions}
    assert "formula" in kinds and "blank" in kinds
    for q in questions:
        assert "_____" in q["question"]
        assert q["answer"] and q["answer"] not in q["question"].replace("_____", "")


def test_same_seed_gives_same_quiz():
    text = _notes("indian_independence_movement.txt")
    assert quiz.make_cloze(text, 5, seed=7) == quiz.make_cloze(text, 5, seed=7)


def test_parse_ai_output():
    good = "Q1: What is Ohm's law?\nA1: V = I R\nQ2: What unit is resistance measured in?\nA2: The ohm"
    assert len(quiz.parse_qa(good, 5)) == 2
    messy = "Sure!\n**Question 1:** What does KE stand for?\n**Answer 1:** Kinetic energy"
    assert quiz.parse_qa(messy, 5)[0]["answer"] == "Kinetic energy"
    assert quiz.parse_qa("I cannot help with that.", 5) == []


def test_ai_mode_falls_back():
    text = _notes("ohms_law.txt")
    questions, note = quiz.make_quiz(text, 3, "ai", ask=lambda s, u, t: "no idea")
    assert questions and questions[0]["kind"] != "qa" and "fill-in-the-blank" in note

    def broken(s, u, t):
        raise RuntimeError("server down")

    questions, note = quiz.make_quiz(text, 3, "ai", ask=broken)
    assert questions


def test_short_document():
    questions, note = quiz.make_quiz("Too short.", 3)
    assert questions == [] and "too little text" in note


def test_checking_answers():
    assert quiz.check_blank(" Voltage ", "voltage")
    assert not quiz.check_blank("", "voltage")
    assert quiz.check_blank("R", "R", "formula")
    assert not quiz.check_blank("r", "R", "formula")


if __name__ == "__main__":
    test_blank_questions_from_prose_and_formulas()
    test_same_seed_gives_same_quiz()
    test_parse_ai_output()
    test_ai_mode_falls_back()
    test_short_document()
    test_checking_answers()
    print("All quiz tests passed.")
