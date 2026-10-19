"""Tests for the writing helper. Run: python tests/test_study_helper.py"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import study_helper as sh  # noqa: E402


def test_prompts_carry_the_choices():
    system, user, tokens = sh.build_request(
        "Explain a topic", "photosynthesis", "Simple (class 6 to 8)", "Hindi", "Short",
        facts="Photosynthesis makes sugar from light.")
    assert "classes 6 to 8" in user and "Hindi" in user and "120 words" in user
    assert "Photosynthesis makes sugar" in user and user.rstrip().endswith("photosynthesis")
    assert tokens == sh.LENGTHS["Short"][1]


def test_improve_keeps_language_and_ignores_facts():
    _, user, tokens = sh.build_request(
        "Improve my writing", "i is going school", "Standard (class 9 to 12)", None, "Short",
        facts="should not appear")
    assert "same language" in user and "should not appear" not in user
    assert tokens >= 600


def test_notes_task_and_input_limit():
    long_text = "word " * 5000
    _, user, _ = sh.build_request(
        "Make study notes", long_text, "Detailed (college)", "English", "Medium", max_input_chars=1000)
    assert "study notes" in user and len(user) < 1500


def test_validation():
    for bad in ("", "   "):
        try:
            sh.build_request("Explain a topic", bad, "Simple (class 6 to 8)", "English", "Short")
            raise AssertionError("empty input accepted")
        except ValueError:
            pass
    try:
        sh.build_request("Dance", "x", "Simple (class 6 to 8)", "English", "Short")
        raise AssertionError("unknown task accepted")
    except ValueError:
        pass


def test_run_uses_the_model():
    calls = []

    def ask(system, user, tokens):
        calls.append((system, user, tokens))
        return "  Plants make food using sunlight.  "

    assert sh.run("Explain a topic", "photosynthesis", "Simple (class 6 to 8)", "English", "Short", ask) \
        == "Plants make food using sunlight."
    assert len(calls) == 1
    try:
        sh.run("Explain a topic", "x", "Simple (class 6 to 8)", "English", "Short", lambda s, u, t: "")
        raise AssertionError("empty answer accepted")
    except ValueError:
        pass


if __name__ == "__main__":
    test_prompts_carry_the_choices()
    test_improve_keeps_language_and_ignores_facts()
    test_notes_task_and_input_limit()
    test_validation()
    test_run_uses_the_model()
    print("All study helper tests passed.")
