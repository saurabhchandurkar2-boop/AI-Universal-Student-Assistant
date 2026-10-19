"""
hosted.py - run the app on a free public host (for example Streamlit Community Cloud).

On your own computer the app talks to a local llama-server (Qwen). A free web host
cannot run that server, so "hosted mode" changes three things:

1. Answers come from Gemini, using the visitor's own free API key.
2. Every visitor gets a private, temporary knowledge base. Documents one visitor
   uploads are never visible to another visitor.
3. The owner's API keys are NOT used for visitors (set ALLOW_OWNER_KEYS=1 to allow it).

Hosted mode turns on automatically when no local llama-server answers on port 8080.
Force it with APP_MODE=hosted, or force normal mode with APP_MODE=local.
"""
import os
import re
import shutil
import tempfile
import time
from pathlib import Path

import requests

from ai_engine import AIEngine
from knowledge.retriever import KnowledgeRetriever
import knowledge_loader as kl

MAX_UPLOAD_MB = 50
MAX_DOCS_PER_VISITOR = 20
WORKSPACE_PREFIX = "sa_ws_"
WORKSPACE_MAX_AGE_SECONDS = 3 * 3600

NO_KEY_MESSAGE = (
    "No answer engine is connected yet. Paste a free Gemini API key in the "
    "sidebar under **Connect your own keys** (get one at aistudio.google.com), "
    "or run the app on your own computer with the local model."
)


# --------------------------------------------------
# Mode detection
# --------------------------------------------------

def local_server_up(timeout=1.0) -> bool:
    base = os.getenv("LLAMA_URL", "http://127.0.0.1:8080/v1/chat/completions")
    base = base.split("/v1/")[0]
    try:
        return requests.get(base + "/health", timeout=timeout).status_code == 200
    except Exception:
        return False


def is_hosted() -> bool:
    mode = os.getenv("APP_MODE", "").strip().lower()
    if mode == "hosted":
        return True
    if mode == "local":
        return False
    return not local_server_up()


# --------------------------------------------------
# Answer engine without a local model
# --------------------------------------------------

class HostedAIEngine(AIEngine):
    """AIEngine whose 'local' answers come from Gemini."""

    def __init__(self):
        super().__init__()
        if os.getenv("ALLOW_OWNER_KEYS") != "1":
            self.gemini_client = None

    def set_gemini_key(self, key: str) -> bool:
        key = (key or "").strip()
        if key and key == getattr(self, "_key", None) and self.gemini_client:
            return True
        self._key = key
        if not key:
            self.gemini_client = None
            return False
        try:
            from google import genai
            self.gemini_client = genai.Client(api_key=key)
            return True
        except Exception:
            self.gemini_client = None
            return False

    def has_key(self) -> bool:
        return self.gemini_client is not None

    def generate_local(self, messages, max_tokens=None):
        if not self.gemini_client:
            return NO_KEY_MESSAGE

        question = self.get_user_question(messages)
        context = self.extract_context_from_messages(messages)

        if not context and isinstance(messages, list):
            # answer_local puts "Knowledge context: ... Question: ..." in the user turn.
            last = str(messages[-1].get("content", "")) if messages else ""
            match = re.search(
                r"knowledge context\s*:\s*(.*?)\n\s*question\s*:",
                last, flags=re.IGNORECASE | re.DOTALL,
            )
            if match:
                context = match.group(1).strip()

        answer = self.generate_gemini(question, context=context)
        if answer.startswith("GEMINI_ERROR"):
            detail = answer.split(":", 1)[-1].strip()
            if "429" in detail or "quota" in detail.lower():
                return ("Your Gemini key has reached its free limit for now. "
                        "Wait a minute and try again.")
            if "API key" in detail or "API_KEY" in detail or "400" in detail or "403" in detail:
                return "Gemini rejected the key. Check that you pasted it correctly."
            return "Gemini could not answer right now. Please try again."
        return answer

    def simple_ask(self, system: str, user: str, max_tokens: int = 300) -> str:
        """One-shot call used by the notes summarizer."""
        if not self.gemini_client:
            raise RuntimeError(NO_KEY_MESSAGE)
        response = self.gemini_client.models.generate_content(
            model=self.gemini_model,
            contents=f"{system}\n\n{user}",
            config={"max_output_tokens": max_tokens, "temperature": 0.2},
        )
        return self.extract_gemini_text(response).strip()


# --------------------------------------------------
# Private per-visitor knowledge base
# --------------------------------------------------

def _cleanup_old_workspaces():
    root = tempfile.gettempdir()
    now = time.time()
    for entry in Path(root).glob(WORKSPACE_PREFIX + "*"):
        try:
            if now - entry.stat().st_mtime > WORKSPACE_MAX_AGE_SECONDS:
                shutil.rmtree(entry, ignore_errors=True)
        except OSError:
            pass


class Workspace:
    """A temporary folder of .txt documents that belongs to one visitor."""

    def __init__(self):
        _cleanup_old_workspaces()
        self.dir = tempfile.mkdtemp(prefix=WORKSPACE_PREFIX)
        # Start with the sample study notes shipped with the project.
        if os.path.isdir(kl.SOURCE_DIR):
            for name in os.listdir(kl.SOURCE_DIR):
                if name.lower().endswith(".txt"):
                    shutil.copy(os.path.join(kl.SOURCE_DIR, name), self.dir)

    def add(self, data: bytes, filename: str, progress=None) -> dict:
        if len(data) > MAX_UPLOAD_MB * 1024 * 1024:
            raise ValueError(f"File is larger than {MAX_UPLOAD_MB} MB (limit on the free host).")
        if len(self.list()) >= MAX_DOCS_PER_VISITOR:
            raise ValueError(f"Limit of {MAX_DOCS_PER_VISITOR} documents reached. Remove one first.")
        name, out_name, payload, pages, warning = kl.convert_upload(data, filename, progress)
        txt_name = name + ".txt"
        with open(os.path.join(self.dir, txt_name), "wb") as f:
            f.write(payload)
        return {"saved_as": txt_name, "index_success": True,
                "pages": pages, "warning": warning}

    def list(self) -> list:
        return sorted(n for n in os.listdir(self.dir) if n.lower().endswith(".txt"))

    def read(self, rel_name: str) -> str:
        target = os.path.abspath(os.path.join(self.dir, rel_name))
        if not target.startswith(os.path.abspath(self.dir) + os.sep) or not os.path.isfile(target):
            raise ValueError("Document not found.")
        with open(target, "r", encoding="utf-8", errors="replace") as f:
            return f.read()

    def remove(self, rel_name: str) -> bool:
        target = os.path.abspath(os.path.join(self.dir, rel_name))
        if not target.startswith(os.path.abspath(self.dir) + os.sep):
            raise ValueError("Invalid document name.")
        if not os.path.isfile(target):
            return False
        os.remove(target)
        return True


def make_hosted_bot():
    """Create a chatbot with a private workspace. Returns (bot, workspace)."""
    from chatbot import StudentChatbot

    bot = StudentChatbot()
    workspace = Workspace()
    bot.knowledge = KnowledgeRetriever(knowledge_path=workspace.dir)
    bot.ai_engine = HostedAIEngine()
    if os.getenv("ALLOW_OWNER_KEYS") != "1":
        bot.web_search.api_key = None
    return bot, workspace
