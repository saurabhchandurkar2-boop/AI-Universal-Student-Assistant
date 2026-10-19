"""Tests for the Wikipedia lookup. They use a stand-in for the network. Run: python tests/test_wiki.py"""
import os
import sys
import types

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import wiki_search as w  # noqa: E402


def _fake_get(pages, calls):
    def get(url, params=None, headers=None, timeout=None):
        calls.append((url, params, headers))
        body = {"query": {"pages": pages}}
        return types.SimpleNamespace(raise_for_status=lambda: None, json=lambda: body)
    return get


def test_clean_query():
    assert w.clean_query("What is the Calvin cycle?") == "Calvin cycle"
    assert w.clean_query("Who was Albert Einstein") == "Albert Einstein"
    assert w.clean_query("explain photosynthesis") == "photosynthesis"
    assert w.clean_query("Tell me about the French Revolution!") == "French Revolution"
    assert w.clean_query("capital of France") == "capital of France"


def test_gate():
    assert not w.looks_like_topic_question("hi")
    assert not w.looks_like_topic_question("hello there")
    assert not w.looks_like_topic_question("12 + 5")
    assert w.looks_like_topic_question("what is photosynthesis")


def test_lookup_filters_and_caches():
    w._cache.clear()
    calls = []
    pages = [
        {"index": 2, "title": "Chloroplast", "extract": "A chloroplast is where photosynthesis happens in plants.",
         "fullurl": "https://en.wikipedia.org/wiki/Chloroplast"},
        {"index": 1, "title": "Photosynthesis", "extract": "Photosynthesis is a process used by plants to convert light energy.",
         "fullurl": "https://en.wikipedia.org/wiki/Photosynthesis"},
        {"index": 3, "title": "Mercury (disambiguation)", "extract": "Mercury may refer to: the planet...", "fullurl": "x"},
        {"index": 4, "title": "Unrelated", "extract": "Something about cars and engines.", "fullurl": "y"},
    ]
    w.requests.get = _fake_get(pages, calls)
    found = w.lookup("What is photosynthesis?")
    assert [p["title"] for p in found] == ["Photosynthesis", "Chloroplast"]   # ordered, junk removed
    assert found[0]["url"].endswith("/Photosynthesis")
    assert calls[0][1]["gsrsearch"] == "photosynthesis"
    assert "User-Agent" in calls[0][2]
    w.lookup("what is photosynthesis")
    assert len(calls) == 1          # second call came from the cache
    assert "Wikipedia - Photosynthesis:" in w.as_context(found)


def test_network_failure_is_silent():
    w._cache.clear()

    def boom(*a, **k):
        raise RuntimeError("no internet")

    w.requests.get = boom
    assert w.lookup("what is photosynthesis") == []
    assert w.lookup("hi") == []


if __name__ == "__main__":
    test_clean_query()
    test_gate()
    test_lookup_filters_and_caches()
    test_network_failure_is_silent()
    print("All wiki tests passed.")
