"""
chunk_filter.py - keep useless pieces of a document out of the answers.

Large PDFs start with a cover, a copyright page and a table of contents. Those
pieces mention every topic by name, so a word-matching search often returns them
instead of the real explanation. This module recognises them so they can be
dropped, and also finds which PDF page a piece of text came from.

Page numbers work for PDFs added after this version (see write_page_index).
"""
import json
import os
import re

_DOT_LEADER_LINE = re.compile(r"\.{4,}\s*[0-9ivxlc]+\s*$", re.IGNORECASE)
_ENDS_WITH_NUMBER = re.compile(r"\s[0-9]{1,4}\s*$")
_CONTENTS_HEADING = re.compile(
    r"^\s*(table\s+of\s+contents|contents|list\s+of\s+(figures|tables))\s*$",
    re.IGNORECASE | re.MULTILINE,
)
_BOILERPLATE = re.compile(
    r"\b(isbn|all\s+rights\s+reserved|copyright\s*(?:©|\(c\))|"
    r"first\s+published|printed\s+in|no\s+part\s+of\s+this\s+(?:book|publication))\b",
    re.IGNORECASE,
)


def _toc_style(lines) -> bool:
    """Does this piece look like (part of) a table of contents?"""
    dotted = sum(1 for l in lines if _DOT_LEADER_LINE.search(l))
    numbered = sum(1 for l in lines if _ENDS_WITH_NUMBER.search(l) or _DOT_LEADER_LINE.search(l))
    if dotted >= 2:
        return True
    if _CONTENTS_HEADING.search("\n".join(lines)) and numbered >= 2:
        return True
    return len(lines) >= 5 and numbered / len(lines) >= 0.7


def clean_chunk(text: str):
    """Remove table-of-contents lines from a piece of text.

    Returns (keep, cleaned). keep is False for a cover page, a copyright page or a
    contents page. When a piece is a contents list followed by real text, the real
    text is kept and the list lines are removed.
    """
    text = text or ""
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if not lines:
        return False, ""

    if _toc_style(lines):
        kept = [
            l for l in lines
            if not (_DOT_LEADER_LINE.search(l) or _ENDS_WITH_NUMBER.search(l)
                    or _CONTENTS_HEADING.match(l))
        ]
        words = len(re.findall(r"[A-Za-z]{2,}", " ".join(kept)))
        if words < 12:
            return False, ""
        return True, "\n".join(kept)

    words = len(re.findall(r"[A-Za-z]{2,}", text))
    if _BOILERPLATE.search(text) and words < 70:
        return False, ""

    return True, text


def is_low_value(text: str) -> bool:
    """True for a cover page, copyright page or table of contents."""
    return not clean_chunk(text)[0]


def filter_results(results):
    """Drop covers and contents pages from retriever results (keeps the order).

    A piece that is a contents list followed by real text is kept, without the list.
    """
    if not isinstance(results, list):
        return results
    kept = []
    for item in results:
        if isinstance(item, dict):
            key = "text" if "text" in item else ("content" if "content" in item else None)
            body = str(item.get(key) or "") if key else ""
            keep, cleaned = clean_chunk(body)
            if not keep:
                continue
            if key and cleaned != body:
                item = dict(item)
                item[key] = cleaned
        kept.append(item)
    return kept


# --------------------------------------------------
# Page numbers
# --------------------------------------------------
# When a PDF is added, a small "<name>.pages.json" file is saved next to the text
# file. It holds the text of every page, so a piece of an answer can be traced
# back to its page. Documents added before this version simply have no page.

PAGE_INDEX_SUFFIX = ".pages.json"
_page_cache = {}


def _squash(text: str) -> str:
    return " ".join((text or "").split()).lower()


def _index_path(txt_path: str) -> str:
    base = txt_path[:-4] if txt_path.lower().endswith(".txt") else txt_path
    return base + PAGE_INDEX_SUFFIX


def write_page_index(directory: str, name: str, pages) -> None:
    """Save the text of each PDF page. Never raises: page numbers are optional."""
    try:
        with open(os.path.join(directory, name + PAGE_INDEX_SUFFIX), "w", encoding="utf-8") as f:
            json.dump({"pages": [_squash(p) for p in pages]}, f)
    except Exception:
        pass


def remove_page_index(directory: str, name: str) -> None:
    try:
        os.remove(os.path.join(directory, name + PAGE_INDEX_SUFFIX))
    except OSError:
        pass


def _pages_of_file(txt_path: str):
    path = _index_path(txt_path)
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        return None
    cached = _page_cache.get(path)
    if cached and cached[0] == mtime:
        return cached[1]
    try:
        with open(path, "r", encoding="utf-8") as f:
            pages = json.load(f).get("pages") or None
    except Exception:
        pages = None
    _page_cache[path] = (mtime, pages)
    return pages


def page_of(path: str, text: str):
    """PDF page number (starting at 1) where this piece of text begins, or None."""
    if not path or not text:
        return None
    pages = _pages_of_file(path)
    if not pages:
        return None
    needle = _squash(text)[:60]
    if len(needle) < 12:
        return None
    for number, page in enumerate(pages, start=1):
        if needle in page:
            return number
    return None
