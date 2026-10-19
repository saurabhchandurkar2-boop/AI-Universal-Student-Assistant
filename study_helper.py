"""
study_helper.py - writing and learning helper.

Four tasks, each built as a prompt for whichever model is available (local
Qwen through llama-server, or Gemini in the online demo):

    Explain a topic        - clear explanation at the chosen level
    Write an essay/answer  - structured piece with introduction and conclusion
    Improve my writing     - fix spelling, grammar and clarity, keep the meaning
    Make study notes       - headings, bullet points and key terms from text
"""

TASKS = [
    "Explain a topic",
    "Write an essay or answer",
    "Improve my writing",
    "Make study notes",
]

LEVELS = {
    "Simple (class 6 to 8)": "a school student in classes 6 to 8, using simple words and short sentences",
    "Standard (class 9 to 12)": "a high school student in classes 9 to 12",
    "Detailed (college)": "a college student, with precise terms and more depth",
}

LANGUAGES = [
    "English", "Hindi", "Marathi", "Bengali", "Tamil", "Telugu",
    "Spanish", "French", "German", "Arabic",
]

# name -> (approximate words, max tokens for the model)
LENGTHS = {
    "Short": (120, 300),
    "Medium": (250, 520),
    "Long": (500, 900),
}

PLACEHOLDERS = {
    "Explain a topic": "For example: How does photosynthesis work?",
    "Write an essay or answer": "For example: The importance of renewable energy",
    "Improve my writing": "Paste the text you want improved",
    "Make study notes": "Paste the text you want turned into notes",
}

SYSTEM_PROMPT = (
    "You are a patient, accurate teacher and writing coach. "
    "Do not invent facts. If you are unsure about something, say so briefly."
)


def build_request(task, text, level, language, length, facts="", max_input_chars=6000):
    """Return (system_prompt, user_prompt, max_tokens). Raises ValueError for empty input."""
    text = (text or "").strip()
    if not text:
        raise ValueError("Please type or paste something first.")
    if task not in TASKS:
        raise ValueError("Unknown task.")

    words, max_tokens = LENGTHS.get(length, LENGTHS["Medium"])
    audience = LEVELS.get(level, LEVELS["Standard (class 9 to 12)"])
    language_line = (
        f"Write the answer in {language}."
        if language else
        "Write in the same language as the text."
    )

    if task == "Explain a topic":
        instruction = (
            f"Explain the topic below to {audience}. Use short paragraphs and one simple "
            f"example. About {words} words. {language_line}"
        )
    elif task == "Write an essay or answer":
        instruction = (
            f"Write a well-structured essay or answer on the topic below for {audience}, "
            f"with an introduction, a body and a conclusion. About {words} words. {language_line}"
        )
    elif task == "Improve my writing":
        instruction = (
            "Improve the writing below: fix spelling and grammar and make it clearer, "
            "but keep the meaning and the author's ideas. Return only the improved text. "
            f"{language_line}"
        )
        max_tokens = max(max_tokens, 600)
    else:
        instruction = (
            f"Turn the text below into clear study notes for {audience}: short headings, "
            "bullet points, key terms and any formulas. Use only the information in the text. "
            f"{language_line}"
        )

    body = text[:max_input_chars]
    user = f"{instruction}\n\n"
    if facts and task in ("Explain a topic", "Write an essay or answer"):
        user += f"Use these facts when they are relevant:\n{facts[:2000]}\n\n"
    label = "Text" if task in ("Improve my writing", "Make study notes") else "Topic"
    user += f"{label}:\n{body}"
    return SYSTEM_PROMPT, user, max_tokens


def run(task, text, level, language, length, ask, facts="", max_input_chars=6000):
    """Build the prompt and ask the model. Returns the answer text."""
    system, user, max_tokens = build_request(
        task, text, level, language, length, facts, max_input_chars
    )
    answer = (ask(system, user, max_tokens) or "").strip()
    if not answer:
        raise ValueError("The model returned an empty answer. Please try again.")
    return answer
