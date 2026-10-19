"""
quiz.py - practice questions made from a study document.

Two modes:

1. Fill in the blank ("cloze"): picks sentences from the notes and hides a key
   term. Needs no AI, is instant, and always works.
2. AI questions: asks the model for short question/answer pairs. A small local
   model can produce messy output, so if it cannot be parsed the quiz falls
   back to fill in the blank.

Both return a list of {"question", "answer", "kind"} dictionaries.
"""
import random
import re

import requests

LLAMA_URL_DEFAULT = "http://127.0.0.1:8080/v1/chat/completions"

STOPWORDS = set("""
about above after again against along also always among because before being below between both
cannot could does doing during each either every first from further given have having here
however into itself just later less many more most much must never next once only other over
rather same several should since some such than that their them then there these they this those
through thus under until upon using very want were what when where whether which while whose will
with within without would your
""".split())

MIN_WORDS = 6
MAX_WORDS = 32


# --------------------------------------------------
# Fill in the blank
# --------------------------------------------------

FORMULA_LINE = re.compile(r"\s*([A-Za-z][A-Za-z0-9_\u00b2\u00b3]*)\s*=\s*(.+?)\s*")


def _is_equation_line(line: str) -> bool:
    return bool(FORMULA_LINE.fullmatch(line)) and len(line.split()) <= 14


def split_sentences(text: str) -> list:
    """Whole sentences from the prose of a document (formula lines are skipped)."""
    sentences = []
    for line in text.replace("\r", "\n").split("\n"):
        line = re.sub(r"\s+", " ", line).strip()
        if not line or _is_equation_line(line):
            continue
        for part in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(])", line):
            part = part.strip()
            words = part.split()
            if not (MIN_WORDS <= len(words) <= MAX_WORDS):
                continue
            if part.endswith(":") or "http" in part or part.count("|") > 1:
                continue
            if sum(c.isalpha() for c in part) < len(part) * 0.6:
                continue
            sentences.append(part)
    return sentences


def _word_frequencies(text: str) -> dict:
    freq = {}
    for word in re.findall(r"[A-Za-z][A-Za-z\-']{3,}", text.lower()):
        if word in STOPWORDS:
            continue
        freq[word] = freq.get(word, 0) + 1
    return freq


def _pick_blank(sentence: str, freq: dict):
    """Choose the best word in a sentence to hide, or None."""
    best, best_score = None, 0.0
    tokens = list(re.finditer(r"[A-Za-z][A-Za-z\-']*|\d+(?:\.\d+)?", sentence))
    for index, match in enumerate(tokens):
        word = match.group(0)
        low = word.lower()
        if low in STOPWORDS or len(word) < 4:
            continue
        # Never hide the first word of the sentence.
        if index == 0:
            continue
        score = 0.0
        if word[0].isdigit():
            score = 2.5
        elif word[0].isupper():
            score = 2.0 + 0.2 * len(word)
        elif freq.get(low, 0) >= 2:
            score = 1.0 + 0.3 * min(freq[low], 6) + 0.1 * len(word)
        if score > best_score:
            best, best_score = word, score
    if best and best.endswith("'s"):
        best = best[:-2]
    return best


def _prose_candidates(text: str, freq: dict) -> list:
    out = []
    for sentence in split_sentences(text):
        answer = _pick_blank(sentence, freq)
        if not answer:
            continue
        pattern = re.compile(r"\b" + re.escape(answer) + r"\b", re.IGNORECASE)
        blanked = pattern.sub("_____", sentence)
        if blanked == sentence:
            continue
        out.append({"question": blanked, "answer": answer, "kind": "blank",
                    "pos": text.find(sentence[:40])})
    return out


def _formula_candidates(text: str, rng) -> list:
    """Questions from equation lines such as 'I = V / R' and 'V = voltage in volts'."""
    lines = [re.sub(r"\s+", " ", l).strip() for l in text.replace("\r", "\n").split("\n")]
    title = next((l for l in lines if l), "")
    out = []
    heading = ""
    for line in lines:
        if not line:
            continue
        match = FORMULA_LINE.fullmatch(line)
        if not match or len(line.split()) > 14:
            if (len(line.split()) <= 8 and "." not in line and "=" not in line
                    and not line.endswith(":")):
                heading = line
            continue
        lhs, rhs = match.group(1), match.group(2)
        if "=" in rhs:
            continue  # worked example such as v = 0 + 2 x 5 = 10 m/s
        topic = (heading or title).replace("(", "- ").replace(")", "").strip()
        pos = text.find(line)

        words = [w for w in re.findall(r"[A-Za-z]{4,}", rhs) if w.lower() not in STOPWORDS]
        if words:
            # Definition line: "V = voltage in volts" -> hide the key word.
            answer = max(words, key=len)
            blanked = re.sub(r"\b" + re.escape(answer) + r"\b", "_____", line, count=1)
            out.append({"question": f"({topic}) {blanked}", "answer": answer,
                        "kind": "blank", "pos": pos})
            continue

        variables = re.findall(r"(?<![A-Za-z0-9])[A-Za-z][\u00b2\u00b3]?(?![A-Za-z0-9])", rhs)
        if not variables or not re.search(r"[+\-\u00d7*/^\u00f7x]", rhs):
            continue
        if rng.random() < 0.4:
            blanked, answer = f"_____ = {rhs}", lhs
        else:
            answer = rng.choice(variables)
            blanked = f"{lhs} = " + re.sub(
                r"(?<![A-Za-z0-9])" + re.escape(answer) + r"(?![A-Za-z0-9\u00b2\u00b3])",
                "_____", rhs, count=1)
        out.append({"question": f"Complete the formula ({topic}): {blanked}",
                    "answer": answer, "kind": "formula", "pos": pos})
    return out


def make_cloze(text: str, n: int = 5, seed=None) -> list:
    """Fill-in-the-blank questions from sentences and formulas. Up to n questions."""
    rng = random.Random(seed)
    freq = _word_frequencies(text)

    pool = _prose_candidates(text, freq) + _formula_candidates(text, rng)
    rng.shuffle(pool)

    questions, seen = [], set()
    for item in pool:
        key = (item["answer"].lower(), item["question"][:40])
        if key in seen:
            continue
        seen.add(key)
        questions.append(item)
        if len(questions) >= n:
            break

    questions.sort(key=lambda q: q.get("pos", 0))
    for q in questions:
        q.pop("pos", None)
    return questions


# --------------------------------------------------
# AI questions
# --------------------------------------------------

def parse_qa(output: str, n: int) -> list:
    """Parse 'Q1: ... A1: ...' style output. Tolerates small formatting changes."""
    output = (output or "").replace("**", "")
    pattern = re.compile(
        r"(?:^|\n)\s*(?:Q(?:uestion)?\s*\d*\s*[:.)\-]|\d+[.)])\s*(.+?)\s*\n+\s*"
        r"(?:A(?:nswer)?\s*\d*\s*[:.)\-])\s*(.+?)(?=\n\s*(?:Q(?:uestion)?\s*\d*\s*[:.)\-]|\d+[.)])|\Z)",
        re.DOTALL | re.IGNORECASE,
    )
    questions = []
    for match in pattern.finditer(output):
        question = " ".join(match.group(1).split())
        answer = " ".join(match.group(2).split())
        if len(question) < 8 or not answer or len(answer) > 400:
            continue
        if not question.endswith("?"):
            question += "?"
        questions.append({"question": question, "answer": answer, "kind": "qa"})
        if len(questions) >= n:
            break
    return questions


def _window(text: str, size: int, rng) -> str:
    text = text.strip()
    if len(text) <= size:
        return text
    start = rng.randint(0, len(text) - size)
    # Start at a paragraph or sentence boundary when one is close.
    boundary = max(text.rfind("\n\n", 0, start + 1), text.rfind(". ", 0, start + 1))
    if boundary != -1 and start - boundary < 600:
        start = boundary + 1
    return text[start:start + size].strip()


def make_ai_questions(text: str, n: int, ask, window_chars: int = 2500, seed=None):
    """Ask the model for n question/answer pairs. Returns a possibly empty list."""
    rng = random.Random(seed)
    excerpt = _window(text, window_chars, rng)
    system = "You are a teacher who writes short quiz questions from study notes."
    user = (
        f"Write {n} short quiz questions with answers, using only the notes below.\n"
        "Use exactly this format and nothing else:\n"
        "Q1: <question>\nA1: <short answer>\nQ2: <question>\nA2: <short answer>\n\n"
        f"Notes:\n{excerpt}"
    )
    try:
        output = ask(system, user, 60 + 70 * n)
    except Exception:
        return []
    return parse_qa(output, n)


def make_quiz(text: str, n: int = 5, mode: str = "blank", ask=None, seed=None):
    """Build a quiz. Returns (questions, note).

    note is a short message for the user, for example when the AI mode had to
    fall back to fill in the blank.
    """
    text = (text or "").strip()
    if len(text) < 80:
        return [], "This document has too little text to make a quiz."

    if mode == "ai" and ask is not None:
        questions = make_ai_questions(text, n, ask, seed=seed)
        if questions:
            return questions, ""
        questions = make_cloze(text, n, seed=seed)
        if questions:
            return questions, (
                "The AI answer could not be turned into questions, "
                "so this is a fill-in-the-blank quiz instead."
            )
        return [], "Could not make questions from this document."

    questions = make_cloze(text, n, seed=seed)
    if not questions:
        return [], "Could not find suitable sentences in this document."
    return questions, ""


def check_blank(given: str, expected: str, kind: str = "blank") -> bool:
    if kind == "formula":
        return (given or "").strip() == (expected or "").strip()
    clean = lambda s: re.sub(r"[^a-z0-9.]+", "", (s or "").lower())
    return bool(clean(given)) and clean(given) == clean(expected)


# --------------------------------------------------
# Ask the local llama-server (used when the app runs locally)
# --------------------------------------------------

def ask_llama_server(system: str, user: str, max_tokens: int = 300) -> str:
    import os
    url = os.getenv("LLAMA_URL", LLAMA_URL_DEFAULT)
    response = requests.post(
        url,
        json={
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "max_tokens": max_tokens,
            "temperature": 0.4,
        },
        timeout=300,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"].strip()
