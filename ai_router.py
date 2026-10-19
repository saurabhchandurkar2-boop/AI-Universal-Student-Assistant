import re


class AIRouter:

    VERSION = "V26.4.2.3"

    def __init__(self):
        print(f"[AI Router] {self.VERSION} initialized.")

    # ========================================================
    # EXTERNAL / CURRENT INFORMATION
    # ========================================================

    def is_external(self, question):

        q = question.lower().strip()

        external_patterns = [
            r"\blatest\b",
            r"\btoday\b",
            r"\bnow\b",
            r"\brecent\b",
            r"\brecently\b",
            r"\bnews\b",
            r"\bweather\b",
            r"\btemperature\b",
            r"\blive\b",
            r"\bstock price\b",
            r"\bshare price\b",
            r"\bcurrent price\b",
            r"\bmarket price\b",
            r"\bcurrent events\b",
            r"\bpresident\b",
            r"\bprime minister\b",
            r"\bchief minister\b",
        ]

        for pattern in external_patterns:

            if re.search(pattern, q):

                print(
                    "[AI Router] External/current question detected."
                )

                return True

        return False

    # ========================================================
    # CALCULATION
    # ========================================================

    def is_calculation(self, question):

        q = question.lower().strip()

        calculation_patterns = [
            r"\bcalculate\b",
            r"\bcalculation\b",
            r"\bsolve\b",
            r"\bcompute\b",
            r"\bfind the value\b",
            r"\bhow much\b",
            r"\bhow many\b",
            r"\bnumerical\b",
            r"\bpercentage\b",
            r"\bratio\b",
            r"\baverage\b",
            r"\bprobability\b",
            r"\bconvert\b",
            r"\bevaluate\b",
        ]

        for pattern in calculation_patterns:

            if re.search(pattern, q):

                print(
                    "[AI Router] Calculation question detected."
                )

                return True

        # Detect simple mathematical expressions.

        if re.search(
            r"\d+\s*[\+\-\*\/\×\÷]\s*\d+",
            q
        ):

            print(
                "[AI Router] Calculation question detected."
            )

            return True

        return False

    # ========================================================
    # COMPLEX / REASONING
    # ========================================================

    def is_complex(self, question):

        q = question.lower().strip()

        complex_patterns = [
            r"\banalyze\b",
            r"\banalyse\b",
            r"\bevaluate\b",
            r"\bcompare\b",
            r"\bcontrast\b",
            r"\bderive\b",
            r"\bprove\b",
            r"\breason\b",
            r"\bjustify\b",
            r"\bexplain in detail\b",
            r"\bdiscuss\b",
        ]

        for pattern in complex_patterns:

            if re.search(pattern, q):

                print(
                    "[AI Router] Complex question detected."
                )

                return True

        return False

    # ========================================================
    # MULTI-TOPIC
    # ========================================================

    def is_multi_topic(self, question):

        q = question.lower().strip()

        # Multiple concepts explicitly connected with "and"

        multi_concept_patterns = [
            r"\bexplain\b.+\band\b.+",
            r"\bdescribe\b.+\band\b.+",
            r"\bdiscuss\b.+\band\b.+",
            r"\bcompare\b.+\band\b.+",
            r"\bcontrast\b.+\band\b.+",
        ]

        for pattern in multi_concept_patterns:

            if re.search(pattern, q):

                print(
                    "[AI Router] Multi-topic question detected."
                )

                return True

        # Explicit multi-part question structures

        multi_part_patterns = [
            r"\bexplain\b.+,\s*and\b.+",
            r"\bwhat are\b.+\band\b.+",
            r"\bhow does\b.+\band\b.+",
            r"\bhow do\b.+\band\b.+",
            r"\bwhy\b.+\band\b.+",
        ]

        for pattern in multi_part_patterns:

            if re.search(pattern, q):

                print(
                    "[AI Router] Multi-topic question detected."
                )

                return True

        return False

    # ========================================================
    # SIMPLE QUESTIONS
    # ========================================================

    def is_simple(self, question):

        q = question.lower().strip()

        simple_patterns = [
            r"^what is\b",
            r"^what are\b",
            r"^who is\b",
            r"^who was\b",
            r"^when\b",
            r"^where\b",
            r"^define\b",
            r"^meaning of\b",
            r"^name\b",
            r"^list\b",
        ]

        for pattern in simple_patterns:

            if re.search(pattern, q):

                print(
                    "[AI Router] Simple question detected."
                )

                return True

        return False

    # ========================================================
    # MAIN ROUTING
    # ========================================================

    def route(self, question):

        # External/current information

        if self.is_external(question):

            print("[Router] Route: external")

            return "external"

        # Calculation

        if self.is_calculation(question):

            print("[Router] Route: calculation")

            return "calculation"

        # Complex reasoning

        if self.is_complex(question):

            print("[Router] Route: gemini")

            return "gemini"

        # Multiple concepts

        if self.is_multi_topic(question):

            print("[Router] Route: gemini")

            return "gemini"

        # Simple factual question

        if self.is_simple(question):

            print("[Router] Route: local")

            return "local"

        # Default local route

        print("[Router] Route: local")

        return "local"


# ============================================================
# DIRECT TEST
# ============================================================

if __name__ == "__main__":

    router = AIRouter()

    test_questions = [

        "What is the formula of Ohm's Law?",

        "What are Python variables?",

        "What are the applications of photosynthesis?",

        "Explain Ohm's Law and Kirchhoff's Voltage Law.",

        "Explain the working principle and applications of a transformer.",

        "Calculate the current when voltage is 24V and resistance is 8Ω.",

        "What are the latest developments in AI?",

    ]

    print()
    print("=" * 60)
    print("AI ROUTER TEST")
    print("=" * 60)

    for question in test_questions:

        print()
        print("Question:", question)

        route = router.route(question)

        print("Route:", route)