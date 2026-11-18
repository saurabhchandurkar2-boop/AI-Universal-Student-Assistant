"""
semantic_check.py - see how meaning search behaves on YOUR notes.

Run it after:  pip install fastembed
    python semantic_check.py
    python semantic_check.py "how do plants make food" "what pushes an object"

The first run downloads a small model (about 80 MB), so it needs internet once.
It prints, for each question, the three notes closest in meaning and their
similarity (1.0 = same meaning). A note counts as a match when its similarity is
at least SEMANTIC_MIN_SIM (default 0.60). If good matches score just below that,
lower it, for example in PowerShell:  $env:SEMANTIC_MIN_SIM = "0.55"
"""
import os
import sys

import semantic

SAMPLE_QUESTIONS = [
    "how do plants make food",
    "what makes an object speed up",
    "who fought for india's freedom",
    "what is the capital of France",   # not in the notes: should score low
]


def main():
    if not semantic.package_installed():
        print("fastembed is not installed. Run:  pip install fastembed")
        return 1

    from knowledge.retriever import KnowledgeRetriever

    folder = "knowledge/documents"
    retriever = KnowledgeRetriever(folder)
    if not retriever.chunks:
        print(f"No notes found in {folder}. Add documents first (sidebar or documents_to_import).")
        return 1

    print(f"Loading the model and embedding {len(retriever.chunks)} piece(s) of notes...")
    retriever.enable_semantic()
    if not retriever._ensure_semantic():
        print("Meaning search could not start:", retriever.semantic_error)
        return 1

    threshold = retriever.semantic_min_sim
    questions = sys.argv[1:] or SAMPLE_QUESTIONS
    for question in questions:
        sims = retriever.semantic.similarities(question)
        order = sims.argsort()[::-1][:3]
        print(f"\nQ: {question}")
        for i in order:
            chunk = retriever.chunks[int(i)]
            mark = "MATCH" if sims[i] >= threshold else "below threshold"
            snippet = " ".join(chunk["text"].split())[:70]
            print(f"   {sims[i]:.2f}  {mark:15}  {chunk['filename']}: {snippet}...")
    print(f"\nThreshold: {threshold}. Change it with the SEMANTIC_MIN_SIM environment variable.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
