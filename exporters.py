"""
exporters.py - turn a chat or a quiz into text a student can save or print.
"""

_ORIGINS = {
    "calc": "exact calculator",
    "web": "web search",
    "wikipedia": "Wikipedia",
    "notes": "your notes",
}


def chat_to_markdown(history, title: str = "Study chat") -> str:
    """A chat history (list of {"role", "content", "meta"}) as Markdown."""
    lines = [f"# {title}", ""]
    for message in history or []:
        role = "You" if message.get("role") == "user" else "Assistant"
        lines.append(f"**{role}:** {str(message.get('content', '')).strip()}")
        meta = message.get("meta") or {}
        notes = []
        origin = _ORIGINS.get(meta.get("origin"))
        if origin:
            notes.append(f"from {origin}")
        names = []
        for source in meta.get("sources") or []:
            label = source.get("filename", "")
            if source.get("page"):
                label += f" p.{source['page']}"
            if label and label not in names:
                names.append(label)
        if names:
            notes.append("sources: " + ", ".join(names))
        if notes:
            lines.append(f"*({'; '.join(notes)})*")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def quiz_to_text(questions, doc: str = "", answers: bool = True) -> str:
    """A quiz as plain text, with an answer key at the end when answers=True."""
    heading = f"Quiz: {doc}" if doc else "Quiz"
    lines = [heading, "=" * len(heading), ""]
    for number, item in enumerate(questions or [], start=1):
        lines.append(f"{number}. {item['question']}")
        lines.append("   Answer: ____________________")
        lines.append("")
    if answers and questions:
        lines.append("Answer key")
        lines.append("----------")
        for number, item in enumerate(questions, start=1):
            lines.append(f"{number}. {item['answer']}")
    return "\n".join(lines).rstrip() + "\n"
