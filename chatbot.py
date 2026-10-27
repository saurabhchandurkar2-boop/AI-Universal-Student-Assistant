# ============================================================
# AI Student Assistant - Chatbot V26.4.3
# ============================================================
#
# Architecture:
# Qwen + Local RAG + Web RAG + Gemini + Tavily
#
# V26.4.3
# - Stability + Performance + Answer Quality
# - Smart local token selection handled by AIEngine
# - Question extraction handled by AIEngine
# - Calculation routing preserved
# - Local RAG preserved
# - Web RAG preserved
# - Gemini RAG preserved
# - Tavily external search preserved
# - Controlled conversation memory preserved
# - Quality control preserved
# - Gemini 429 quota protection added
# - Gemini quota failure is cached
# - Prevents repeated Gemini calls after quota exhaustion
# - Existing fallbacks preserved
# - app.py compatibility preserved
# ============================================================

import re
import time

from ai_engine import AIEngine
from ai_router import AIRouter
from accuracy import AccuracyLayer
from chunk_filter import filter_results, page_of
from quality_control import QualityController
from knowledge.retriever import KnowledgeRetriever
from tavily_web_search import TavilyWebSearch


class StudentChatbot:

    # ========================================================
    # VERSION
    # ========================================================

    VERSION = "V26.4.4"

    # ========================================================
    # PERFORMANCE / SAFETY SETTINGS
    # ========================================================

    MAX_CONVERSATION_MESSAGES = 2

    RAG_TOP_K = 2

    WEB_MAX_RESULTS = 5

    WEB_RAG_MAX_CHARS = 1800

    LOCAL_KNOWLEDGE_MAX_CHARS = 1600

    # Gemini quota protection
    GEMINI_QUOTA_PROTECTION = True

    # ========================================================
    # INITIALIZATION
    # ========================================================

    def __init__(self):

        print("=" * 70)

        print(
            f"AI Student Assistant {self.VERSION}"
        )

        print(
            "Local RAG + Web RAG Architecture"
        )

        print(
            "Qwen + Local RAG + Web RAG + Gemini + Tavily"
        )

        print(
            "External questions -> Tavily + Gemini"
        )

        print(
            "Web RAG fallback -> Tavily + Qwen"
        )

        print(
            "V26 -> Stability + Performance + Answer Quality"
        )

        print(
            "Qwen controlled retry -> Enabled"
        )

        print(
            "Stage performance diagnostics -> Enabled"
        )

        print(
            "Web Reliability -> Enabled"
        )

        print(
            "Controlled conversation memory -> Enabled"
        )

        print(
            "Automatic knowledge pipeline -> Enabled"
        )

        print(
            "Optimized local RAG -> Enabled"
        )

        print(
            "Web RAG Performance Optimization -> Enabled"
        )

        print(
            "Gemini RAG Performance Optimization -> Enabled"
        )

        print(
            "Gemini 429 Quota Protection -> Enabled"
        )

        print(
            "SAFE MODE -> Enabled"
        )

        print(
            "ONE SYSTEM PROMPT -> Enabled"
        )

        print("=" * 70)

        # ====================================================
        # CORE COMPONENTS
        # ====================================================

        self.accuracy = AccuracyLayer()

        self.quality_control = QualityController()

        self.knowledge = KnowledgeRetriever()

        self.router = AIRouter()

        self.ai_engine = AIEngine()

        self.web_search = TavilyWebSearch()

        # ====================================================
        # CONVERSATION MEMORY
        # ====================================================

        self.conversation = []

        # ====================================================
        # GEMINI QUOTA STATE
        # ====================================================

        self.gemini_quota_exhausted = False

        self.gemini_quota_message = ""

        # Time at which Gemini quota protection was activated
        self.gemini_quota_time = None

        # Details of the most recent answer (used by the UI)
        self.last_sources = []
        self.last_route = ""

        # Use Wikipedia when the student's notes have no good match.
        # NOTES_MIN_SCORE: real matches score above ~3, unrelated ones below 1.
        self.use_wikipedia = True
        self.NOTES_MIN_SCORE = 1.5

    # ========================================================
    # CONVERSATION
    # ========================================================

    def clear_conversation(self):

        self.conversation = []

        print(
            "[Conversation] Memory cleared."
        )

    # ========================================================
    # CONVERSATION MEMORY
    # ========================================================

    def _add_conversation(
        self,
        role,
        content
    ):

        if not content:
            return

        self.conversation.append(
            {
                "role": role,
                "content": str(content)
            }
        )

        # Keep only the latest messages.
        if len(self.conversation) > self.MAX_CONVERSATION_MESSAGES:

            self.conversation = (
                self.conversation[
                    -self.MAX_CONVERSATION_MESSAGES:
                ]
            )

    # ========================================================
    # LOCAL KNOWLEDGE
    # ========================================================

    def _wikipedia_context(self, question):
        """Wikipedia text for the question, or "" (never raises)."""

        try:

            from wiki_search import lookup, as_context

            pages = lookup(question)

            if not pages:
                return ""

            self.last_sources = [
                {
                    "filename": page["title"],
                    "snippet": page["extract"][:220],
                    "url": page["url"],
                    "kind": "wikipedia",
                }
                for page in pages
            ]

            print("[Wikipedia] Using:", ", ".join(p["title"] for p in pages))

            return as_context(pages)[:self.LOCAL_KNOWLEDGE_MAX_CHARS]

        except Exception as error:

            print("[Wikipedia] Skipped:", error)

            return ""

    def get_knowledge(
        self,
        question
    ):

        self.last_sources = []

        try:

            start = time.time()

            results = self.knowledge.search(
                question,
                top_k=self.RAG_TOP_K
            )

            # Drop covers, copyright pages and tables of contents.
            results = filter_results(results)

            # Remember which documents were used (shown under the answer).
            if isinstance(results, list):

                seen = set()

                for item in results:

                    if not isinstance(item, dict):
                        continue

                    name = item.get("filename") or ""
                    text = str(item.get("text") or item.get("content") or "")

                    if not name or name in seen:
                        continue

                    seen.add(name)

                    source = {
                        "filename": name,
                        "snippet": " ".join(text.split())[:220],
                    }

                    page = page_of(item.get("path"), text)

                    if page:
                        source["page"] = page

                    self.last_sources.append(source)

            elapsed = (
                time.time() - start
            )

            print(
                f"[Performance] Local RAG: "
                f"{elapsed:.2f}s"
            )

            # Weak or no match in the notes: try Wikipedia instead.
            best_score = 0.0

            if isinstance(results, list):

                for item in results:

                    if isinstance(item, dict):

                        best_score = max(
                            best_score,
                            float(item.get("score", 0) or 0)
                        )

            if (
                self.use_wikipedia
                and (
                    not results
                    or (
                        isinstance(results, list)
                        and best_score < self.NOTES_MIN_SCORE
                    )
                )
            ):

                wiki_context = self._wikipedia_context(question)

                if wiki_context:
                    return wiki_context

            if not results:

                print(
                    "[RAG] No local knowledge found."
                )

                return ""

            print(
                "[RAG] Knowledge found."
            )

            # ------------------------------------------------
            # Normalize retriever output
            # ------------------------------------------------

            if isinstance(
                results,
                str
            ):

                text = results

            elif isinstance(
                results,
                list
            ):

                parts = []

                for item in results:

                    if isinstance(
                        item,
                        str
                    ):

                        parts.append(item)

                    elif isinstance(
                        item,
                        dict
                    ):

                        content = (
                            item.get("content")
                            or item.get("text")
                            or item.get("chunk")
                            or ""
                        )

                        if content:

                            parts.append(
                                str(content)
                            )

                text = "\n\n".join(
                    parts
                )

            else:

                text = str(
                    results
                )

            text = text.strip()

            # ------------------------------------------------
            # Compact local context
            # ------------------------------------------------

            if len(text) > self.LOCAL_KNOWLEDGE_MAX_CHARS:

                text = text[
                    :self.LOCAL_KNOWLEDGE_MAX_CHARS
                ]

            return text

        except Exception as error:

            print(
                "[RAG] Local knowledge error:",
                error
            )

            return ""

    # ========================================================
    # EXTERNAL QUESTION CHECK
    # ========================================================

    def check_external(
        self,
        question
    ):

        try:

            return self.router.is_external(
                question
            )

        except Exception:

            q = question.lower()

            external_words = [

                "latest",
                "today",
                "current",
                "now",
                "recent",
                "news",
                "weather",
                "temperature",
                "live",
                "current price",
                "ranking",
                "live score",
                "current events",

            ]

            return any(
                word in q
                for word in external_words
            )

    # ========================================================
    # WEB SEARCH
    # ========================================================

    def search_web(
        self,
        question
    ):

        try:

            start = time.time()

            results = self.web_search.search(
                question,
                max_results=self.WEB_MAX_RESULTS
            )

            elapsed = (
                time.time() - start
            )

            print(
                f"[Performance] Web Search: "
                f"{elapsed:.2f}s"
            )

            return results

        except Exception as error:

            print(
                "[Web] Search error:",
                error
            )

            return []

    # ========================================================
    # WEB KNOWLEDGE
    # ========================================================

    def get_web_knowledge(
        self,
        question
    ):

        results = self.search_web(
            question
        )

        if not results:

            return ""

        # ----------------------------------------------------
        # Normalize Tavily output
        #
        # TavilyWebSearch.search() returns:
        # {
        #     "answer": "...",
        #     "results": [...]
        # }
        # ----------------------------------------------------

        if isinstance(results, dict):

            parts = []

            # Tavily-generated web summary
            answer = results.get(
                "answer",
                ""
            )

            if answer:

                parts.append(
                    "WEB SUMMARY:\n"
                    + str(answer).strip()
                )

            # Tavily source results
            source_results = results.get(
                "results",
                []
            )

            if isinstance(
                source_results,
                list
            ):

                for result in source_results:

                    if isinstance(
                        result,
                        str
                    ):

                        parts.append(
                            result.strip()
                        )

                    elif isinstance(
                        result,
                        dict
                    ):

                        title = result.get(
                            "title",
                            ""
                        )

                        content = (
                            result.get("content")
                            or result.get("snippet")
                            or result.get("text")
                            or ""
                        )

                        url = result.get(
                            "url",
                            ""
                        )

                        block = ""

                        if title:

                            block += (
                                f"Title: {title}\n"
                            )

                        if content:

                            block += (
                                f"Information: {content}\n"
                            )

                        if url:

                            block += (
                                f"Source: {url}\n"
                            )

                        if block:

                            parts.append(
                                block.strip()
                            )

            context = "\n\n".join(
                parts
            ).strip()

            # Keep Web RAG context compact.
            if len(context) > self.WEB_RAG_MAX_CHARS:

                context = context[
                    :self.WEB_RAG_MAX_CHARS
                ]

                print(
                    "[Web RAG] Context compacted to "
                    f"{self.WEB_RAG_MAX_CHARS} characters."
                )

            return context

        # ----------------------------------------------------
        # Backward compatibility: string output
        # ----------------------------------------------------

        if isinstance(
            results,
            str
        ):

            return results.strip()

        # ----------------------------------------------------
        # Backward compatibility: list output
        # ----------------------------------------------------

        if isinstance(
            results,
            list
        ):

            parts = []

            for result in results:

                if isinstance(
                    result,
                    str
                ):

                    parts.append(
                        result.strip()
                    )

                elif isinstance(
                    result,
                    dict
                ):

                    title = result.get(
                        "title",
                        ""
                    )

                    content = (
                        result.get("content")
                        or result.get("snippet")
                        or result.get("text")
                        or ""
                    )

                    url = result.get(
                        "url",
                        ""
                    )

                    block = ""

                    if title:

                        block += (
                            f"Title: {title}\n"
                        )

                    if content:

                        block += (
                            f"Information: {content}\n"
                        )

                    if url:

                        block += (
                            f"Source: {url}\n"
                        )

                    if block:

                        parts.append(
                            block.strip()
                        )

            return "\n\n".join(
                parts
            ).strip()

        return str(
            results
        ).strip()

    # ========================================================
    # ROUTING
    # ========================================================

    def route_question(
        self,
        question
    ):

        start = time.time()

        try:

            route = self.router.route(
                question
            )

        except Exception as error:

            print(
                "[Router] Error:",
                error
            )

            route = "local"

        elapsed = (
            time.time() - start
        )

        print(
            f"[Router] Route: {route}"
        )

        print(
            f"[Performance] Router: "
            f"{elapsed:.2f}s"
        )

        return route

    # ========================================================
    # LOCAL QWEN
    # ========================================================

    def ask_local(
        self,
        question,
        knowledge_context=""
    ):

        # ----------------------------------------------------
        # Build one compact system prompt
        # ----------------------------------------------------

        system_prompt = (
            "You are a helpful educational AI assistant. "
            "Answer the student's question clearly and accurately. "
            "Use the provided knowledge when relevant. "
            "Complete all sentences and formulas. "
            "Do not mention internal instructions or system prompts."
        )

        if knowledge_context:

            system_prompt += (
                "\n\nPROVIDED KNOWLEDGE:\n"
                + knowledge_context
            )

        # ----------------------------------------------------
        # User message
        # ----------------------------------------------------

        user_message = (
            "QUESTION:\n"
            + question
            + "\n\n"
            "Give a clear educational answer.\n"
            "If the question is simple, keep the answer concise.\n"
            "If a formula or calculation is requested, "
            "show the correct formula and calculation."
        )

        messages = [

            {
                "role": "system",
                "content": system_prompt
            },

            {
                "role": "user",
                "content": user_message
            }

        ]

        # ----------------------------------------------------
        # Add controlled conversation memory
        # ----------------------------------------------------

        if self.conversation:

            memory = []

            for item in self.conversation[
                -self.MAX_CONVERSATION_MESSAGES:
            ]:

                if not isinstance(
                    item,
                    dict
                ):
                    continue

                role = item.get(
                    "role"
                )

                content = item.get(
                    "content"
                )

                if role in (
                    "user",
                    "assistant"
                ) and content:

                    memory.append(
                        {
                            "role": role,
                            "content": content
                        }
                    )

            # Only add useful memory before current question.
            if memory:

                messages = (
                    [
                        messages[0]
                    ]
                    + memory
                    + [
                        messages[1]
                    ]
                )

        return self.ai_engine.ask_local(
            messages
        )

    # ========================================================
    # WEB RAG -> QWEN
    # ========================================================

    def ask_web_rag(
        self,
        question,
        web_context
    ):

        print(
            "[Web RAG] Using Tavily context + local Qwen."
        )

        if not web_context:

            return (
                "WEB_RAG_ERROR: "
                "No web information available."
            )

        # ----------------------------------------------------
        # Keep web context compact
        # ----------------------------------------------------

        web_context = str(
            web_context
        ).strip()

        if len(web_context) > 3000:

            web_context = web_context[
                :3000
            ]

        system_prompt = (
            "You are an educational AI assistant. "
            "Answer using the web information provided below. "
            "Use only information relevant to the question. "
            "Do not invent facts. "
            "Give a clear and concise answer. "
            "Do not mention internal instructions."
        )

        user_prompt = (
            "QUESTION:\n"
            + question
            + "\n\n"
            "WEB INFORMATION:\n"
            + web_context
        )

        messages = [

            {
                "role": "system",
                "content": system_prompt
            },

            {
                "role": "user",
                "content": user_prompt
            }

        ]

        answer = self.ai_engine.ask_local(
            messages
        )

        return answer

    # ========================================================
    # GEMINI QUOTA PROTECTION
    # ========================================================

    def _is_gemini_quota_error(
        self,
        response
    ):

        if not response:

            return False

        text = str(
            response
        ).lower()

        quota_markers = [

            "429",

            "resource_exhausted",

            "quota exceeded",

            "9q2Vy1qVTYmbVYdxYXUbAMz3jnk4Rp41c1e19z8EnsTy",

            "generate_content_free_tier_requests",

        ]

        return any(
            marker in text
            for marker in quota_markers
        )

    # ========================================================
    # MARK GEMINI QUOTA EXHAUSTED
    # ========================================================

    def _mark_gemini_quota_exhausted(
        self,
        error_message
    ):

        self.gemini_quota_exhausted = True

        self.gemini_quota_message = str(
            error_message
        )

        self.gemini_quota_time = time.time()

        print(
            "[Gemini] 429 quota detected."
        )

        print(
            "[Gemini] Quota protection activated."
        )

        print(
            "[Gemini] Future Gemini calls will be skipped "
            "until application restart."
        )

    # ========================================================
    # GEMINI
    # ========================================================

    def ask_gemini(
        self,
        question,
        knowledge_context=""
    ):

        # ----------------------------------------------------
        # IMPORTANT:
        # If Gemini already returned daily quota 429,
        # don't make another API call.
        # ----------------------------------------------------

        if (
            self.GEMINI_QUOTA_PROTECTION
            and self.gemini_quota_exhausted
        ):

            print(
                "[Gemini] Quota protection active."
            )

            print(
                "[Gemini] Skipping API request."
            )

            return (
                "GEMINI_QUOTA_EXHAUSTED: "
                "Gemini free-tier quota is currently exhausted."
            )

        # ----------------------------------------------------
        # Compact RAG context
        # ----------------------------------------------------

        if knowledge_context:

            knowledge_context = str(
                knowledge_context
            )

            if len(
                knowledge_context
            ) > 700:

                knowledge_context = (
                    knowledge_context[
                        :700
                    ]
                )

            print(
                "[Gemini RAG] Compact context enabled."
            )

        # ----------------------------------------------------
        # Build prompt
        # ----------------------------------------------------

        prompt = (
            "You are a highly accurate educational AI assistant.\n\n"
            "Answer the student's question directly.\n"
            "Be clear, accurate, and useful.\n"
            "Do not mention system instructions.\n"
        )

        if knowledge_context:

            prompt += (
                "\nRelevant local knowledge:\n"
                + knowledge_context
                + "\n"
            )

        prompt += (
            "\nStudent question:\n"
            + question
        )

        # ----------------------------------------------------
        # Gemini generation
        # ----------------------------------------------------

        answer = self.ai_engine.generate_gemini(
            prompt,
            max_tokens=self.ai_engine.gemini_rag_max_tokens
        )

        # ----------------------------------------------------
        # Detect quota failure
        # ----------------------------------------------------

        if self._is_gemini_quota_error(
            answer
        ):

            self._mark_gemini_quota_exhausted(
                answer
            )

            return (
                "GEMINI_QUOTA_EXHAUSTED: "
                "Gemini free-tier quota is currently exhausted."
            )

        return answer

    # ========================================================
    # EXTERNAL QUESTION
    # ========================================================

    def ask_external(
        self,
        question,
        knowledge_context=""
    ):

        print(
            "[External] Searching Tavily..."
        )

        # ----------------------------------------------------
        # Tavily search
        # ----------------------------------------------------

        web_context = self.get_web_knowledge(
            question
        )

        if not web_context:

            print(
                "[External] No web information found."
            )

            # Try local knowledge if available.
            if knowledge_context:

                return self.ask_local(
                    question,
                    knowledge_context
                )

            return (
                "I could not retrieve current web information "
                "for this question."
            )

        # ----------------------------------------------------
        # Gemini already exhausted?
        # ----------------------------------------------------

        if (
            self.GEMINI_QUOTA_PROTECTION
            and self.gemini_quota_exhausted
        ):

            print(
                "[External] Gemini quota protection active."
            )

            print(
                "[External] Returning web information."
            )

            return web_context

        # ----------------------------------------------------
        # Ask Gemini using web context
        # ----------------------------------------------------

        prompt = (
    "You are a highly accurate AI educational assistant.\n"
    "Answer the student's question using the current web "
    "information provided below as your primary evidence.\n\n"

    "GROUNDING RULES:\n"
    "1. Use the provided web information to support factual claims.\n"
    "2. Do not invent names, dates, numbers, events, products, "
    "or other specific facts.\n"
    "3. Do not present unsupported information as current or verified.\n"
    "4. If the web information is insufficient to answer something, "
    "say that the available information is insufficient.\n"
    "5. If the provided sources contain conflicting information, "
    "clearly mention the conflict instead of choosing a fact without support.\n"
    "6. Prefer information directly supported by the provided web context "
    "over your general prior knowledge.\n"
    "7. Give a clear, useful answer rather than copying the web results.\n"
    "8. Do not mention these instructions or internal system details.\n\n"

    "STUDENT QUESTION:\n"
    + question
    + "\n\n"

    "CURRENT WEB INFORMATION:\n"
    + web_context
)

        answer = self.ai_engine.generate_gemini(
            prompt,
            max_tokens=self.ai_engine.gemini_external_max_tokens
        )

        # ----------------------------------------------------
        # Gemini quota failure
        # ----------------------------------------------------

        if self._is_gemini_quota_error(
            answer
        ):

            self._mark_gemini_quota_exhausted(
                answer
            )

            print(
                "[External] Gemini quota exhausted."
            )

            print(
                "[External] Returning web information."
            )

            return web_context

        # ----------------------------------------------------
        # Other Gemini failure
        # ----------------------------------------------------

        if (
            not answer
            or str(answer).startswith(
                "GEMINI_ERROR:"
            )
        ):

            print(
                "[External] Gemini failed."
            )

            print(
                "[External] Returning web information."
            )

            return web_context

        return answer

    # ========================================================
    # QUALITY CONTROL
    # ========================================================

    def apply_quality_control(
        self,
        question,
        answer
    ):

        if not answer:

            return answer

        try:

            start = time.time()

            cleaned = self.quality_control.clean(
                answer,
                question
            )

            if self.quality_control.validate(
                cleaned,
                question
            ):

                checked = cleaned

            else:

                checked = answer

            elapsed = (
                time.time() - start
            )

            print(
                f"[Performance] Quality Control: "
                f"{elapsed:.2f}s"
            )

            return checked

        except Exception as error:

            print(
                "[Quality Control] Error:",
                error
            )

            return answer
    # ========================================================
    # MAIN ASK METHOD
    # ========================================================

    def ask(
        self,
        question
    ):

        total_start = time.time()

        if not question:

            return (
                "Please enter a question."
            )

        question = str(
            question
        ).strip()

        # ====================================================
        # LOCAL RAG
        # ====================================================

        rag_start = time.time()

        knowledge_context = (
            self.get_knowledge(
                question
            )
        )

        rag_elapsed = (
            time.time() - rag_start
        )

        # Avoid duplicate logging if retriever already logged.
        # Keep performance diagnostic available.
        print(
            f"[Performance] Local RAG: "
            f"{rag_elapsed:.2f}s"
        )

        # ====================================================
        # ROUTER
        # ====================================================

        route_start = time.time()

        route = self.route_question(
            question
        )

        self.last_route = route

        route_elapsed = (
            time.time() - route_start
        )

        print(
            f"[Performance] Router: "
            f"{route_elapsed:.2f}s"
        )

        # ====================================================
        # GENERATION
        # ====================================================

        generation_start = time.time()

        answer = ""

        # ----------------------------------------------------
        # EXTERNAL
        # ----------------------------------------------------

        if route == "external":

            answer = self.ask_external(
                question,
                knowledge_context
            )

        # ----------------------------------------------------
        # CALCULATION
        # ----------------------------------------------------

        elif route == "calculation":

            answer = self.ask_local(
                question,
                knowledge_context
            )

        # ----------------------------------------------------
        # WEB RAG
        # ----------------------------------------------------

        elif route == "web_rag":

            web_context = (
                self.get_web_knowledge(
                    question
                )
            )

            if web_context:

                answer = self.ask_web_rag(
                    question,
                    web_context
                )

            else:

                answer = self.ask_local(
                    question,
                    knowledge_context
                )

        # ----------------------------------------------------
        # GEMINI / GEMINI RAG
        # ----------------------------------------------------

        elif route in (
            "gemini",
            "gemini_rag"
        ):

            answer = self.ask_gemini(
                question,
                knowledge_context
            )

            # ------------------------------------------------
            # Gemini quota fallback
            # ------------------------------------------------

            if (
                not answer
                or answer.startswith(
                    "GEMINI_QUOTA_EXHAUSTED:"
                )
                or answer.startswith(
                    "GEMINI_ERROR:"
                )
            ):

                print(
                    "[Gemini] Gemini unavailable."
                )

                # If local knowledge exists, use local Qwen.
                if knowledge_context:

                    print(
                        "[Gemini] Falling back to local Qwen."
                    )

                    answer = self.ask_local(
                        question,
                        knowledge_context
                    )

                else:

                    # Try web RAG if no local knowledge.
                    print(
                        "[Gemini] No local knowledge. "
                        "Trying web fallback."
                    )

                    web_context = (
                        self.get_web_knowledge(
                            question
                        )
                    )

                    if web_context:

                        answer = self.ask_web_rag(
                            question,
                            web_context
                        )

                    else:

                        answer = self.ask_local(
                            question,
                            ""
                        )

        # ----------------------------------------------------
        # LOCAL RAG
        # ----------------------------------------------------

        elif route == "local_rag":

            answer = self.ask_local(
                question,
                knowledge_context
            )

        # ----------------------------------------------------
        # LOCAL
        # ----------------------------------------------------

        else:

            answer = self.ask_local(
                question,
                knowledge_context
            )

        generation_elapsed = (
            time.time() - generation_start
        )

        print(
            f"[Performance] Generation: "
            f"{generation_elapsed:.2f}s"
        )

        # ====================================================
        # QUALITY CONTROL
        # ====================================================

        qc_start = time.time()

        answer = self.apply_quality_control(
            question,
            answer
        )

        qc_elapsed = (
            time.time() - qc_start
        )

        # ====================================================
        # TOTAL
        # ====================================================

        total_elapsed = (
            time.time() - total_start
        )

        print(
            f"[Performance] TOTAL: "
            f"{total_elapsed:.2f}s"
        )

        # ====================================================
        # SAVE CONVERSATION
        # ====================================================

        self._add_conversation(
            "user",
            question
        )

        self._add_conversation(
            "assistant",
            answer
        )

        print(
            "[Provider] Answer generated."
        )

        return answer

    # ========================================================
    # ANSWER WITH DETAILS (timer + sources) - used by app.py
    # ========================================================

    def ask_with_info(
        self,
        question
    ):
        """Return {"answer", "seconds", "sources", "origin"}.

        origin is "web" when the answer came from web search, otherwise
        "notes". Sources are only reported for answers based on the
        knowledge base.
        """

        self.last_sources = []
        self.last_route = ""

        start = time.time()

        answer = self.ask(question)

        seconds = time.time() - start

        origin = (
            "web"
            if self.last_route in ("external", "web_rag")
            else "notes"
        )

        if (
            origin == "notes"
            and self.last_sources
            and self.last_sources[0].get("kind") == "wikipedia"
        ):
            origin = "wikipedia"

        sources = (
            list(self.last_sources)
            if origin in ("notes", "wikipedia")
            else []
        )

        return {
            "answer": answer,
            "seconds": seconds,
            "sources": sources,
            "origin": origin,
        }

    # ========================================================
    # TERMINAL MODE
    # ========================================================

    def terminal_mode(self):

        print("=" * 70)

        print(
            f"AI Student Assistant {self.VERSION}"
        )

        print(
            "Terminal mode started."
        )

        print(
            "Type 'exit' to quit."
        )

        print(
            "Type 'clear' to clear conversation memory."
        )

        print("=" * 70)

        while True:

            try:

                question = input(
                    "\nYou: "
                ).strip()

            except KeyboardInterrupt:

                print(
                    "\nExiting..."
                )

                break

            except EOFError:

                print(
                    "\nExiting..."
                )

                break

            if not question:

                continue

            if question.lower() in (
                "exit",
                "quit"
            ):

                print(
                    "Goodbye."
                )

                break

            if question.lower() == "clear":

                self.clear_conversation()

                print(
                    "Conversation memory cleared."
                )

                continue

            answer = self.ask(
                question
            )

            print(
                "\nAssistant:"
            )

            print(
                answer
            )

            print()


