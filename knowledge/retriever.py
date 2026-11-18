import os
import re
from collections import Counter

import semantic


class KnowledgeRetriever:
    """
    Knowledge Retriever V27.3.5

    Improvements:
    - Heading-aware chunking
    - Intent-aware retrieval
    - Topic-aware retrieval
    - Strong specific-intent matching
    - Stronger explicit topic matching
    - Better ranking for formula/application/example/variable queries
    """

    def __init__(self, knowledge_path="knowledge/documents"):

        self.knowledge_path = knowledge_path

        self.documents = []
        self.chunks = []

        self.chunk_size = 500
        self.chunk_overlap = 100

        self.min_score = 0.05

        # Optional search by meaning (see semantic.py). Off unless fastembed is
        # installed; any problem switches it off and word search carries on.
        self.semantic = None
        self.semantic_error = ""
        self._semantic_ready = False
        self.semantic_min_sim = float(os.getenv("SEMANTIC_MIN_SIM", "0.60"))
        self.semantic_margin = 0.10
        # A match found only by meaning starts just above the chatbot's
        # "good enough" line (1.5) and rises with the similarity.
        self.semantic_base_score = 1.6

        self.refresh_cache()

        if semantic.wanted() and semantic.package_installed():
            self.enable_semantic()

    # ---------------------------------------------------------
    # CACHE
    # ---------------------------------------------------------

    def refresh_cache(self):

        self._semantic_ready = False

        self.documents = []
        self.chunks = []

        if not os.path.exists(self.knowledge_path):

            print(
                f"[RAG] Knowledge directory not found: "
                f"{self.knowledge_path}"
            )

            return

        for root, _, files in os.walk(self.knowledge_path):

            for filename in files:

                if not filename.lower().endswith(".txt"):
                    continue

                filepath = os.path.join(
                    root,
                    filename
                )

                try:

                    with open(
                        filepath,
                        "r",
                        encoding="utf-8"
                    ) as file:

                        text = file.read().strip()

                    if not text:
                        continue

                    self.documents.append(
                        {
                            "path": filepath,
                            "filename": filename,
                            "text": text
                        }
                    )

                except Exception as e:

                    print(
                        f"[RAG] Failed to read "
                        f"{filepath}: {e}"
                    )

        print(
            f"[RAG] Knowledge cache refreshed: "
            f"{len(self.documents)} document(s)."
        )

        self.build_chunks()

    # ---------------------------------------------------------
    # INTENT DETECTION
    # ---------------------------------------------------------

    def detect_intent(self, question):

        question_lower = question.lower().strip()

        specific_intents = {

            "formula": [
                "formula",
                "equation",
                "equations",
                "expression"
            ],

            "application": [
                "application",
                "applications",
                "use",
                "uses",
                "usage",
                "applied"
            ],

            "example": [
                "example",
                "examples",
                "example of"
            ],

            "variable": [
                "variable",
                "variables",
                "parameters",
                "quantities"
            ],

            "calculation": [
                "calculate",
                "calculation",
                "calculate the",
                "find",
                "compute",
                "numerical"
            ],

            "advantages": [
                "advantage",
                "advantages",
                "benefit",
                "benefits"
            ],

            "disadvantages": [
                "disadvantage",
                "disadvantages",
                "limitation",
                "limitations"
            ],

            "working": [
                "working",
                "works",
                "working principle",
                "mechanism"
            ],

            "importance": [
                "importance",
                "important",
                "significance"
            ]
        }

        detected_intents = []

        for intent, keywords in specific_intents.items():

            for keyword in keywords:

                if keyword in question_lower:

                    detected_intents.append(
                        intent
                    )

                    break

        if not detected_intents:

            definition_keywords = [
                "definition",
                "define",
                "meaning",
                "what is",
                "what are"
            ]

            for keyword in definition_keywords:

                if keyword in question_lower:

                    detected_intents.append(
                        "definition"
                    )

                    break

        return detected_intents

    # ---------------------------------------------------------
    # HEADING DETECTION
    # ---------------------------------------------------------

    def get_section_heading(self, text):

        lines = text.splitlines()

        for line in lines:

            line = line.strip()

            if re.match(
                r"^#{1,6}\s+.+$",
                line
            ):

                return line

        return ""

    # ---------------------------------------------------------
    # TOPIC WORD EXTRACTION
    # ---------------------------------------------------------

    def extract_topic_terms(self, question):

        question_lower = question.lower()

        stop_words = {

            "what",
            "what's",
            "is",
            "are",
            "was",
            "were",
            "the",
            "a",
            "an",
            "of",
            "in",
            "on",
            "for",
            "to",
            "and",
            "or",
            "with",
            "from",
            "give",
            "explain",
            "describe",
            "define",
            "meaning",
            "tell",
            "me",
            "about",
            "please",
            "can",
            "you",
            "how",
            "why",
            "does",
            "do",
            "used",
            "use",
            "uses",
            "application",
            "applications",
            "example",
            "examples",
            "formula",
            "equation",
            "equations",
            "variable",
            "variables",
            "parameters",
            "quantities",
            "calculate",
            "calculation",
            "compute",
            "numerical",
            "advantage",
            "advantages",
            "benefit",
            "benefits",
            "disadvantage",
            "disadvantages",
            "limitation",
            "limitations",
            "working",
            "works",
            "principle",
            "mechanism",
            "importance",
            "important",
            "significance"
        }

        words = re.findall(
            r"[a-zA-Z0-9]+",
            question_lower
        )

        topic_terms = []

        for word in words:

            if word in stop_words:
                continue

            if len(word) < 2:
                continue

            topic_terms.append(word)

        return topic_terms

    # ---------------------------------------------------------
    # TOPIC RELEVANCE
    # ---------------------------------------------------------

    def topic_score(self, question, chunk):

        question_terms = self.extract_topic_terms(
            question
        )

        if not question_terms:
            return 0.0

        chunk_text = chunk["text"].lower()

        filename = chunk.get(
            "filename",
            ""
        ).lower()

        relative_path = chunk.get(
            "path",
            ""
        ).lower()

        heading = self.get_section_heading(
            chunk["text"]
        ).lower()

        score = 0.0

        for term in question_terms:

            # -------------------------------------------------
            # Strong explicit topic match
            # -------------------------------------------------

            if term in filename:

                score += 3.00

            elif term in relative_path:

                score += 2.50

            # -------------------------------------------------
            # Topic appears inside retrieved content
            # -------------------------------------------------

            if re.search(
                r"\b" + re.escape(term) + r"\b",
                chunk_text
            ):

                score += 0.80

            # -------------------------------------------------
            # Topic appears in section heading
            # -------------------------------------------------

            if re.search(
                r"\b" + re.escape(term) + r"\b",
                heading
            ):

                score += 0.60

        return score

        # ---------------------------------------------------------
        # CHUNKING
        # ---------------------------------------------------------

    def split_long_text(self, text):
        """Split a very long block (for example one PDF page with no blank
        lines) into pieces of at most chunk_size characters, breaking at
        line ends or sentence ends where possible."""

        text = text.strip()

        if len(text) <= self.chunk_size:
            return [text] if text else []

        pieces = []

        while len(text) > self.chunk_size:

            window = text[:self.chunk_size]

            cut = max(
                window.rfind("\n"),
                window.rfind(". "),
                window.rfind("? "),
                window.rfind("! ")
            )

            if cut < self.chunk_size // 2:
                cut = window.rfind(" ")

            if cut < self.chunk_size // 2:
                cut = self.chunk_size - 1

            pieces.append(text[:cut + 1].strip())
            text = text[cut + 1:].strip()

        if text:
            pieces.append(text)

        return pieces

    def build_chunks(self):

        self.chunks = []

        for document in self.documents:

            text = document["text"]

            sections = re.split(
                r"(?m)(?=^#{1,6}\s+.+$)",
                text
            )

            for section in sections:

                section = section.strip()

                if not section:
                    continue

                heading = self.get_section_heading(
                    section
                ).lower()

                # -------------------------------------------------
                # Keep list-oriented sections together.
                # These sections are usually directly useful as
                # complete answers for application/list queries.
                # -------------------------------------------------

                keep_section_together = any(
                    keyword in heading
                    for keyword in [
                        "application",
                        "applications",
                        "advantages",
                        "disadvantages",
                        "examples",
                        "requirements",
                        "factors",
                        "importance"
                    ]
                )

                if (
                    keep_section_together
                    and len(section) <= 1800
                ):

                    self.chunks.append(
                        {
                            "text": section,
                            "filename": document["filename"],
                            "path": document["path"]
                        }
                    )

                    continue

                # -------------------------------------------------
                # Normal sections
                # -------------------------------------------------

                if len(section) <= self.chunk_size:

                    self.chunks.append(
                        {
                            "text": section,
                            "filename": document["filename"],
                            "path": document["path"]
                        }
                    )

                    continue

                paragraphs = [
                    piece
                    for paragraph in re.split(r"\n\s*\n", section)
                    for piece in self.split_long_text(paragraph)
                ]

                current_chunk = ""

                for paragraph in paragraphs:

                    paragraph = paragraph.strip()

                    if not paragraph:
                        continue

                    if (
                        len(current_chunk)
                        + len(paragraph)
                        + 2
                        <= self.chunk_size
                    ):

                        if current_chunk:

                            current_chunk += (
                                "\n\n" + paragraph
                            )

                        else:

                            current_chunk = paragraph

                    else:

                        if current_chunk:

                            self.chunks.append(
                                {
                                    "text": current_chunk,
                                    "filename": document["filename"],
                                    "path": document["path"]
                                }
                            )

                        overlap = current_chunk[
                            -self.chunk_overlap:
                        ]

                        current_chunk = (
                            overlap
                            + "\n\n"
                            + paragraph
                        )

                if current_chunk:

                    self.chunks.append(
                        {
                            "text": current_chunk,
                            "filename": document["filename"],
                            "path": document["path"]
                        }
                    )

        print(
            f"[RAG] Knowledge chunks created: "
            f"{len(self.chunks)}"
        )
    # ---------------------------------------------------------
    # CHUNK SCORING
    # ---------------------------------------------------------

    def score_chunk(self, question, chunk):

        question_lower = question.lower()

        chunk_text = chunk["text"].lower()

        question_words = re.findall(
            r"\b[a-zA-Z0-9]+\b",
            question_lower
        )

        chunk_words = re.findall(
            r"\b[a-zA-Z0-9]+\b",
            chunk_text
        )

        if not question_words or not chunk_words:

            return 0.0

        question_counter = Counter(
            question_words
        )

        chunk_counter = Counter(
            chunk_words
        )

        overlap_count = 0
        weighted_count = 0

        for word, count in question_counter.items():

            if word in chunk_counter:

                overlap_count += 1

                weighted_count += min(
                    count,
                    chunk_counter[word]
                )

        overlap_score = (
            overlap_count
            / max(len(question_counter), 1)
        )

        weighted_score = (
            weighted_count
            / max(len(question_words), 1)
        )

        base_score = (
            overlap_score * 0.7
            + weighted_score * 0.3
        )

        # -----------------------------------------------------
        # Filename boost
        # -----------------------------------------------------

        filename = chunk.get(
            "filename",
            ""
        ).lower()

        filename_without_extension = re.sub(
            r"\.txt$",
            "",
            filename
        )

        filename_words = re.findall(
            r"[a-zA-Z0-9]+",
            filename_without_extension
        )

        filename_boost = 0.0

        for word in question_words:

            if word in filename_words:

                filename_boost += 0.35

        # -----------------------------------------------------
        # Phrase boost
        # -----------------------------------------------------

        phrase_boost = 0.0

        important_phrases = [

            "ohm's law",
            "ohms law",
            "photosynthesis",
            "python variables",
            "python variable",
            "indian history"
        ]

        for phrase in important_phrases:

            if phrase in question_lower:

                if phrase in chunk_text:

                    phrase_boost += 0.50

        # -----------------------------------------------------
        # Topic relevance
        # -----------------------------------------------------

        topic_relevance = self.topic_score(
            question,
            chunk
        )

        # -----------------------------------------------------
        # Intent relevance
        # -----------------------------------------------------

        intents = self.detect_intent(
            question
        )

        heading = self.get_section_heading(
            chunk["text"]
        ).lower()

        heading_mapping = {

            "formula": [
                "formula",
                "equation",
                "expression"
            ],

            "definition": [
                "definition"
            ],

            "application": [
                "application",
                "applications",
                "uses",
                "usage"
            ],

            "example": [
                "example",
                "examples"
            ],

            "variable": [
                "variable",
                "variables",
                "parameters",
                "quantities"
            ],

            "calculation": [
                "calculation",
                "example"
            ],

            "advantages": [
                "advantages",
                "benefits"
            ],

            "disadvantages": [
                "disadvantages",
                "limitations"
            ],

            "working": [
                "working",
                "principle",
                "mechanism"
            ],

            "importance": [
                "importance",
                "significance"
            ]
        }

        # -----------------------------------------------------
        # V27.3.5 intent priority
        # -----------------------------------------------------

        intent_priority = {

            "formula": 2.80,
            "definition": 1.40,
            "application": 2.50,
            "example": 2.50,
            "variable": 2.30,
            "calculation": 2.50,
            "advantages": 2.50,
            "disadvantages": 2.50,
            "working": 2.50,
            "importance": 2.50
        }

        intent_boost = 0.0

        for intent in intents:

            expected_headings = (
                heading_mapping.get(
                    intent,
                    []
                )
            )

            heading_match = False

            for expected in expected_headings:

                if expected in heading:

                    intent_boost += (
                        intent_priority.get(
                            intent,
                            1.0
                        )
                    )

                    heading_match = True

                    break

            # Direct intent word match gets only a
            # smaller additional boost.
            if (
                heading_match
                and intent in heading
            ):

                intent_boost += 0.20

        # -----------------------------------------------------
        # Specific-intent bonus
        # -----------------------------------------------------

        specific_intent_bonus = 0.0

        for intent in intents:

            expected_headings = (
                heading_mapping.get(
                    intent,
                    []
                )
            )

            for expected in expected_headings:

                if expected in heading:

                    specific_intent_bonus += 1.00

                    break

        # -----------------------------------------------------
        # Final V27.3.5 score
        # -----------------------------------------------------

        final_score = (
            base_score
            + filename_boost
            + phrase_boost
            + topic_relevance * 0.70
            + intent_boost * 0.65
            + specific_intent_bonus
        )

        return final_score

    # ---------------------------------------------------------
    # SEARCH BY MEANING (optional)
    # ---------------------------------------------------------

    def enable_semantic(self, embedder=None, cache_path="auto"):
        """Turn on search by meaning. Returns True when it is on."""

        try:

            if cache_path == "auto":

                folder = os.path.dirname(
                    os.path.normpath(self.knowledge_path)
                )

                cache_path = (
                    os.path.join(folder, "semantic_cache.json")
                    if os.path.basename(
                        os.path.normpath(self.knowledge_path)
                    ) == "documents"
                    else None
                )

            self.semantic = semantic.SemanticIndex(
                embedder=embedder,
                cache_path=cache_path
            )

            self.semantic_error = ""
            self._semantic_ready = False

            return True

        except Exception as error:

            self._disable_semantic(error)

            return False

    def _disable_semantic(self, error):

        self.semantic = None
        self._semantic_ready = False
        self.semantic_error = str(error)[:200]

        print("[Semantic] Switched off:", self.semantic_error)

    def semantic_status(self):
        """'on', 'off' or 'error: ...' for the sidebar."""

        if self.semantic is not None:
            return "on"

        if self.semantic_error:
            return "error: " + self.semantic_error

        return "off"

    def _ensure_semantic(self):

        if self.semantic is None:
            return False

        if self._semantic_ready:
            return True

        try:

            self.semantic.build(
                [chunk["text"] for chunk in self.chunks]
            )

            self._semantic_ready = True

            print(
                "[Semantic] Index ready:",
                len(self.chunks),
                "chunk(s),",
                self.semantic.embedded_now,
                "newly embedded."
            )

            return True

        except Exception as error:

            self._disable_semantic(error)

            return False

    # ---------------------------------------------------------
    # SEARCH
    # ---------------------------------------------------------

    def search(
        self,
        question,
        top_k=3
    ):

        if not self.chunks:

            return []

        results = []

        for index, chunk in enumerate(self.chunks):

            score = self.score_chunk(
                question,
                chunk
            )

            if score >= self.min_score:

                results.append(
                    {
                        "text": chunk["text"],
                        "filename": chunk["filename"],
                        "path": chunk["path"],
                        "score": score,
                        "chunk_index": index
                    }
                )

        results = self._add_meaning_matches(
            question,
            results,
            top_k
        )

        results.sort(
            key=lambda item: item["score"],
            reverse=True
        )

        return results[:top_k]

    def _add_meaning_matches(
        self,
        question,
        results,
        top_k
    ):
        """Boost word matches that also match in meaning, and add notes
        that match only in meaning. Does nothing when meaning search is off."""

        if not self._ensure_semantic():

            return results

        try:

            hits = self.semantic.search(
                question,
                top_k=top_k + 2,
                min_sim=self.semantic_min_sim,
                margin=self.semantic_margin
            )

        except Exception as error:

            self._disable_semantic(error)

            return results

        by_index = {
            item["chunk_index"]: item
            for item in results
        }

        for index, sim in hits:

            bonus = (sim - self.semantic_min_sim) * 10

            if index in by_index:

                by_index[index]["score"] += bonus
                by_index[index]["via"] = "words+meaning"

            else:

                chunk = self.chunks[index]

                results.append(
                    {
                        "text": chunk["text"],
                        "filename": chunk["filename"],
                        "path": chunk["path"],
                        "score": self.semantic_base_score + bonus,
                        "chunk_index": index,
                        "via": "meaning"
                    }
                )

        return results

    # ---------------------------------------------------------
    # BUILD CONTEXT
    # ---------------------------------------------------------

    def build_context(
        self,
        question,
        top_k=3
    ):

        results = self.search(
            question,
            top_k=top_k
        )

        if not results:

            return ""

        context_parts = []

        for result in results:

            context_parts.append(
                f"Source: {result['filename']}\n"
                f"{result['text']}"
            )

        return "\n\n".join(
            context_parts
        )

    # ---------------------------------------------------------
    # TEST MODE
    # ---------------------------------------------------------

    def interactive_test(self):

        print()
        print("======================================")
        print("       KNOWLEDGE RETRIEVER V27.3.5")
        print("======================================")

        question = input(
            "Enter a question: "
        ).strip()

        if not question:

            print("No question entered.")

            return

        results = self.search(
            question,
            top_k=3
        )

        print()
        print("Retrieved knowledge:")
        print()

        if not results:

            print("No relevant knowledge found.")

            return

        for result in results:

            print(
                f"Source: {result['filename']}"
            )

            print(
                f"Score: {result['score']:.4f}"
            )

            print(
                result["text"]
            )

            print(
                "--------------------------------------------------"
            )


if __name__ == "__main__":

    retriever = KnowledgeRetriever()

    retriever.interactive_test()