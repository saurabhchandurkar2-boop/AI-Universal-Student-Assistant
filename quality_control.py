import re


class QualityController:

    """
    AI Student Assistant V22
    Quality Control Layer

    Responsibilities:
        1. Detect empty/invalid answers
        2. Remove internal prompt leakage
        3. Remove duplicate lines
        4. Remove excessive blank lines
        5. Correct conservative known formula errors
        6. Correct selected high-confidence technical errors
        7. Detect obvious unfinished answers
        8. Detect truncated mathematical expressions
        9. Prevent extremely long responses
        10. Keep processing lightweight
    """

    def __init__(self):

        # =========================================
        # CONFIGURATION
        # =========================================

        self.max_answer_length = 5000
        self.min_answer_length = 5

        # =========================================
        # INTERNAL TEXT THAT MUST NOT REACH USER
        # =========================================

        self.forbidden_patterns = [

            "rules**:",
            "rules:",
            "quality control:",
            "quality check:",
            "quality evaluation:",
            "evaluation:",
            "self-evaluation:",
            "internal evaluation:",
            "internal instructions:",
            "assistant evaluation:",
            "response evaluation:",
            "starts with direct answer?",
            "is accurate?",
            "uses retrieved knowledge?",
            "does it answer",
            "should be removed",
            "final answer should",
            "chain of thought:",
            "chain-of-thought:",
            "hidden instructions:",
            "system prompt:",
            "developer message:",
            "internal reasoning:",
            "internal analysis:",
        ]

        # =========================================
        # COMMON FORMULA ERRORS
        # =========================================

        self.known_formula_errors = {

            # Ohm's law
            "r = v/r": "R = V/I",
            "r=v/r": "R = V/I",

        }

        # =========================================
        # HIGH-CONFIDENCE TECHNICAL CORRECTIONS
        # =========================================

        self.known_technical_corrections = [

            # -------------------------------------
            # Transformer frequency
            # -------------------------------------

            (
                re.compile(
                    r"[^.!?\n]*\btransformer(?:s)?\s+"
                    r"(?:change|changes|convert|converts)\s+"
                    r"(?:the\s+)?frequency"
                    r"[^.!?\n]*[.!?]",
                    re.IGNORECASE
                ),
                "A transformer does not change the frequency of the AC supply."
            ),

            # -------------------------------------
            # Transformer core made of copper
            # -------------------------------------

            (
                re.compile(
                    r"[^.!?\n]*\btransformer(?:s)?\s+"
                    r"core(?:s)?\s+"
                    r"(?:can|may|is|are)\s+be\s+made\s+of\s+"
                    r"(?:copper|copper\s+and\s+iron)"
                    r"[^.!?\n]*[.!?]",
                    re.IGNORECASE
                ),
                "A conventional transformer core is made from laminated magnetic steel, not copper."
            ),

            # -------------------------------------
            # Transformer changes polarity
            # -------------------------------------

            (
                re.compile(
                    r"[^.!?\n]*\btransformer(?:s)?\s+"
                    r"(?:change|changes|convert|converts)\s+"
                    r"(?:the\s+)?polarity"
                    r"[^.!?\n]*[.!?]",
                    re.IGNORECASE
                ),
                "A transformer transfers AC electrical energy between windings without changing the supply frequency."
            ),
        ]

        # =========================================
        # COMMON REPETITIVE PHRASES
        # =========================================

        self.redundant_phrases = [

            (
                re.compile(
                    r"\bused for scripting,\s*"
                    r"automation,\s*and\s+automation\s+of\s+tasks\b",
                    re.IGNORECASE
                ),
                "used for scripting and automation of tasks"
            ),

            (
                re.compile(
                    r"\bfor scripting,\s*automation,\s*"
                    r"and\s+automation\s+of\s+tasks\b",
                    re.IGNORECASE
                ),
                "for scripting and automation of tasks"
            ),
        ]

    # =========================================
    # REMOVE INTERNAL LEAKS
    # =========================================

    def _remove_internal_lines(self, answer):

        lines = answer.splitlines()
        cleaned_lines = []

        for line in lines:

            stripped = line.strip()
            lower_line = stripped.lower()

            if not stripped:

                cleaned_lines.append(line)
                continue

            if any(
                pattern in lower_line
                for pattern in self.forbidden_patterns
            ):
                continue

            cleaned_lines.append(line)

        return "\n".join(cleaned_lines)

    # =========================================
    # REMOVE DUPLICATE LINES
    # =========================================

    def _remove_duplicate_lines(self, answer):

        lines = answer.splitlines()

        cleaned_lines = []

        # Keep track of all non-empty lines already seen.
        # This catches duplicates even when blank lines
        # separate repeated content.
        seen_lines = set()

        for line in lines:

            current = line.strip()

            # Preserve blank lines.
            if not current:

                cleaned_lines.append(line)
                continue

            normalized = current.lower()

            # Remove repeated non-empty lines.
            if normalized in seen_lines:

                continue

            seen_lines.add(normalized)
            cleaned_lines.append(line)

        return "\n".join(cleaned_lines)

    # =========================================
    # REMOVE EXCESSIVE BLANK LINES
    # =========================================

    def _remove_excessive_blank_lines(self, answer):

        while "\n\n\n" in answer:

            answer = answer.replace(
                "\n\n\n",
                "\n\n"
            )

        return answer

    # =========================================
    # FIX KNOWN FORMULA ERRORS
    # =========================================

    def _fix_known_formula_errors(self, answer):

        for wrong, correct in self.known_formula_errors.items():

            pattern = re.compile(
                re.escape(wrong),
                re.IGNORECASE
            )

            answer = pattern.sub(
                correct,
                answer
            )

        return answer

    # =========================================
    # FIX HIGH-CONFIDENCE TECHNICAL ERRORS
    # =========================================

    def _fix_known_technical_errors(self, answer):

        for pattern, replacement in self.known_technical_corrections:

            answer = pattern.sub(
                replacement,
                answer
            )

        return answer

    # =========================================
    # REMOVE REDUNDANT PHRASES
    # =========================================

    def _remove_redundant_phrases(self, answer):

        for pattern, replacement in self.redundant_phrases:

            answer = pattern.sub(
                replacement,
                answer
            )

        return answer

    # =========================================
    # LIMIT RESPONSE LENGTH
    # =========================================

    def _limit_length(self, answer):

        if len(answer) <= self.max_answer_length:

            return answer

        shortened = answer[
            :self.max_answer_length
        ]

        if " " in shortened:

            shortened = shortened.rsplit(
                " ",
                1
            )[0]

        return (
            shortened
            + "\n\n[Answer shortened for clarity.]"
        )

    # =========================================
    # DETECT TRUNCATED MATH
    # =========================================

    def _looks_like_truncated_math(self, answer):

        if not answer:

            return False

        text = answer.strip()

        if not text:

            return False

        # -----------------------------------------
        # Check whether the response ends while a
        # LaTeX inline math expression is still open.
        #
        # Example:
        #
        # "alternating current ($I_2
        #
        # The "$" has been opened but not closed.
        # -----------------------------------------

        dollar_count = text.count("$")

        if dollar_count % 2 != 0:

            return True

        # -----------------------------------------
        # Detect common unfinished LaTeX commands.
        # -----------------------------------------

        lower_text = text.lower()

        incomplete_latex_endings = (

            "\\frac",
            "\\sqrt",
            "\\text",
            "\\begin",
            "\\left",
            "\\right",
            "\\sin",
            "\\cos",
            "\\tan",
            "\\log",
            "\\ln",
        )

        if lower_text.endswith(
            incomplete_latex_endings
        ):
            return True

        # -----------------------------------------
        # Detect an answer ending immediately after
        # a LaTeX variable/subscript fragment.
        #
        # Example:
        # "$I_2"
        #
        # This is useful when Gemini stops during
        # generation.
        # -----------------------------------------

        if re.search(
            r"\$\s*[A-Za-z]+(?:_\d+)?$",
            text
        ):
            return True

        # -----------------------------------------
        # Detect an opening mathematical delimiter
        # at the very end of the response.
        # -----------------------------------------

        if text.endswith(
            (
                "$",
                "(",
                "[",
                "{",
            )
        ):
            return True

        return False

    # =========================================
    # DETECT OBVIOUS TRUNCATION
    # =========================================

    def _looks_unfinished(self, answer):

        if not answer:

            return True

        text = answer.strip()
        lower_text = text.lower()

        # -----------------------------------------
        # First check mathematical truncation.
        # -----------------------------------------

        if self._looks_like_truncated_math(text):

            return True

        # -----------------------------------------
        # Strong indicators that can occur at the
        # end of longer Gemini responses.
        # -----------------------------------------

        long_unfinished_endings = (

            "because",
            "therefore",
            "which",
            "that",
            "its",
            "their",
            "his",
            "her",
            "across",
        )

        if lower_text.endswith(
            long_unfinished_endings
        ):
            return True

        # -----------------------------------------
        # Short-answer unfinished endings.
        # -----------------------------------------

        short_unfinished_endings = (

            "in the",
            "such as:",
            "where:",
            "for example:",
            "including:",
            "and",
            "or",
            "with",
            "to",
            "of",
            "the",
            "a",
            "an",
        )

        if (
            len(text) < 250
            and lower_text.endswith(
                short_unfinished_endings
            )
        ):
            return True

        # -----------------------------------------
        # Short response ending with ":" often
        # means the model was about to provide
        # a list or explanation.
        # -----------------------------------------

        if (
            lower_text.endswith(":")
            and len(text) < 180
        ):
            return True

        return False

    # =========================================
    # CLEAN RESPONSE
    # =========================================

    def clean(self, answer, question):

        if not answer:

            return (
                "I could not generate a useful answer."
            )

        answer = str(answer).strip()

        # STEP 1 — Remove internal leakage

        answer = self._remove_internal_lines(
            answer
        )

        # STEP 2 — Fix known formula errors

        answer = self._fix_known_formula_errors(
            answer
        )

        # STEP 3 — Fix technical errors

        answer = self._fix_known_technical_errors(
            answer
        )

        # STEP 4 — Remove redundant phrases

        answer = self._remove_redundant_phrases(
            answer
        )

        # STEP 5 — Remove duplicate lines

        answer = self._remove_duplicate_lines(
            answer
        )

        # STEP 6 — Remove excessive blank lines

        answer = self._remove_excessive_blank_lines(
            answer
        )

        # STEP 7 — Final whitespace cleanup

        answer = answer.strip()

        # STEP 8 — Empty response check

        if not answer:

            return (
                "I could not generate a useful answer."
            )

        # STEP 9 — Length protection

        answer = self._limit_length(
            answer
        )

        return answer.strip()

    # =========================================
    # VALIDATE RESPONSE
    # =========================================

    def validate(self, answer, question):

        if not answer:

            return False

        answer = str(answer).strip()

        # -----------------------------------------
        # Minimum useful length
        # -----------------------------------------

        if len(answer) < self.min_answer_length:

            return False

        # -----------------------------------------
        # Internal leakage
        # -----------------------------------------

        lower_answer = answer.lower()

        leaked_patterns = [

            "starts with direct answer?",
            "uses retrieved knowledge?",
            "quality control:",
            "quality check:",
            "internal evaluation:",
            "internal instructions:",
            "chain of thought:",
            "chain-of-thought:",
            "system prompt:",
            "developer message:",
            "internal reasoning:",
            "internal analysis:",
        ]

        for pattern in leaked_patterns:

            if pattern in lower_answer:

                return False

        # -----------------------------------------
        # Obvious unfinished answer
        # -----------------------------------------

        if self._looks_unfinished(answer):

            return False

        return True


# =============================================
# DIRECT TEST
# =============================================

if __name__ == "__main__":

    qc = QualityController()

    print()
    print("======================================")
    print("       QUALITY CONTROL V22 TEST")
    print("======================================")
    print()

    # =========================================
    # TEST 1 — INTERNAL LEAK
    # =========================================

    test_answer = """
**Ohm's Law** describes the relationship between voltage,
current, and resistance.

Rules**:
    * Starts with direct answer? Yes.
    * Accurate and uses retrieved knowledge? Yes.

The formula is:

V = I × R
"""

    print("TEST 1 — INTERNAL LEAK")
    print("--------------------------------------")

    cleaned = qc.clean(
        test_answer,
        "Explain Ohm's law."
    )

    print(cleaned)

    print()
    print(
        "Validation:",
        "VALID"
        if qc.validate(
            cleaned,
            "Explain Ohm's law."
        )
        else
        "INVALID"
    )

    # =========================================
    # TEST 2 — FORMULA ERROR
    # =========================================

    print()
    print("TEST 2 — FORMULA PROTECTION")
    print("--------------------------------------")

    formula_answer = """
Ohm's law can be rearranged to find resistance.

R = V/R
"""

    cleaned_formula = qc.clean(
        formula_answer,
        "What is the formula for resistance?"
    )

    print(cleaned_formula)

    print()
    print(
        "Validation:",
        "VALID"
        if qc.validate(
            cleaned_formula,
            "What is the formula for resistance?"
        )
        else
        "INVALID"
    )

    # =========================================
    # TEST 3 — DUPLICATE LINES
    # =========================================

    print()
    print("TEST 3 — DUPLICATE PROTECTION")
    print("--------------------------------------")

    duplicate_answer = """
Photosynthesis is the process by which plants make food.

Photosynthesis is the process by which plants make food.

It uses sunlight, carbon dioxide, and water.
"""

    cleaned_duplicate = qc.clean(
        duplicate_answer,
        "What is photosynthesis?"
    )

    print(cleaned_duplicate)

    print()
    print(
        "Validation:",
        "VALID"
        if qc.validate(
            cleaned_duplicate,
            "What is photosynthesis?"
        )
        else
        "INVALID"
    )

    # =========================================
    # TEST 4 — TRANSFORMER FACT PROTECTION
    # =========================================

    print()
    print("TEST 4 — TRANSFORMER FACT PROTECTION")
    print("--------------------------------------")

    transformer_answer = """
A transformer changes the frequency of AC electricity.

The transformer core can be made of copper.
"""

    cleaned_transformer = qc.clean(
        transformer_answer,
        "Explain the working principle of a transformer."
    )

    print(cleaned_transformer)

    print()
    print(
        "Validation:",
        "VALID"
        if qc.validate(
            cleaned_transformer,
            "Explain the working principle of a transformer."
        )
        else
        "INVALID"
    )

    # =========================================
    # TEST 5 — REDUNDANCY
    # =========================================

    print()
    print("TEST 5 — REPETITION PROTECTION")
    print("--------------------------------------")

    redundant_answer = """
Python is used for scripting, automation, and automation of tasks.
"""

    cleaned_redundant = qc.clean(
        redundant_answer,
        "What is Python?"
    )

    print(cleaned_redundant)

    print()
    print(
        "Validation:",
        "VALID"
        if qc.validate(
            cleaned_redundant,
            "What is Python?"
        )
        else
        "INVALID"
    )

    # =========================================
    # TEST 6 — LONG TRUNCATION DETECTION
    # =========================================

    print()
    print("TEST 6 — TRUNCATION DETECTION")
    print("--------------------------------------")

    unfinished_answer = """
A transformer is an electrical device that transfers electrical
energy between two circuits through electromagnetic induction.
It consists of a primary winding, secondary winding, and magnetic
core. When AC voltage is applied to the primary winding, it creates
a changing magnetic flux in the core. This changing flux links with
the secondary winding and induces an electromotive force according
to Faraday's law. The induced voltage depends on the number of turns
in each winding and the magnetic flux linking them across its
"""

    print(
        "Looks unfinished:",
        qc._looks_unfinished(
            unfinished_answer
        )
    )

    print(
        "Validation:",
        "VALID"
        if qc.validate(
            unfinished_answer,
            "Explain transformer working."
        )
        else
        "INVALID"
    )

    # =========================================
    # TEST 7 — TRUNCATED MATH
    # =========================================

    print()
    print("TEST 7 — TRUNCATED MATH DETECTION")
    print("--------------------------------------")

    truncated_math_answer = """
A transformer transfers electrical energy through electromagnetic
induction. When the secondary winding is connected to a load,
the induced voltage causes an alternating current ($I_2
"""

    print(
        "Looks like truncated math:",
        qc._looks_like_truncated_math(
            truncated_math_answer
        )
    )

    print(
        "Looks unfinished:",
        qc._looks_unfinished(
            truncated_math_answer
        )
    )

    print(
        "Validation:",
        "VALID"
        if qc.validate(
            truncated_math_answer,
            "Explain transformer working."
        )
        else
        "INVALID"
    )

    print()
    print("======================================")
    print("          V22 TEST COMPLETE")
    print("======================================")