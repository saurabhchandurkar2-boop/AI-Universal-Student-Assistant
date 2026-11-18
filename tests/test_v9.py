"""Tests for v9: search by meaning and streaming answers. Run: python tests/test_v9.py"""
import json
import os
import shutil
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import numpy as np  # noqa: E402

import semantic  # noqa: E402
from knowledge.retriever import KnowledgeRetriever  # noqa: E402

# A tiny stand-in for the real model: words with a similar meaning share a dimension.
CONCEPTS = {
    "sugar": 0, "glucose": 0, "food": 0, "starch": 0,
    "plants": 1, "plant": 1, "leaves": 1, "leaf": 1, "green": 1,
    "make": 2, "makes": 2, "produce": 2, "produces": 2, "convert": 2,
    "force": 3, "mass": 3, "acceleration": 3, "newton": 3,
}


class FakeEmbedder:
    name = "fake-concepts"

    def __init__(self):
        self.calls = 0

    def embed(self, texts, is_query=False):
        self.calls += len(texts)
        out = np.zeros((len(texts), 5), dtype="float32")
        for row, text in enumerate(texts):
            for word in text.lower().replace(".", " ").replace(",", " ").split():
                if word in CONCEPTS:
                    out[row, CONCEPTS[word]] += 1.0
            if not out[row].any():
                out[row, 4] = 1.0  # a text about none of our concepts
        return out / np.linalg.norm(out, axis=1, keepdims=True)


BIOLOGY = (
    "Leaves produce glucose using sunlight. The green pigment in the leaf captures "
    "light and the plant stores the energy as starch for later use."
)
PHYSICS = (
    "A larger force gives a larger acceleration when the mass stays the same. "
    "This is what Newton described for moving objects."
)
QUESTION = "how do plants make sugar"  # shares no important word with the biology note


def _library():
    folder = tempfile.mkdtemp(prefix="v9_lib_")
    with open(os.path.join(folder, "biology.txt"), "w", encoding="utf-8") as f:
        f.write(BIOLOGY)
    with open(os.path.join(folder, "physics.txt"), "w", encoding="utf-8") as f:
        f.write(PHYSICS)
    return folder


def test_index_finds_meaning_and_applies_threshold():
    index = semantic.SemanticIndex(embedder=FakeEmbedder())
    index.build([BIOLOGY, PHYSICS])
    hits = index.search(QUESTION, top_k=3, min_sim=0.6)
    assert [i for i, _ in hits] == [0], hits          # biology only
    assert index.search("what is the capital of France", min_sim=0.6) == []


def test_cache_means_each_text_is_embedded_once():
    folder = tempfile.mkdtemp(prefix="v9_cache_")
    try:
        cache = os.path.join(folder, "semantic_cache.json")
        first = FakeEmbedder()
        semantic.SemanticIndex(embedder=first, cache_path=cache).build([BIOLOGY, PHYSICS])
        assert first.calls == 2 and os.path.exists(cache)

        second = FakeEmbedder()
        index = semantic.SemanticIndex(embedder=second, cache_path=cache)
        index.build([BIOLOGY, PHYSICS, "A third, brand new note about leaves."])
        assert second.calls == 1 and index.embedded_now == 1

        other_model = FakeEmbedder()
        other_model.name = "another-model"
        third = semantic.SemanticIndex(embedder=other_model, cache_path=cache)
        third.build([BIOLOGY])
        assert other_model.calls == 1  # a different model never reuses old numbers
    finally:
        shutil.rmtree(folder, ignore_errors=True)


def test_retriever_adds_notes_found_only_by_meaning():
    folder = _library()
    try:
        retriever = KnowledgeRetriever(folder)
        assert retriever.semantic_status() == "off" or retriever.semantic is not None

        retriever.semantic = None  # make sure we start from plain word search
        words_only = retriever.search(QUESTION, top_k=3)
        assert all(r["filename"] != "biology.txt" or r["score"] < 1.5 for r in words_only), words_only

        assert retriever.enable_semantic(embedder=FakeEmbedder(), cache_path=None)
        assert retriever.semantic_status() == "on"
        results = retriever.search(QUESTION, top_k=3)
        assert results and results[0]["filename"] == "biology.txt"
        assert results[0]["via"] == "meaning"
        assert results[0]["score"] >= 1.5          # good enough for the chatbot to trust it
        assert all(r["filename"] != "physics.txt" for r in results)

        # Adding a document refreshes the index.
        with open(os.path.join(folder, "more.txt"), "w", encoding="utf-8") as f:
            f.write("Green plants make food. The leaf makes sugar from light.")
        retriever.refresh_cache()
        names = [r["filename"] for r in retriever.search(QUESTION, top_k=3)]
        assert "more.txt" in names, names
    finally:
        shutil.rmtree(folder, ignore_errors=True)


def test_word_matches_that_also_match_in_meaning_rank_higher():
    folder = _library()
    try:
        retriever = KnowledgeRetriever(folder)
        question = "Leaves produce glucose using sunlight"
        retriever.semantic = None
        plain = retriever.search(question, top_k=1)[0]["score"]
        retriever.enable_semantic(embedder=FakeEmbedder(), cache_path=None)
        boosted = retriever.search(question, top_k=1)[0]
        assert boosted["filename"] == "biology.txt"
        assert boosted["score"] > plain and boosted["via"] == "words+meaning"
    finally:
        shutil.rmtree(folder, ignore_errors=True)


def test_a_failing_model_switches_itself_off_and_word_search_continues():
    class Broken(FakeEmbedder):
        def embed(self, texts, is_query=False):
            raise RuntimeError("model download failed")

    folder = _library()
    try:
        retriever = KnowledgeRetriever(folder)
        retriever.enable_semantic(embedder=Broken(), cache_path=None)
        results = retriever.search("Newton force mass acceleration", top_k=3)
        assert results and results[0]["filename"] == "physics.txt"   # word search still works
        assert retriever.semantic is None
        assert retriever.semantic_status().startswith("error: model download failed")
    finally:
        shutil.rmtree(folder, ignore_errors=True)


def test_switch_off_and_missing_package():
    os.environ["SEMANTIC_SEARCH"] = "0"
    try:
        assert semantic.wanted() is False
    finally:
        del os.environ["SEMANTIC_SEARCH"]
    assert semantic.wanted() is True
    assert isinstance(semantic.package_installed(), bool)


# ---------------------------------------------------------------- streaming

class FakeLlama(BaseHTTPRequestHandler):
    """Answers like llama-server: a normal JSON reply, or server-sent events when stream=true."""

    pieces = ["Photo", "synthesis ", "makes ", "glucose", "."]
    stop_reason = "stop"

    def log_message(self, *args):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        self.send_response(200)
        if body.get("stream"):
            self.send_header("Content-Type", "text/event-stream")
            self.end_headers()
            for piece in self.pieces:
                event = {"choices": [{"delta": {"content": piece}, "finish_reason": None}]}
                self.wfile.write(("data: " + json.dumps(event) + "\n\n").encode())
                self.wfile.flush()
            last = {"choices": [{"delta": {}, "finish_reason": self.stop_reason}]}
            self.wfile.write(("data: " + json.dumps(last) + "\n\n").encode())
            self.wfile.write(b"data: [DONE]\n\n")
        else:
            reply = {"choices": [{"message": {"content": "".join(self.pieces)},
                                  "finish_reason": self.stop_reason}]}
            data = json.dumps(reply).encode()
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)


def _server():
    server = HTTPServer(("127.0.0.1", 0), FakeLlama)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def _engine(server):
    from ai_engine import AIEngine

    engine = AIEngine()
    engine.local_url = f"http://127.0.0.1:{server.server_port}/v1/chat/completions"
    return engine


MESSAGES = [{"role": "system", "content": "Be brief."},
            {"role": "user", "content": "What is photosynthesis?"}]


def test_streaming_sends_growing_text_and_returns_the_same_answer():
    server = _server()
    try:
        engine = _engine(server)
        plain = engine.generate_local(MESSAGES)

        seen = []
        engine.stream_callback = seen.append
        streamed = engine.generate_local(MESSAGES)
        engine.stream_callback = None

        assert streamed == plain == "Photosynthesis makes glucose."
        shown = [s for s in seen if s]
        assert len(shown) == 5 and shown[0] == "Photo" and shown[-1] == streamed
        assert all(b.startswith(a) for a, b in zip(shown, shown[1:]))  # text only grows
    finally:
        server.shutdown()


def test_a_broken_display_callback_never_breaks_the_answer():
    server = _server()
    try:
        engine = _engine(server)

        def explode(text):
            raise ValueError("screen closed")

        engine.stream_callback = explode
        assert engine.generate_local(MESSAGES) == "Photosynthesis makes glucose."
    finally:
        server.shutdown()


def test_ask_with_info_passes_the_callback_and_always_clears_it():
    import chatbot

    bot = chatbot.StudentChatbot()
    bot.use_wikipedia = False
    captured = {}

    def fake_ask(question):
        captured["callback"] = bot.ai_engine.stream_callback
        raise RuntimeError("boom")

    bot.ask = fake_ask
    marker = lambda text: None  # noqa: E731
    try:
        bot.ask_with_info("hello", stream_callback=marker)
    except RuntimeError:
        pass
    assert captured["callback"] is marker
    assert bot.ai_engine.stream_callback is None


# ---------------------------------------------------------------- v9.1

def test_cut_off_list_item_is_detected_but_complete_answers_are_not():
    from ai_engine import AIEngine

    engine = AIEngine()
    engine._current_messages = MESSAGES
    cut = "Plants make food in two steps.\n1. Light reactions split water.\n2. The Calvin cycle makes glucose.\n3. **Oxygen"
    assert engine.looks_truncated(cut, "length") is True
    assert engine.looks_truncated("The answer is **glucose", "length") is True       # unclosed bold
    done = "Plants make glucose from carbon dioxide and water using light energy."
    assert engine.looks_truncated(done, "length") is False
    assert engine.looks_truncated(done + "\n3. Oxygen is released.", "length") is False
    assert engine.looks_truncated(cut, "stop") is False                               # normal finishes untouched


def test_join_parts():
    from ai_engine import AIEngine

    join = AIEngine._join_parts
    assert join("", "b") == "b" and join("a", "") == "a"
    assert join("It makes", "glucose.") == "It makes glucose."
    assert join("It makes glucose", ".") == "It makes glucose."
    assert join("Line one\n", "Line two") == "Line one\nLine two"


def test_more_room_for_how_and_why_questions():
    from ai_engine import AIEngine

    engine = AIEngine()
    assert engine.select_local_tokens("how does photosynthesis work") == engine.local_explain_tokens == 224
    assert engine.select_local_tokens("why is the sky blue") == 224
    assert engine.select_local_tokens("what is photosynthesis?") == engine.local_short_tokens
    assert engine.select_local_tokens("explain ohm's law") == engine.local_technical_tokens


class FakeLlamaCutOff(BaseHTTPRequestHandler):
    """First reply is cut off by the length limit, the second one finishes the answer."""

    replies = [("Photosynthesis has two stages.\n1. Light reactions.\n2. Calvin cycle.\n3. **Oxygen", "length"),
               ("is released as a by-product.", "stop")]
    count = 0

    def log_message(self, *args):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        text, reason = self.replies[min(type(self).count, len(self.replies) - 1)]
        type(self).count += 1
        self.send_response(200)
        if body.get("stream"):
            self.send_header("Content-Type", "text/event-stream")
            self.end_headers()
            for word in text.split(" "):
                event = {"choices": [{"delta": {"content": word + " "}, "finish_reason": None}]}
                self.wfile.write(("data: " + json.dumps(event) + "\n\n").encode())
            last = {"choices": [{"delta": {}, "finish_reason": reason}]}
            self.wfile.write(("data: " + json.dumps(last) + "\n\ndata: [DONE]\n\n").encode())
        else:
            data = json.dumps({"choices": [{"message": {"content": text}, "finish_reason": reason}]}).encode()
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)


def _cutoff_run(stream):
    FakeLlamaCutOff.count = 0
    server = HTTPServer(("127.0.0.1", 0), FakeLlamaCutOff)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        engine = _engine(server)
        seen = []
        engine.stream_callback = seen.append if stream else None
        return engine.generate_local(MESSAGES), seen
    finally:
        server.shutdown()


def test_a_cut_off_answer_is_continued_and_joined_not_replaced():
    answer, _ = _cutoff_run(stream=False)
    assert answer.startswith("Photosynthesis has two stages.")
    assert answer.endswith("**Oxygen is released as a by-product.")
    assert answer.count("Photosynthesis has two stages.") == 1


def test_streaming_keeps_the_first_part_visible_during_the_retry():
    answer, seen = _cutoff_run(stream=True)
    assert answer.endswith("**Oxygen is released as a by-product.")
    shown = [t for t in seen if t]
    assert shown[-1].strip() == answer
    # while the continuation arrives the earlier text must still be on screen
    assert any(t.startswith("Photosynthesis has two stages.") and "is released" in t for t in shown)


def test_typed_gemini_key_is_session_only_and_empty_keeps_environment_key():
    from ai_engine import AIEngine

    engine = AIEngine()
    sentinel = object()
    engine.gemini_client = sentinel
    assert engine.has_key() is True
    assert engine.set_gemini_key("") is True and engine.gemini_client is sentinel
    assert engine.set_gemini_key("   ") is True and engine.gemini_client is sentinel
    try:
        import google.genai  # noqa: F401
    except ImportError:
        return
    assert engine.set_gemini_key("typed-test-key") is True
    assert engine.gemini_client is not sentinel and engine.has_key()
    assert engine.set_gemini_key("typed-test-key") is True


if __name__ == "__main__":
    test_index_finds_meaning_and_applies_threshold()
    test_cache_means_each_text_is_embedded_once()
    test_retriever_adds_notes_found_only_by_meaning()
    test_word_matches_that_also_match_in_meaning_rank_higher()
    test_a_failing_model_switches_itself_off_and_word_search_continues()
    test_switch_off_and_missing_package()
    test_streaming_sends_growing_text_and_returns_the_same_answer()
    test_a_broken_display_callback_never_breaks_the_answer()
    test_ask_with_info_passes_the_callback_and_always_clears_it()
    test_cut_off_list_item_is_detected_but_complete_answers_are_not()
    test_join_parts()
    test_more_room_for_how_and_why_questions()
    test_a_cut_off_answer_is_continued_and_joined_not_replaced()
    test_streaming_keeps_the_first_part_visible_during_the_retry()
    test_typed_gemini_key_is_session_only_and_empty_keeps_environment_key()
    print("All v9 tests passed.")
