"""
Notes summarizer.

Uses the local llama-server that the chatbot already uses
(http://127.0.0.1:8080), so no second model is loaded. Long notes are split
into chunks, each chunk is summarized, and the partial summaries are combined.

If the llama server is not running, it falls back to loading Qwen through
`transformers` (slow, large download).
"""
import os

import requests

LLAMA_URL = os.getenv(
    "LLAMA_URL",
    "http://127.0.0.1:8080/v1/chat/completions"
)

# About 3,500 characters is roughly 900 tokens, which fits a 2048-token context.
CHUNK_CHARS = 3500
MAX_CHUNKS = 8

SYSTEM_PROMPT = (
    "You are a helpful study assistant. Summarize study notes clearly "
    "and briefly. Do not add facts that are not in the notes."
)

_fallback_pipeline = None


def _split_chunks(text, size=CHUNK_CHARS):
    """Split text into chunks, preferring paragraph or sentence breaks."""
    text = text.strip()
    chunks = []
    while len(text) > size:
        cut = max(
            text.rfind("\n\n", 0, size),
            text.rfind(". ", 0, size)
        )
        if cut < size // 2:
            cut = size
        chunks.append(text[:cut + 1].strip())
        text = text[cut + 1:].strip()
    if text:
        chunks.append(text)
    return chunks


def _ask_server(instruction, text, max_tokens=150):
    response = requests.post(
        LLAMA_URL,
        json={
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"{instruction}\n\n{text}"}
            ],
            "max_tokens": max_tokens,
            "temperature": 0.2
        },
        timeout=120
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"].strip()


def _ask_fallback(instruction, text):
    global _fallback_pipeline
    if _fallback_pipeline is None:
        from transformers import pipeline
        print("Llama server not found. Loading fallback summarizer...")
        _fallback_pipeline = pipeline(
            "text-generation",
            model="Qwen/Qwen2.5-0.5B-Instruct",
            max_new_tokens=120
        )
    result = _fallback_pipeline(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"{instruction}\n\n{text}"}
        ],
        do_sample=False
    )
    generated = result[0]["generated_text"]
    if isinstance(generated, list):
        return generated[-1]["content"].strip()
    return generated.strip()


def _ask(instruction, text, ask=None):
    if ask is not None:
        # Hosted mode: ask(system, user) calls Gemini with the visitor's key.
        return ask(SYSTEM_PROMPT, f"{instruction}\n\n{text}")
    try:
        return _ask_server(instruction, text)
    except requests.exceptions.ConnectionError:
        return _ask_fallback(instruction, text)


def summarize_text(text, ask=None):
    if not text or not text.strip():
        return "Please enter some notes to summarize."

    chunks = _split_chunks(text)[:MAX_CHUNKS]

    if len(chunks) == 1:
        return _ask("Summarize these notes in 2 or 3 sentences:", chunks[0], ask)

    parts = [
        _ask("Summarize this part of the notes in 1 or 2 sentences:", chunk, ask)
        for chunk in chunks
    ]
    return _ask(
        "Combine these partial summaries into one short summary "
        "of 3 to 4 sentences:",
        "\n".join(f"- {p}" for p in parts),
        ask
    )


if __name__ == "__main__":
    notes = input("\nEnter your notes:\n")
    print("\n===== SUMMARY =====")
    print(summarize_text(notes))
