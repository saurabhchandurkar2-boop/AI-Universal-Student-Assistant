"""
wiki_search.py - free Wikipedia lookup (no API key).

Used when the student's own notes do not contain a good match, so the model
gets real text about the topic instead of answering from memory alone.

lookup(question) returns a list of {"title", "extract", "url"} (possibly empty).
It never raises: on any network problem it returns an empty list.
"""
import re
import time

import requests

API_URL = "https://{lang}.wikipedia.org/w/api.php"
USER_AGENT = "AI-Universal-Student-Assistant/1.0 (educational project; https://github.com)"
TIMEOUT_SECONDS = 6
CACHE_SECONDS = 3600
MAX_CHARS = 1100

_cache = {}

QUESTION_WORDS = re.compile(
    r"^(please\s+)?(can you\s+|could you\s+)?"
    r"(tell me about|tell me|explain to me|explain|describe|define|what is|what are|what was|what were|"
    r"what's|who is|who was|who were|who are|where is|where was|when was|when did|why is|why are|"
    r"why did|why does|how does|how do|how did|how is|give me|write about|teach me|meaning of)\s+",
    re.IGNORECASE,
)
FILLER_START = re.compile(r"^(the|a|an|about)\s+", re.IGNORECASE)
GREETING = re.compile(
    r"^(hi|hello|hey|thanks|thank you|ok|okay|good (morning|evening|night)|bye|how are you)\b",
    re.IGNORECASE,
)
STOPWORDS = set(
    "a an and are as at be by do does for from how in is it of on or that the this to was were what when "
    "where which who why with you your me my i can could please tell about explain define".split()
)


def clean_query(question: str) -> str:
    """Turn a question into a search phrase: 'What is the Calvin cycle?' -> 'Calvin cycle'."""
    text = (question or "").strip().strip("?!. ")
    text = QUESTION_WORDS.sub("", text)
    text = FILLER_START.sub("", text)
    return text.strip()


def looks_like_topic_question(question: str) -> bool:
    text = (question or "").strip()
    if len(text) < 4 or GREETING.match(text):
        return False
    # Calculations and pure numbers are handled elsewhere.
    if not re.search(r"[A-Za-z]{3,}", text):
        return False
    return True


def _content_words(text: str) -> set:
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in STOPWORDS and len(w) > 2}


def _is_relevant(query: str, title: str, extract: str) -> bool:
    """The page must share at least one real word with what was asked."""
    words = _content_words(query)
    if not words:
        return False
    haystack = _content_words(title) | _content_words(extract[:400])
    return bool(words & haystack)


def _fetch(query: str, lang: str, limit: int):
    params = {
        "action": "query",
        "generator": "search",
        "gsrsearch": query,
        "gsrlimit": limit,
        "prop": "extracts|info",
        "exintro": 1,
        "explaintext": 1,
        "exchars": MAX_CHARS,
        "exlimit": limit,
        "inprop": "url",
        "redirects": 1,
        "format": "json",
        "formatversion": 2,
    }
    response = requests.get(
        API_URL.format(lang=lang),
        params=params,
        headers={"User-Agent": USER_AGENT},
        timeout=TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    pages = response.json().get("query", {}).get("pages", [])
    pages = sorted(pages, key=lambda p: p.get("index", 99))
    results = []
    for page in pages:
        extract = " ".join((page.get("extract") or "").split())
        title = page.get("title") or ""
        url = page.get("fullurl") or ""
        if not extract or not title:
            continue
        if "may refer to" in extract[:120] or title.lower().endswith("(disambiguation)"):
            continue
        results.append({"title": title, "extract": extract, "url": url})
    return results


def lookup(question: str, lang: str = "en", limit: int = 2):
    """Wikipedia pages relevant to the question. Returns [] on any problem."""
    if not looks_like_topic_question(question):
        return []

    query = clean_query(question)
    if len(query) < 3:
        return []

    key = (lang, query.lower(), limit)
    cached = _cache.get(key)
    if cached and time.time() - cached[0] < CACHE_SECONDS:
        return cached[1]

    try:
        pages = _fetch(query, lang, limit)
    except Exception:
        return []

    pages = [p for p in pages if _is_relevant(query, p["title"], p["extract"])]
    _cache[key] = (time.time(), pages)
    return pages


def as_context(pages: list) -> str:
    """Text block handed to the model."""
    return "\n\n".join(f"Wikipedia - {p['title']}: {p['extract']}" for p in pages)


if __name__ == "__main__":
    import sys

    q = " ".join(sys.argv[1:]) or "What is photosynthesis?"
    found = lookup(q)
    if not found:
        print("No Wikipedia result (or no internet connection).")
    for p in found:
        print(f"{p['title']}  {p['url']}\n  {p['extract'][:200]}...\n")
