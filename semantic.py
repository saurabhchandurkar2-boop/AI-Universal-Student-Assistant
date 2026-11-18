"""
semantic.py - search your notes by MEANING, not only by matching words.

Word search misses "how do plants make food?" when the notes say "photosynthesis".
This module turns every piece of text into a short list of numbers (an embedding)
so that pieces with a similar meaning end up close together.

It is OPTIONAL and safe:
  * It needs the small `fastembed` package (about 80 MB model, runs on the CPU).
    Without it the app keeps using word search exactly as before.
  * If anything goes wrong it switches itself off and word search carries on.
  * Embeddings are saved on disk, so each piece of text is embedded only once.

Turn it off with the environment variable SEMANTIC_SEARCH=0.
"""
import hashlib
import importlib.util
import json
import os

import numpy as np

MODEL_NAME = os.getenv("SEMANTIC_MODEL", "BAAI/bge-small-en-v1.5")
# bge models work best when a search question starts with this sentence.
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


def package_installed() -> bool:
    """True when fastembed is installed (checked without importing it)."""
    return importlib.util.find_spec("fastembed") is not None


def wanted() -> bool:
    """False when the owner switched meaning search off."""
    return os.getenv("SEMANTIC_SEARCH", "1").strip().lower() not in ("0", "off", "false", "no")


class FastEmbedder:
    """Real embedder. The model is downloaded the first time it is used."""

    name = MODEL_NAME

    def __init__(self):
        self._model = None

    def _load(self):
        if self._model is None:
            from fastembed import TextEmbedding

            self._model = TextEmbedding(model_name=MODEL_NAME)
        return self._model

    def embed(self, texts, is_query=False):
        model = self._load()
        if is_query:
            texts = [QUERY_PREFIX + t for t in texts]
        vectors = np.array(list(model.embed(list(texts))), dtype="float32")
        return _normalise(vectors)


def _normalise(vectors):
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return vectors / norms


def _key(model_name: str, text: str) -> str:
    return hashlib.sha1((model_name + "\n" + " ".join(text.split())).encode("utf-8")).hexdigest()


class SemanticIndex:
    """Embeds chunks (cached on disk) and finds the ones closest in meaning to a question."""

    def __init__(self, embedder=None, cache_path=None, batch_size=32):
        self.embedder = embedder or FastEmbedder()
        self.cache_path = cache_path
        self.batch_size = batch_size
        self._cache = None          # key -> list of floats, loaded lazily
        self._keys = []             # one key per indexed chunk
        self._matrix = None         # chunks x dimensions
        self.embedded_now = 0       # how many chunks needed a fresh embedding last time

    # ---------------- cache ----------------

    def _load_cache(self):
        if self._cache is not None:
            return
        self._cache = {}
        if self.cache_path and os.path.exists(self.cache_path):
            try:
                with open(self.cache_path, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                if saved.get("model") == getattr(self.embedder, "name", ""):
                    self._cache = {k: v for k, v in saved.get("vectors", {}).items()}
            except Exception:
                self._cache = {}

    def _save_cache(self, wanted_keys):
        if not self.cache_path:
            return
        try:
            folder = os.path.dirname(self.cache_path)
            if folder:
                os.makedirs(folder, exist_ok=True)
            vectors = {k: self._cache[k] for k in wanted_keys if k in self._cache}
            tmp = self.cache_path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump({"model": getattr(self.embedder, "name", ""),
                           "vectors": {k: [round(float(x), 5) for x in v] for k, v in vectors.items()}}, f)
            os.replace(tmp, self.cache_path)
        except Exception:
            pass  # the cache is only a speed-up

    # ---------------- building ----------------

    def build(self, texts):
        """Embed the texts (only the ones not seen before). Order is kept."""
        self._load_cache()
        name = getattr(self.embedder, "name", "")
        self._keys = [_key(name, t) for t in texts]

        missing = {}
        for key, text in zip(self._keys, texts):
            if key not in self._cache and key not in missing:
                missing[key] = text
        self.embedded_now = len(missing)

        items = list(missing.items())
        for start in range(0, len(items), self.batch_size):
            batch = items[start:start + self.batch_size]
            vectors = self.embedder.embed([t for _, t in batch])
            for (key, _), vector in zip(batch, vectors):
                self._cache[key] = [float(x) for x in vector]

        if missing:
            self._save_cache(set(self._keys))

        if self._keys:
            self._matrix = _normalise(np.array([self._cache[k] for k in self._keys], dtype="float32"))
        else:
            self._matrix = None

    # ---------------- searching ----------------

    def similarities(self, question):
        """Cosine similarity of the question with every indexed chunk (same order)."""
        if self._matrix is None:
            return np.zeros(0, dtype="float32")
        query = self.embedder.embed([question], is_query=True)
        return (self._matrix @ query[0]).astype("float32")

    def search(self, question, top_k=3, min_sim=0.6, margin=0.1):
        """[(chunk_index, similarity)] best first.

        Only chunks with similarity >= min_sim, and within `margin` of the best one,
        are returned, so a weak question does not drag in unrelated notes.
        """
        sims = self.similarities(question)
        if not len(sims):
            return []
        best = float(sims.max())
        if best < min_sim:
            return []
        order = np.argsort(-sims)[:top_k]
        return [(int(i), float(sims[i])) for i in order
                if sims[i] >= min_sim and sims[i] >= best - margin]
