# ============================================================
# AI ENGINE V26.6.8
# ============================================================
#
# Local Qwen + Gemini AI Engine
#
# V26.6.8 improvement:
# - Gemini completeness validation
# - Gemini finish-reason validation
# - Multi-topic Gemini answer completeness validation
#
# Preserved from V26.6.7:
# - Dedicated multi-topic technical token budget
# - Smart local token selection
# - Dedicated list/application token budget
# - List/application questions get 320 tokens
# - Controlled list/application prompt optimization
# - Complete list generation from RAG context
# - Simple factual questions remain concise
# - Technical questions remain concise
# - Detailed/reasoning questions supported
# - Beginner explanations supported
# - Controlled Qwen retry preserved
# - Retry token budget increased for list answers
# - Question-aware truncation detection
# - Gemini RAG preserved
# - Gemini external generation preserved
# - Gemini formula formatting preserved
# - ask_local() compatibility with chatbot.py
# - Message-list normalization
# - Correct question extraction before token selection
# - Gemini max_tokens compatibility with chatbot.py
# - Robust Gemini response-part extraction
# - Gemini thought-part filtering
# - Gemini empty/fragment response detection
# - Gemini error propagation preserved for fallback handling
# ============================================================

import os
import re
import time

import requests


class AIEngine:

    def __init__(self):

        # ====================================================
        # LOCAL QWEN / LLAMA.CPP
        # ====================================================

        self.local_url = (
            "http://127.0.0.1:8080/v1/chat/completions"
        )

        # ----------------------------------------------------
        # Local token budgets
        # ----------------------------------------------------

        self.local_short_tokens = 64
        self.local_technical_tokens = 96

        # V26.6.7:
        # Dedicated budget for questions containing multiple
        # technical concepts.
        self.local_multi_topic_tokens = 220

        self.local_calculation_tokens = 200
        self.local_default_tokens = 144
        self.local_detail_tokens = 256

        # Dedicated token budget for complete list/application
        # answers.
        self.local_list_tokens = 320

        # Maximum local attempts.
        self.local_max_attempts = 2

        # Maximum retry token budget.
        self.local_retry_max_tokens = 400

        # Current messages used by truncation detection.
        self._current_messages = []

        # ====================================================
        # GEMINI
        # ====================================================

        self.gemini_model = "gemini-3.6-flash"

        self.gemini_rag_max_tokens = 700
        self.gemini_external_max_tokens = 600
        self.gemini_default_max_tokens = 700

        self.gemini_thinking_level = "minimal"

        self.gemini_rag_context_chars = 700
        self.gemini_context_chars = 1200

        # ----------------------------------------------------
        # Gemini client
        # ----------------------------------------------------

        self.gemini_client = None

        try:

            from google import genai

            api_key = os.getenv(
                "GEMINI_API_KEY"
            )

            if api_key:

                self.gemini_client = genai.Client(
                    api_key=api_key
                )

                print(
                    "[Gemini] Client initialized."
                )

            else:

                print(
                    "[Gemini] API key not found."
                )

        except Exception as e:

            print(
                f"[Gemini] Initialization failed: {e}"
            )

    # ========================================================
    # QUESTION EXTRACTION
    # ========================================================

    def get_user_question(self, messages):

        if not messages:
            return ""

        # ----------------------------------------------------
        # Normal string input
        # ----------------------------------------------------

        if isinstance(messages, str):

            return messages.strip()

        # ----------------------------------------------------
        # Message-list input
        # ----------------------------------------------------

        if isinstance(messages, list):

            for message in reversed(messages):

                if not isinstance(message, dict):
                    continue

                if message.get("role") != "user":
                    continue

                content = str(
                    message.get(
                        "content",
                        ""
                    )
                ).strip()

                if not content:
                    continue

                # --------------------------------------------
                # Remove common wrapper text used by chatbot
                # --------------------------------------------

                match = re.search(
                    r"question\s*:\s*(.*?)(?:\n\s*\n|\Z)",
                    content,
                    flags=re.IGNORECASE | re.DOTALL
                )

                if match:

                    extracted = match.group(1).strip()

                    if extracted:
                        return extracted

                # --------------------------------------------
                # Otherwise use complete user content
                # --------------------------------------------

                return content

        # ----------------------------------------------------
        # Dictionary message input
        # ----------------------------------------------------

        if isinstance(messages, dict):

            if messages.get("role") == "user":

                content = str(
                    messages.get(
                        "content",
                        ""
                    )
                ).strip()

                match = re.search(
                    r"question\s*:\s*(.*?)(?:\n\s*\n|\Z)",
                    content,
                    flags=re.IGNORECASE | re.DOTALL
                )

                if match:

                    extracted = match.group(1).strip()

                    if extracted:
                        return extracted

                return content

        return ""

    # ========================================================
    # CONTEXT EXTRACTION
    # ========================================================

    def extract_context_from_messages(self, messages):

        if not messages:
            return ""

        if not isinstance(messages, list):
            return ""

        # ----------------------------------------------------
        # Search system messages for provided knowledge
        # ----------------------------------------------------

        for message in messages:

            if not isinstance(message, dict):
                continue

            if message.get("role") != "system":
                continue

            content = str(
                message.get(
                    "content",
                    ""
                )
            ).strip()

            if not content:
                continue

            # -----------------------------------------------
            # Pattern used by current chatbot
            # -----------------------------------------------

            match = re.search(
                r"provided knowledge\s*:\s*(.*)",
                content,
                flags=re.IGNORECASE | re.DOTALL
            )

            if match:

                context = match.group(1).strip()

                if context:
                    return context

            # -----------------------------------------------
            # Alternative knowledge context patterns
            # -----------------------------------------------

            match = re.search(
                r"knowledge context\s*:\s*(.*)",
                content,
                flags=re.IGNORECASE | re.DOTALL
            )

            if match:

                context = match.group(1).strip()

                if context:
                    return context

        return ""

    # ========================================================
    # NORMALIZE LOCAL INPUT
    # ========================================================

    def normalize_local_input(
        self,
        question,
        context=""
    ):

        # ----------------------------------------------------
        # If question is already a normal string
        # ----------------------------------------------------

        if isinstance(question, str):

            normalized_question = question.strip()

            normalized_context = (
                str(context).strip()
                if context
                else ""
            )

            return (
                normalized_question,
                normalized_context
            )

        # ----------------------------------------------------
        # If chatbot passed the complete messages list
        # ----------------------------------------------------

        if isinstance(question, list):

            normalized_question = (
                self.get_user_question(
                    question
                )
            )

            normalized_context = (
                str(context).strip()
                if context
                else ""
            )

            # If context wasn't separately supplied,
            # extract it from the system message.
            if not normalized_context:

                normalized_context = (
                    self.extract_context_from_messages(
                        question
                    )
                )

            return (
                normalized_question,
                normalized_context
            )

        # ----------------------------------------------------
        # Dictionary input
        # ----------------------------------------------------

        if isinstance(question, dict):

            normalized_question = (
                self.get_user_question(
                    [question]
                )
            )

            normalized_context = (
                str(context).strip()
                if context
                else ""
            )

            return (
                normalized_question,
                normalized_context
            )

        return (
            str(question).strip(),
            str(context).strip()
            if context
            else ""
        )

    # ========================================================
    # SIMPLE QUESTION DETECTION
    # ========================================================

    def is_simple_question(self, question):

        if not question:
            return False

        q = question.lower().strip()

        simple_patterns = [

            r"^what\s+is\b",

            r"^what\s+are\b",

            r"^who\s+is\b",

            r"^who\s+was\b",

            r"^when\s+is\b",

            r"^when\s+was\b",

            r"^where\s+is\b",

            r"^where\s+was\b",

            r"^define\b",

            r"^definition\s+of\b",

            r"^meaning\s+of\b",

            r"^name\b",

            r"^list\b",

        ]

        return any(
            re.search(
                pattern,
                q
            )
            for pattern in simple_patterns
        )

    # ========================================================
    # TECHNICAL QUESTION DETECTION
    # ========================================================

    def is_technical_question(self, question):

        if not question:
            return False

        q = question.lower().strip()

        technical_patterns = [

            r"\bformula\b",

            r"\bequation\b",

            r"\bequations\b",

            r"\bexpression\b",

            r"\bvoltage\b",

            r"\bcurrent\b",

            r"\bresistance\b",

            r"\bcircuit\b",

            r"\bpython\b",

            r"\bprogramming\b",

            r"\balgorithm\b",

            r"\bmachine learning\b",

            r"\bneural network\b",

            r"\brag\b",

            r"\btransformer\b",

            r"\bkirchhoff\b",

            r"\bohm'?s law\b",

        ]

        return any(
            re.search(
                pattern,
                q
            )
            for pattern in technical_patterns
        )

    # ========================================================
    # MULTI-TOPIC QUESTION DETECTION
    # ========================================================

    def is_multi_topic_question(self, question):

        if not question:
            return False

        q = question.lower().strip()

        # ----------------------------------------------------
        # Must first be a technical question.
        # ----------------------------------------------------

        if not self.is_technical_question(q):
            return False

        # ----------------------------------------------------
        # Technical concept patterns.
        # ----------------------------------------------------

        concept_patterns = [

            r"\bohm'?s law\b",

            r"\bkirchhoff\b",

            r"\bvoltage\b",

            r"\bcurrent\b",

            r"\bresistance\b",

            r"\bcircuit\b",

            r"\bformula\b",

            r"\bequation\b",

            r"\bpython\b",

            r"\bprogramming\b",

            r"\balgorithm\b",

            r"\bmachine learning\b",

            r"\bneural network\b",

            r"\brag\b",

            r"\btransformer\b",

        ]

        matched_concepts = []

        for pattern in concept_patterns:

            if re.search(
                pattern,
                q
            ):

                matched_concepts.append(
                    pattern
                )

        # ----------------------------------------------------
        # Two or more technical concepts indicate a
        # multi-topic technical question.
        # ----------------------------------------------------

        if len(matched_concepts) >= 2:

            return True

        # ----------------------------------------------------
        # Explicit multi-topic conjunctions.
        # ----------------------------------------------------

        multi_topic_patterns = [

            r"\band\b.*\b(?:law|formula|equation|circuit)\b",

            r"\b(?:compare|difference between|contrast)\b",

            r"\bmultiple\b.*\bconcepts?\b",

        ]

        return any(
            re.search(
                pattern,
                q
            )
            for pattern in multi_topic_patterns
        )

    # ========================================================
    # CALCULATION QUESTION DETECTION
    # ========================================================

    def is_calculation_question(self, question):

        if not question:
            return False

        q = question.lower().strip()

        calculation_patterns = [

            r"\bcalculate\b",

            r"\bcalculation\b",

            r"\bsolve\b",

            r"\bcompute\b",

            r"\bnumerical\b",

            r"\bfind\s+the\s+value\b",

            r"\bhow\s+much\b",

            r"\bhow\s+many\b",

            r"\bpercentage\b",

            r"\bratio\b",

            r"\baverage\b",

            r"\bprobability\b",

            r"\bconvert\b",

            r"\bevaluate\b",

        ]

        return any(
            re.search(
                pattern,
                q
            )
            for pattern in calculation_patterns
        )

    # ========================================================
    # DETAIL QUESTION DETECTION
    # ========================================================

    def is_detail_question(self, question):

        if not question:
            return False

        q = question.lower().strip()

        detail_patterns = [

            r"\banalyze\b",

            r"\banalyse\b",

            r"\bcompare\b",

            r"\bcontrast\b",

            r"\bderive\b",

            r"\bprove\b",

            r"\breason\b",

            r"\bjustify\b",

            r"\bexplain\s+in\s+detail\b",

            r"\bin\s+detail\b",

            r"\bdiscuss\b",

            r"\bdeep\s+dive\b",

            r"\bin\s+depth\b",

            r"\bdetailed\b",

            r"\bdeep\b",

            r"\breasoning\b",

        ]

        return any(
            re.search(
                pattern,
                q
            )
            for pattern in detail_patterns
        )

    # ========================================================
    # LIST / APPLICATION QUESTION DETECTION
    # ========================================================

    def is_list_question(self, question):

        if not question:
            return False

        q = question.lower().strip()

        list_patterns = [

            r"\bapplications?\b",

            r"\badvantages?\b",

            r"\bdisadvantages?\b",

            r"\bbenefits?\b",

            r"\bfeatures?\b",

            r"\btypes?\b",

            r"\bexamples?\b",

            r"\buses?\b",

            r"\blimitations?\b",

            r"\bcomponents?\b",

            r"\bcharacteristics?\b",

            r"\bmethods?\b",

            r"\bfunctions?\b",

            r"\bsteps?\b",

            r"\blist\b",

            r"\bclassifications?\b",

            r"\bdifferences?\b",

        ]

        return any(
            re.search(
                pattern,
                q
            )
            for pattern in list_patterns
        )

    # ========================================================
    # LOCAL TOKEN SELECTION
    # ========================================================

    def select_local_tokens(self, question):

        q = question.lower().strip()

        print(
            "[AI Engine] Question for token selection:",
            q
        )

        # ----------------------------------------------------
        # 1. Calculation
        # ----------------------------------------------------

        if self.is_calculation_question(q):

            print(
                "[AI Engine] Token class: calculation"
            )

            return self.local_calculation_tokens

        # ----------------------------------------------------
        # 2. Explicit detailed / reasoning
        # ----------------------------------------------------

        if self.is_detail_question(q):

            print(
                "[AI Engine] Token class: detail"
            )

            return self.local_detail_tokens

        # ----------------------------------------------------
        # 3. List / application / multi-item
        # ----------------------------------------------------

        if self.is_list_question(q):

            print(
                "[AI Engine] Token class: list/application"
            )

            return self.local_list_tokens

        # ----------------------------------------------------
        # 4. Multi-topic technical question
        # ----------------------------------------------------

        if self.is_multi_topic_question(q):

            print(
                "[AI Engine] Token class: multi-topic"
            )

            return self.local_multi_topic_tokens

        # ----------------------------------------------------
        # 5. Technical / formula
        # ----------------------------------------------------

        if self.is_technical_question(q):

            print(
                "[AI Engine] Token class: technical"
            )

            return self.local_technical_tokens

        # ----------------------------------------------------
        # 6. Simple factual
        # ----------------------------------------------------

        if self.is_simple_question(q):

            print(
                "[AI Engine] Token class: simple"
            )

            return self.local_short_tokens

        # ----------------------------------------------------
        # 7. Default
        # ----------------------------------------------------

        print(
            "[AI Engine] Token class: default"
        )

        return self.local_default_tokens

    # ========================================================
    # LOCAL PROMPT OPTIMIZATION
    # ========================================================

    def optimize_local_messages(self, messages):

        question = self.get_user_question(
            messages
        )

        q = question.lower().strip()

        optimized_messages = []

        for message in messages:

            if isinstance(message, dict):

                optimized_messages.append(
                    dict(message)
                )

        optimization_instruction = None

        # ====================================================
        # 1. Simple factual question
        # ====================================================

        if (
            self.is_simple_question(question)
            and not self.is_technical_question(question)
            and not self.is_detail_question(q)
            and not self.is_list_question(question)
            and not self.is_calculation_question(question)
        ):

            optimization_instruction = (
                "For this simple factual question, "
                "answer in 1 to 2 clear sentences. "
                "Give only the key definition or fact. "
                "Be concise and complete. "
                "Stop immediately after answering. "
                "Do not add examples or unnecessary details."
            )

            print(
                "[AI Engine] Simple-question optimization: Enabled"
            )

        # ====================================================
        # 2. Detail / reasoning question
        # ====================================================

        if optimization_instruction is None:

            if self.is_detail_question(q):

                optimization_instruction = (
                    "Give a concise but complete detailed explanation of the exact question asked. "
                    "Answer the main question first, then explain the key concept clearly. "
                    "Use standard and factually correct formulas or principles when applicable. "
                    "Do not invent numbers, scenarios, examples, facts, or relationships unless they are explicitly requested or clearly supported by the provided knowledge. "
                    "Do not continue from an unrelated example or previous topic. "
                    "If an example is useful, keep it simple and clearly label it as an example. "
                    "Use short, clear sentences. "
                    "Avoid unnecessary background, repetition, and advanced details. "
                    "Prioritize factual accuracy over extra detail. "
                    "Complete the explanation within the available space."
                )

                print(
                    "[AI Engine] Detail-question optimization: Enabled"
                )

        # ====================================================
        # 3. List / application / multi-item question
        # ====================================================

        if optimization_instruction is None:

            if self.is_list_question(question):

                optimization_instruction = (
                    "Answer the question using only the provided knowledge context. "
                    "If the context contains a numbered list matching the question, include EVERY item in that list. "
                    "Use the original item names and give only one short supporting sentence per item. "
                    "Do not invent, expand, repeat, or add unrelated information. "
                    "Use a clear numbered list. "
                    "Return the COMPLETE list and stop."
                )

                print(
                    "[AI Engine] List/application optimization: Enabled"
                )

        # ====================================================
        # 4. Multi-topic technical question
        # ====================================================

        if optimization_instruction is None:

            if self.is_multi_topic_question(q):

                optimization_instruction = (
                    "This question contains multiple technical concepts. "
                    "Answer EVERY concept asked in the question. "
                    "Do not stop after explaining only the first concept. "
                    "Give the definition or main principle of each concept. "
                    "Include the relevant formula when applicable. "
                    "Use short clear paragraphs or numbered points. "
                    "Keep each concept concise but complete. "
                    "Do not add unrelated information. "
                    "Make sure the final answer is complete before stopping."
                )

                print(
                    "[AI Engine] Multi-topic optimization: Enabled"
                )

        # ====================================================
        # 5. Technical / formula question
        # ====================================================

        if optimization_instruction is None:

            if (
                self.is_technical_question(question)
                and not self.is_list_question(question)
                and not self.is_calculation_question(question)
            ):

                optimization_instruction = (
                    "Answer this technical question directly and accurately. "
                    "Give the key definition or principle first. "
                    "Include the relevant formula if applicable. "
                    "Keep the answer concise and complete in about 50-80 words. "
                    "Use only the essential explanation needed to answer the question. "
                    "Do not add examples, history, advanced details, or extra discussion unless requested. "
                    "Stop immediately after the answer is complete."
                )

                print(
                    "[AI Engine] Technical-question optimization: Enabled"
                )

        # ====================================================
        # 6. Beginner explanation
        # ====================================================

        if optimization_instruction is None:

            beginner_patterns = [

                r"\bexplain\b.*\bto\s+a\s+beginner\b",

                r"\bexplain\b.*\bin\s+simple\s+words\b",

                r"\bexplain\b.*\bsimply\b",

                r"\bexplain\b.*\bin\s+simple\s+terms\b",

            ]

            if any(
                re.search(
                    pattern,
                    q
                )
                for pattern in beginner_patterns
            ):

                optimization_instruction = (
                    "Give a very concise, beginner-friendly explanation. "
                    "Keep the answer around 60 to 80 words. "
                    "State the main idea clearly, include the formula only if useful, "
                    "and give at most one simple example. "
                    "Do not add introductions, repetition, advanced details, "
                    "or extra conclusions. "
                    "Answer the question directly and stop."
                )

                print(
                    "[AI Engine] Beginner-explanation optimization: Enabled"
                )

        # ====================================================
        # 7. Merge optimization into existing system prompt
        # ====================================================

        if optimization_instruction:

            system_index = None

            for index, message in enumerate(
                optimized_messages
            ):

                if (
                    isinstance(message, dict)
                    and message.get("role") == "system"
                ):

                    system_index = index

                    break

            if system_index is not None:

                existing_system = (
                    optimized_messages[
                        system_index
                    ].get(
                        "content",
                        ""
                    )
                )

                existing_system = str(
                    existing_system
                ).strip()

                optimized_messages[
                    system_index
                ]["content"] = (
                    existing_system
                    + "\n\n"
                    + optimization_instruction
                )

            else:

                optimized_messages.insert(
                    0,
                    {
                        "role": "system",
                        "content": optimization_instruction
                    }
                )

        return optimized_messages

    # ========================================================
    # TRUNCATION DETECTION
    # ========================================================

    def looks_truncated(
        self,
        text,
        finish_reason=None
    ):

        if not text:
            return True

        text = text.strip()

        if not text:
            return True

        # ----------------------------------------------------
        # V26.6.8:
        # A length finish does not automatically mean the
        # answer is incomplete. Existing structural checks
        # below still detect obvious truncation.
        # ----------------------------------------------------

        question = self.get_user_question(
            self._current_messages
        ).lower()

        # ----------------------------------------------------
        # List questions
        # ----------------------------------------------------

        if self.is_list_question(question):

            lines = [
                line.strip()
                for line in text.splitlines()
                if line.strip()
            ]

            numbered_items = [
                line
                for line in lines
                if re.match(
                    r"^\d+[\.\)]\s+",
                    line
                )
            ]

            if len(numbered_items) >= 2:

                last_line = numbered_items[-1]

                if last_line.endswith(
                    (
                        ":",
                        ",",
                        "and",
                        "or",
                    )
                ):

                    return True

            if text.endswith(
                (
                    ":",
                    ",",
                    "and",
                    "or",
                    "-",
                )
            ):

                return True

        # ----------------------------------------------------
        # Generic unfinished sentence
        # ----------------------------------------------------

        if text.endswith(
            (
                ":",
                ",",
                "-",
            )
        ):

            return True

        # ----------------------------------------------------
        # V26.6.10:
        # Stronger detection for answers cut off by the
        # local Qwen token limit.
        #
        # Normal stop responses are not affected.
        # ----------------------------------------------------

        if str(finish_reason).lower() == "length":

            words = text.split()

            if words:

                last_word = re.sub(
                    r"[^a-zA-Z]+$",
                    "",
                    words[-1]
                ).lower()

                continuation_words = {
                    "the",
                    "a",
                    "an",
                    "this",
                    "that",
                    "these",
                    "those",
                    "which",
                    "who",
                    "because",
                    "although",
                    "while",
                    "when",
                    "where",
                    "if",
                    "as",
                    "and",
                    "or",
                    "but",
                    "than",
                    "to",
                    "of",
                    "for",
                    "with",
                    "from",
                    "into",
                    "through",
                    "by",
                    "is",
                    "are",
                    "was",
                    "were",
                    "be",
                    "been",
                    "being",
                }

                if last_word in continuation_words:

                    return True

            # Detect an obviously unfinished LaTeX expression.

            if text.count("\\[") > text.count("\\]"):

                return True

            # Detect a substantial final sentence that was
            # likely cut off by the token limit.

            # V26.7:
            # Detect common words/phrases that strongly indicate
            # the final sentence is still continuing.

            continuation_endings = (
                "particularly",
                "especially",
                "mainly",
                "primarily",
                "typically",
                "generally",
                "important to",
                "useful for",
                "necessary for",
                "essential for",
                "used to",
                "based on",
                "dependent on",
                "known as",
                "called",
                "defined as",
            )

            lowered_text = text.lower().strip()

            if any(
                lowered_text.endswith(ending)
                for ending in continuation_endings
            ):

                return True

            sentences = re.split(
                r"(?<=[.!?])\s+",
                text
            )

            last_sentence = sentences[-1].strip()

            if (
                len(words) >= 45
                and len(last_sentence.split()) >= 8
                and not last_sentence.endswith(
                    (
                        ".",
                        "!",
                        "?",
                        ")",
                        "]",
                        "}",
                        '"',
                        "'",
                    )
                )
            ):

                return True

        return False

    # ========================================================
    # LOCAL QWEN GENERATION
    # ========================================================

    def generate_local(
        self,
        messages,
        max_tokens=None
    ):

        # ----------------------------------------------------
        # Select token budget
        # ----------------------------------------------------

        if max_tokens is None:

            question = self.get_user_question(
                messages
            )

            max_tokens = self.select_local_tokens(
                question
            )

        # ----------------------------------------------------
        # Optimize prompt
        # ----------------------------------------------------

        optimized_messages = (
            self.optimize_local_messages(
                messages
            )
        )

        self._current_messages = (
            optimized_messages
        )

        current_max_tokens = max_tokens

        for attempt in range(
            self.local_max_attempts
        ):

            payload = {

                "messages":
                    optimized_messages,

                "temperature":
                    0.2,

                "max_tokens":
                    current_max_tokens,

                "stream":
                    False,
            }

            start_time = time.time()

            try:

                response = requests.post(
                    self.local_url,
                    json=payload,
                    timeout=120
                )

                elapsed = (
                    time.time()
                    - start_time
                )

                print(
                    f"[AI Engine] Local Qwen: "
                    f"{elapsed:.2f}s"
                )

                response.raise_for_status()

                data = response.json()

                choices = data.get(
                    "choices",
                    []
                )

                if not choices:

                    print(
                        "[AI Engine] "
                        "No choices returned."
                    )

                    continue

                choice = choices[0]

                message = choice.get(
                    "message",
                    {}
                )

                answer = str(
                    message.get(
                        "content",
                        ""
                    )
                ).strip()

                finish_reason = choice.get(
                    "finish_reason"
                )

                print(
                    "[AI Engine] Finish reason:",
                    finish_reason
                )

                print(
                    "[AI Engine] Output characters:",
                    len(answer)
                )

                print(
                    "[AI Engine] Output words:",
                    len(answer.split())
                )

                if not answer:

                    continue

                if self.looks_truncated(
                    answer,
                    finish_reason
                ):

                    print(
                        "[AI Engine] "
                        "Response appears incomplete."
                    )

                    if attempt + 1 < (
                        self.local_max_attempts
                    ):

                        print(
                            "[AI Engine] "
                            "Controlled retry: Enabled"
                        )

                        retry_tokens = min(
                            current_max_tokens + 80,
                            self.local_retry_max_tokens
                        )

                        print(
                            "[AI Engine] "
                            "Retry max tokens:",
                            retry_tokens
                        )

                        optimized_messages = list(
                            optimized_messages
                        )

                        optimized_messages.append(
                            {
                                "role":
                                    "assistant",

                                "content":
                                    answer
                            }
                        )

                        optimized_messages.append(
                            {
                                "role":
                                    "user",

                                "content":
                                    (
                                        "Complete the previous answer. "
                                        "Do not repeat information already given. "
                                        "Continue from exactly where the previous answer stopped. "
                                        "Finish the answer clearly and completely."
                                    )
                            }
                        )

                        self._current_messages = (
                            optimized_messages
                        )

                        current_max_tokens = retry_tokens

                        continue

                    print(
                        "[AI Engine] "
                        "Final response still incomplete."
                    )

                    return (
                        "I was unable to generate a complete response. "
                        "Please try asking the question in a shorter or simpler way."
                    )

                print(
                    "[AI Engine] "
                    "Response appears complete."
                )

                return answer

            except Exception as e:

                print(
                    f"[AI Engine] Local generation error: {e}"
                )

        return (
            "I was unable to generate a response "
            "from the local AI model."
        )

    # ========================================================
    # GEMINI RESPONSE EXTRACTION
    # ========================================================

    def extract_gemini_text(self, response):

        if response is None:
            return ""

        collected_parts = []

        # ----------------------------------------------------
        # Primary method:
        # inspect candidates -> content -> parts.
        # ----------------------------------------------------

        try:

            candidates = getattr(
                response,
                "candidates",
                None
            )

            if candidates:

                for candidate in candidates:

                    content = getattr(
                        candidate,
                        "content",
                        None
                    )

                    if content is None:
                        continue

                    parts = getattr(
                        content,
                        "parts",
                        None
                    )

                    if not parts:
                        continue

                    for part in parts:

                        if part is None:
                            continue

                        # Gemini may expose internal thought
                        # parts. Do not return those as the
                        # user-facing answer.
                        is_thought = getattr(
                            part,
                            "thought",
                            False
                        )

                        if is_thought:
                            continue

                        part_text = getattr(
                            part,
                            "text",
                            None
                        )

                        if part_text:

                            part_text = str(
                                part_text
                            ).strip()

                            if part_text:

                                collected_parts.append(
                                    part_text
                                )

        except Exception as e:

            print(
                "[Gemini] Response-part extraction warning:",
                e
            )

        # ----------------------------------------------------
        # If response parts produced usable text, return it.
        # ----------------------------------------------------

        if collected_parts:

            combined = "\n".join(
                collected_parts
            ).strip()

            if combined:

                return combined

        # ----------------------------------------------------
        # Fallback:
        # SDK response.text
        # ----------------------------------------------------

        try:

            response_text = getattr(
                response,
                "text",
                ""
            )

            if response_text:

                response_text = str(
                    response_text
                ).strip()

                if response_text:

                    return response_text

        except Exception as e:

            print(
                "[Gemini] Response.text extraction warning:",
                e
            )

        return ""

    # ========================================================
    # GEMINI FINISH REASON
    # ========================================================

    def get_gemini_finish_reason(self, response):

        if response is None:
            return ""

        try:

            candidates = getattr(
                response,
                "candidates",
                None
            )

            if not candidates:
                return ""

            candidate = candidates[0]

            finish_reason = getattr(
                candidate,
                "finish_reason",
                None
            )

            if finish_reason is None:
                return ""

            return str(
                finish_reason
            ).upper()

        except Exception as e:

            print(
                "[Gemini] Finish-reason extraction warning:",
                e
            )

            return ""

    # ========================================================
    # GEMINI MULTI-TOPIC COMPLETENESS
    # ========================================================

    def is_multi_topic_answer_complete(
        self,
        answer,
        question
    ):

        if not answer:
            return False

        if not question:
            return True

        if not self.is_multi_topic_question(
            question
        ):

            return True

        answer_lower = answer.lower()
        question_lower = question.lower()

        # ----------------------------------------------------
        # Required concept groups.
        #
        # We check only concepts explicitly present in the
        # user's question.
        # ----------------------------------------------------

        required_patterns = []

        if re.search(
            r"\bohm'?s law\b",
            question_lower
        ):

            required_patterns.append(
                (
                    "Ohm's Law",
                    r"\bohm'?s law\b"
                )
            )

        if re.search(
            r"\bkirchhoff\b",
            question_lower
        ):

            required_patterns.append(
                (
                    "Kirchhoff",
                    r"\bkirchhoff\b"
                )
            )

        if re.search(
            r"\bvoltage\b",
            question_lower
        ):

            required_patterns.append(
                (
                    "voltage",
                    r"\bvoltage\b"
                )
            )

        if re.search(
            r"\bcurrent\b",
            question_lower
        ):

            required_patterns.append(
                (
                    "current",
                    r"\bcurrent\b"
                )
            )

        if re.search(
            r"\bresistance\b",
            question_lower
        ):

            required_patterns.append(
                (
                    "resistance",
                    r"\bresistance\b"
                )
            )

        if re.search(
            r"\bcircuit\b",
            question_lower
        ):

            required_patterns.append(
                (
                    "circuit",
                    r"\bcircuit\b"
                )
            )

        if re.search(
            r"\bpython\b",
            question_lower
        ):

            required_patterns.append(
                (
                    "Python",
                    r"\bpython\b"
                )
            )

        if re.search(
            r"\bprogramming\b",
            question_lower
        ):

            required_patterns.append(
                (
                    "programming",
                    r"\bprogramming\b"
                )
            )

        if re.search(
            r"\balgorithm\b",
            question_lower
        ):

            required_patterns.append(
                (
                    "algorithm",
                    r"\balgorithm\b"
                )
            )

        if re.search(
            r"\bmachine learning\b",
            question_lower
        ):

            required_patterns.append(
                (
                    "machine learning",
                    r"\bmachine learning\b"
                )
            )

        if re.search(
            r"\bneural network\b",
            question_lower
        ):

            required_patterns.append(
                (
                    "neural network",
                    r"\bneural network\b"
                )
            )

        if re.search(
            r"\brag\b",
            question_lower
        ):

            required_patterns.append(
                (
                    "RAG",
                    r"\brag\b"
                )
            )

        if re.search(
            r"\btransformer\b",
            question_lower
        ):

            required_patterns.append(
                (
                    "transformer",
                    r"\btransformer\b"
                )
            )

        # ----------------------------------------------------
        # Every explicitly requested concept must appear in
        # the answer.
        # ----------------------------------------------------

        missing_concepts = []

        for label, pattern in required_patterns:

            if not re.search(
                pattern,
                answer_lower
            ):

                missing_concepts.append(
                    label
                )

        if missing_concepts:

            print(
                "[AI Engine] Gemini multi-topic answer "
                "missing concepts:",
                ", ".join(
                    missing_concepts
                )
            )

            return False

        return True

    # ========================================================
    # GEMINI ANSWER VALIDATION
    # ========================================================

    def is_usable_gemini_answer(
        self,
        answer,
        question="",
        finish_reason=""
    ):

        if not answer:
            return False

        answer = str(
            answer
        ).strip()

        if not answer:
            return False

        # ----------------------------------------------------
        # Very short fragments are usually not useful final
        # answers for normal student questions.
        # ----------------------------------------------------

        if len(answer) < 20:

            return False

        # ----------------------------------------------------
        # V26.6.8:
        # Reject known incomplete Gemini finish reasons.
        # ----------------------------------------------------

        normalized_finish_reason = str(
            finish_reason or ""
        ).upper()

        incomplete_finish_reasons = [

            "MAX_TOKENS",

            "LENGTH",

            "SAFETY",

            "BLOCKLIST",

            "PROHIBITED_CONTENT",

            "RECITATION",

            "MALFORMED_FUNCTION_CALL",

        ]

        for reason in incomplete_finish_reasons:

            if reason in normalized_finish_reason:

                print(
                    "[AI Engine] Gemini finish reason "
                    "indicates incomplete response:",
                    normalized_finish_reason
                )

                return False

        # ----------------------------------------------------
        # Detect obvious fragment endings.
        # ----------------------------------------------------

        stripped = answer.strip()

        if stripped.startswith(
            (
                ",",
                "*",
                "-",
                ")",
            )
        ):

            # Allow normal numbered lists.
            if not re.match(
                r"^\d+[\.\)]\s+",
                stripped
            ):

                return False

        # ----------------------------------------------------
        # V26.6.8:
        # Detect unfinished sentence endings.
        # ----------------------------------------------------

        if stripped.endswith(
            (
                ",",
                ":",
                "-",
                "(",
                "[",
                "{",
            )
        ):

            print(
                "[AI Engine] Gemini response ends with "
                "unfinished punctuation."
            )

            return False

        # ----------------------------------------------------
        # Detect a response that is mostly a fragment.
        # ----------------------------------------------------

        words = stripped.split()

        if len(words) <= 8:

            if not re.search(
                r"[.!?]$",
                stripped
            ):

                return False

        # ----------------------------------------------------
        # V26.6.8:
        # Multi-topic answers must contain all requested
        # concepts.
        # ----------------------------------------------------

        if not self.is_multi_topic_answer_complete(
            stripped,
            question
        ):

            print(
                "[AI Engine] "
                "Gemini multi-topic answer is incomplete."
            )

            return False

        return True

    # ========================================================
    # GEMINI GENERATION
    # ========================================================

    def generate_gemini(
        self,
        question,
        context="",
        max_tokens=None
    ):

        if not self.gemini_client:

            return (
                "GEMINI_ERROR: Gemini is currently unavailable."
            )

        if max_tokens is None:

            max_tokens = (
                self.gemini_rag_max_tokens
            )

        context = (
            context or ""
        )[:self.gemini_context_chars]

        prompt = (

            "You are an AI Student Assistant. "
            "Answer the user's question accurately and clearly. "
            "Use the provided knowledge context when relevant. "
            "Do not invent facts.\n\n"

            "Formatting requirements:\n"
            "- Use clear paragraphs or numbered lists when appropriate.\n"
            "- Format formulas clearly.\n"
            "- Use standard mathematical operators.\n"
            "- Use / for division when appropriate.\n"
            "- Include units when relevant.\n"
            "- For Kirchhoff's Voltage Law, use Î£V = 0 when applicable.\n"
            "- Answer all parts of a multi-part question.\n"
            "- Do not return partial fragments.\n"
            "- Finish the complete answer before stopping.\n\n"

            f"Knowledge context:\n{context}\n\n"

            f"User question:\n{question}"
        )

        try:

            start_time = time.time()

            response = (
                self.gemini_client.models.generate_content(
                    model=self.gemini_model,
                    contents=prompt,
                    config={
                        "max_output_tokens":
                            max_tokens,

                        "temperature":
                            0.2,
                    }
                )
            )

            elapsed = (
                time.time()
                - start_time
            )

            print(
                f"[AI Engine] Gemini: "
                f"{elapsed:.2f}s"
            )

            # ------------------------------------------------
            # V26.6.8:
            # Capture Gemini finish reason.
            # ------------------------------------------------

            finish_reason = (
                self.get_gemini_finish_reason(
                    response
                )
            )

            if finish_reason:

                print(
                    "[AI Engine] Gemini finish reason:",
                    finish_reason
                )

            answer = (
                self.extract_gemini_text(
                    response
                )
            )

            print(
                "[AI Engine] Gemini output characters:",
                len(answer)
            )

            print(
                "[AI Engine] Gemini output words:",
                len(answer.split())
            )

            if not self.is_usable_gemini_answer(
                answer,
                question,
                finish_reason
            ):

                print(
                    "[AI Engine] "
                    "Gemini response appears unusable."
                )

                return (
                    "GEMINI_ERROR: Gemini returned "
                    "an incomplete or unusable response."
                )

            print(
                "[AI Engine] "
                "Gemini response appears usable."
            )

            return answer

        except Exception as e:

            print(
                f"[AI Engine] Gemini generation error: {e}"
            )

            return (
                f"GEMINI_ERROR: {e}"
            )

    # ========================================================
    # GEMINI EXTERNAL
    # ========================================================

    def generate_gemini_external(
        self,
        question,
        context="",
        max_tokens=None
    ):

        if not self.gemini_client:

            return (
                "GEMINI_ERROR: Gemini is currently unavailable."
            )

        if max_tokens is None:

            max_tokens = (
                self.gemini_external_max_tokens
            )

        context = (
            context or ""
        )[:self.gemini_context_chars]

        prompt = (

            "You are an AI Student Assistant. "
            "Answer the user's question using reliable information. "
            "If context is provided, use it as supporting information. "
            "Do not invent facts.\n\n"

            "Formatting requirements:\n"
            "- Give a complete answer.\n"
            "- Use clear paragraphs or lists when appropriate.\n"
            "- Do not return partial fragments.\n\n"

            f"Context:\n{context}\n\n"

            f"Question:\n{question}"
        )

        try:

            start_time = time.time()

            response = (
                self.gemini_client.models.generate_content(
                    model=self.gemini_model,
                    contents=prompt,
                    config={
                        "max_output_tokens":
                            max_tokens,

                        "temperature":
                            0.2,
                    }
                )
            )

            elapsed = (
                time.time()
                - start_time
            )

            print(
                f"[AI Engine] Gemini external: "
                f"{elapsed:.2f}s"
            )

            # ------------------------------------------------
            # V26.6.8:
            # Capture Gemini finish reason.
            # ------------------------------------------------

            finish_reason = (
                self.get_gemini_finish_reason(
                    response
                )
            )

            if finish_reason:

                print(
                    "[AI Engine] Gemini external finish reason:",
                    finish_reason
                )

            answer = (
                self.extract_gemini_text(
                    response
                )
            )

            print(
                "[AI Engine] Gemini external output characters:",
                len(answer)
            )

            print(
                "[AI Engine] Gemini external output words:",
                len(answer.split())
            )

            if not self.is_usable_gemini_answer(
                answer,
                question,
                finish_reason
            ):

                print(
                    "[AI Engine] "
                    "Gemini external response appears unusable."
                )

                return (
                    "GEMINI_ERROR: Gemini returned "
                    "an incomplete or unusable response."
                )

            return answer

        except Exception as e:

            print(
                f"[AI Engine] Gemini external error: {e}"
            )

            return (
                f"GEMINI_ERROR: {e}"
            )

    # ========================================================
    # PUBLIC LOCAL METHOD
    # ========================================================

    def ask_local(
        self,
        question,
        context=""
    ):
        """
        Compatibility method used by chatbot.py.

        Accepts either:

        1. A normal question string
        2. The complete message list passed by chatbot.py

        The method extracts the actual user question before
        token selection and prompt optimization.
        """

        (
            normalized_question,
            normalized_context
        ) = self.normalize_local_input(
            question,
            context
        )

        print(
            "[AI Engine] Normalized question:",
            normalized_question
        )

        if normalized_context:

            print(
                "[AI Engine] Knowledge context:",
                len(normalized_context),
                "characters"
            )

        return self.answer_local(
            question=normalized_question,
            context=normalized_context
        )

    # ========================================================
    # INTERNAL LOCAL ANSWER METHOD
    # ========================================================

    def answer_local(
        self,
        question,
        context=""
    ):

        # ----------------------------------------------------
        # Normalize again for direct calls
        # ----------------------------------------------------

        (
            question,
            context
        ) = self.normalize_local_input(
            question,
            context
        )

        messages = [

            {
                "role":
                    "system",

                "content":
                    (
                        "You are an AI Student Assistant. "
                        "Answer accurately and directly. "
                        "Use the provided knowledge context. "
                        "Do not invent information. "
                        "If the context contains the answer, "
                        "base the response on that context."
                    )
            },

            {
                "role":
                    "user",

                "content":
                    (
                        f"Knowledge context:\n"
                        f"{context}\n\n"
                        f"Question:\n"
                        f"{question}"
                    )
            }
        ]

        return self.generate_local(
            messages
        )



