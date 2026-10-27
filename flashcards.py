"""
flashcards.py - flashcards that come back at the right time (Leitner boxes).

Every card sits in a box from 1 to 5. A card you get right moves up a box and
comes back later; a card you miss goes back to box 1 and comes back at once.

    box 1: again now   box 2: after 1 day   box 3: after 3 days
    box 4: after 7 days   box 5: after 14 days

Pure Python, no AI and no extra downloads. Cards can be saved as JSON between
sessions and exported as CSV (for example to import into Anki).
"""
import csv
import hashlib
import io
import time

DAY = 24 * 60 * 60
MAX_BOX = 5
INTERVALS = {1: 0, 2: 1 * DAY, 3: 3 * DAY, 4: 7 * DAY, 5: 14 * DAY}
LEARNED_BOX = 4


def card_id(front: str) -> str:
    return hashlib.sha1(" ".join((front or "").split()).lower().encode("utf-8")).hexdigest()[:12]


def _number(value, kind):
    """A number from saved data; 0 when the value is missing or damaged."""
    try:
        return kind(value or 0)
    except (TypeError, ValueError):
        return kind(0)


class Deck:
    def __init__(self, cards=None):
        self.cards = [dict(c) for c in (cards or []) if c.get("front") and c.get("back")]

    # ---------------- adding and removing ----------------

    def add(self, front: str, back: str, source: str = "", now=None) -> bool:
        """Add one card. Returns False when the same question is already in the deck."""
        front, back = (front or "").strip(), (back or "").strip()
        if not front or not back:
            return False
        cid = card_id(front)
        if any(c["id"] == cid for c in self.cards):
            return False
        now = time.time() if now is None else now
        self.cards.append({
            "id": cid, "front": front, "back": back, "source": source or "",
            "box": 1, "due": now, "reviews": 0, "lapses": 0,
        })
        return True

    def add_questions(self, questions, source: str = "", now=None) -> int:
        """Add cards from quiz questions ({"question", "answer"}). Returns how many were new."""
        return sum(bool(self.add(q.get("question"), q.get("answer"), source, now)) for q in questions or [])

    def remove(self, cid: str) -> bool:
        before = len(self.cards)
        self.cards = [c for c in self.cards if c["id"] != cid]
        return len(self.cards) < before

    def clear(self) -> None:
        self.cards = []

    # ---------------- studying ----------------

    def due_cards(self, now=None) -> list:
        now = time.time() if now is None else now
        due = [c for c in self.cards if c["due"] <= now]
        return sorted(due, key=lambda c: (c["box"], c["due"]))

    def next_card(self, now=None):
        due = self.due_cards(now)
        return due[0] if due else None

    def grade(self, cid: str, correct: bool, now=None) -> bool:
        """Record an answer. Returns False for an unknown card."""
        now = time.time() if now is None else now
        for card in self.cards:
            if card["id"] == cid:
                card["reviews"] += 1
                if correct:
                    card["box"] = min(MAX_BOX, card["box"] + 1)
                else:
                    card["box"] = 1
                    card["lapses"] += 1
                card["due"] = now + INTERVALS[card["box"]]
                return True
        return False

    def seconds_until_next(self, now=None):
        """Seconds until the next card is due, 0 if one is due now, None for an empty deck."""
        if not self.cards:
            return None
        now = time.time() if now is None else now
        return max(0, min(c["due"] for c in self.cards) - now)

    def stats(self, now=None) -> dict:
        now = time.time() if now is None else now
        boxes = {b: 0 for b in range(1, MAX_BOX + 1)}
        for c in self.cards:
            boxes[c["box"]] += 1
        return {
            "total": len(self.cards),
            "due": len(self.due_cards(now)),
            "learned": sum(n for b, n in boxes.items() if b >= LEARNED_BOX),
            "boxes": boxes,
        }

    # ---------------- saving and exporting ----------------

    def to_list(self) -> list:
        return [dict(c) for c in self.cards]

    @classmethod
    def from_list(cls, data):
        cards = []
        for c in data if isinstance(data, list) else []:
            if not isinstance(c, dict) or not c.get("front") or not c.get("back"):
                continue
            box = c.get("box", 1)
            cards.append({
                "id": str(c.get("id") or card_id(c["front"])),
                "front": str(c["front"]), "back": str(c["back"]),
                "source": str(c.get("source", "")),
                "box": box if isinstance(box, int) and 1 <= box <= MAX_BOX else 1,
                "due": _number(c.get("due"), float),
                "reviews": _number(c.get("reviews"), int),
                "lapses": _number(c.get("lapses"), int),
            })
        return cls(cards)

    def to_csv(self) -> str:
        """Front, back, source. No header row, so it can be imported straight into Anki."""
        out = io.StringIO()
        writer = csv.writer(out, lineterminator="\n")
        for c in self.cards:
            writer.writerow([c["front"], c["back"], c["source"]])
        return out.getvalue()


def describe_wait(seconds) -> str:
    """'now', 'in 3 hours', 'in 2 days' ... for the next-card message."""
    if seconds is None:
        return ""
    if seconds <= 0:
        return "now"
    if seconds < 3600:
        return f"in {max(1, round(seconds / 60))} minutes"
    if seconds < DAY:
        hours = round(seconds / 3600)
        return f"in {hours} hour{'s' if hours != 1 else ''}"
    days = round(seconds / DAY)
    return f"in {days} day{'s' if days != 1 else ''}"
