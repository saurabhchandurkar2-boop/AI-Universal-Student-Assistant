"""Retrieval evaluation (does NOT need the llama server).

For each question in eval/questions.json it checks whether the retriever
returns the expected source file and text. Run from the project folder:

    python eval/retrieval_eval.py

Prints a score and exits with code 1 if any question fails.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

import tempfile  # noqa: E402

from knowledge.ingest.document_ingester import DocumentIngester  # noqa: E402
from knowledge.retriever import KnowledgeRetriever  # noqa: E402


def main():
    # Build a temporary knowledge folder from the bundled sample notes, so the
    # evaluation never depends on (or changes) your own knowledge base.
    temp_docs = tempfile.mkdtemp()
    ingester = DocumentIngester(
        source_folder=os.path.join(ROOT, "documents_to_import"),
        knowledge_folder=temp_docs
    )
    ingester.import_all()
    retriever = KnowledgeRetriever(knowledge_path=temp_docs)

    with open(os.path.join(ROOT, "eval", "questions.json"), encoding="utf-8") as f:
        questions = json.load(f)

    source_hits = text_hits = 0
    failures = []

    for item in questions:
        context = retriever.build_context(item["q"])
        got_source = f"Source: {item['source']}" in context
        got_text = item["expect"].lower() in context.lower()
        source_hits += got_source
        text_hits += got_text
        if not (got_source and got_text):
            failures.append((item["q"], got_source, got_text))

    n = len(questions)
    print("\n==== RETRIEVAL EVALUATION ====")
    print(f"Questions:              {n}")
    print(f"Correct source found:   {source_hits}/{n}  ({100 * source_hits / n:.0f}%)")
    print(f"Expected text found:    {text_hits}/{n}  ({100 * text_hits / n:.0f}%)")
    for q, s, t in failures:
        print(f"  FAIL: {q}  (source={s}, text={t})")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
