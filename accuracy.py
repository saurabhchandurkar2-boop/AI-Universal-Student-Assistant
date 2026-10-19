class AccuracyLayer:

    def classify_question(self, question):

        q = question.lower().strip()

        if any(word in q for word in [
            "calculate",
            "solve",
            "compute",
            "find",
            "how much",
            "what is the value"
        ]):
            return "calculation"

        if any(word in q for word in [
            "upsc",
            "ias",
            "civil services",
            "competitive exam",
            "mcq",
            "multiple choice"
        ]):
            return "exam"

        if any(word in q for word in [
            "explain",
            "what is",
            "define",
            "meaning",
            "why",
            "how does"
        ]):
            return "explanation"

        if any(word in q for word in [
            "code",
            "python",
            "java",
            "javascript",
            "programming",
            "algorithm"
        ]):
            return "programming"

        return "general"

    def build_instruction(self, question):

        category = self.classify_question(question)

        instructions = {

            "calculation":
                "Show the correct formula, substitute the values, "
                "calculate carefully, and give the final answer with units.",

            "exam":
                "Give accurate exam-relevant information. "
                "Do not invent dates, events, names, or facts.",

            "explanation":
                "Explain clearly at the user's likely level. "
                "Start with the direct answer and avoid unnecessary repetition.",

            "programming":
                "Give technically correct code or concepts. "
                "Use a simple example when useful.",

            "general":
                "Answer the user's exact question accurately and clearly."
        }

        return instructions.get(
            category,
            instructions["general"]
        )