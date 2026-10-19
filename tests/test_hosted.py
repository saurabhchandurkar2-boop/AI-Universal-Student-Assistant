"""Tests for hosted (public demo) mode. Run: python tests/test_hosted.py"""
import os
import sys
import types

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ["APP_MODE"] = "hosted"

import hosted  # noqa: E402
from knowledge.retriever import KnowledgeRetriever  # noqa: E402


def test_mode_switch():
    assert hosted.is_hosted() is True
    os.environ["APP_MODE"] = "local"
    assert hosted.is_hosted() is False
    os.environ["APP_MODE"] = "hosted"


def test_visitors_are_isolated():
    a, b = hosted.Workspace(), hosted.Workspace()
    a.add(b"Zebrafinch secret code 777 belongs to visitor A.", "private notes.txt")
    assert "private_notes.txt" in a.list()
    assert "private_notes.txt" not in b.list()
    assert len(KnowledgeRetriever(a.dir).documents) == len(KnowledgeRetriever(b.dir).documents) + 1
    assert a.remove("private_notes.txt") is True
    try:
        a.remove("../app.py")
        raise AssertionError("path traversal was not blocked")
    except ValueError:
        pass


def test_limits():
    w = hosted.Workspace()
    try:
        w.add(b"x" * (hosted.MAX_UPLOAD_MB * 1024 * 1024 + 1), "big.txt")
        raise AssertionError("size limit not enforced")
    except ValueError:
        pass


def test_no_key_and_fake_gemini():
    bot, _ = hosted.make_hosted_bot()
    assert bot.ai_engine.has_key() is False
    assert "Gemini API key" in bot.ask("what is ohm's law")

    class Models:
        def generate_content(self, model, contents, config):
            assert "Knowledge context" in contents
            return types.SimpleNamespace(text="Ohm's law says V = I R, so the voltage across a conductor equals the current through it times its resistance.", candidates=None)

    bot.ai_engine.gemini_client = types.SimpleNamespace(models=Models())
    assert "V = I R" in bot.ask("what is ohm's law")


def test_answer_details():
    bot, _ = hosted.make_hosted_bot()

    class Models:
        def generate_content(self, model, contents, config):
            return types.SimpleNamespace(
                text="Ohm's law says V = I R, so the voltage across a conductor equals "
                     "the current through it times its resistance.",
                candidates=None,
            )

    bot.ai_engine.gemini_client = types.SimpleNamespace(models=Models())
    info = bot.ask_with_info("what is ohm's law")
    assert info["seconds"] > 0
    assert info["origin"] == "notes"
    assert any("ohms_law" in s["filename"] for s in info["sources"]), info["sources"]
    assert all(s["snippet"] for s in info["sources"])


def test_wikipedia_only_when_notes_do_not_cover_it():
    import wiki_search

    bot, _ = hosted.make_hosted_bot()
    seen = []

    class Models:
        def generate_content(self, model, contents, config):
            seen.append(contents)
            return types.SimpleNamespace(
                text="Earthquakes are caused by the sudden release of energy in the Earth's crust, "
                     "usually along faults where tectonic plates move against each other.",
                candidates=None,
            )

    bot.ai_engine.gemini_client = types.SimpleNamespace(models=Models())
    calls = []

    def fake_lookup(question):
        calls.append(question)
        return [{"title": "Earthquake", "extract": "An earthquake is the shaking of the surface of the Earth.",
                 "url": "https://en.wikipedia.org/wiki/Earthquake"}]

    original = wiki_search.lookup
    wiki_search.lookup = fake_lookup
    try:
        info = bot.ask_with_info("what causes earthquakes")
        assert info["origin"] == "wikipedia", info["origin"]
        assert info["sources"][0]["url"].endswith("/Earthquake")
        assert "Wikipedia - Earthquake" in seen[-1]

        calls.clear()
        info = bot.ask_with_info("what is ohm's law")       # covered by the notes
        assert info["origin"] == "notes" and calls == []

        bot.use_wikipedia = False
        calls.clear()
        bot.ask_with_info("what causes earthquakes")
        assert calls == []                                   # switched off
    finally:
        wiki_search.lookup = original


if __name__ == "__main__":
    test_mode_switch()
    test_visitors_are_isolated()
    test_limits()
    test_no_key_and_fake_gemini()
    test_answer_details()
    test_wikipedia_only_when_notes_do_not_cover_it()
    print("All hosted tests passed.")
