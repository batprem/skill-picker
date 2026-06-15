"""Embedding backends.

Production selection MUST use vLLM (Constitution IV). ``HashingEmbedder`` is a
deterministic, offline lexical embedder provided only for development and tests; it is
clearly not the production path.
"""

from __future__ import annotations

import hashlib
import re
from typing import Protocol, Sequence, runtime_checkable

import numpy as np

# e5 models expect these task prefixes; query/passage asymmetry matches our use case.
QUERY_PREFIX = "query: "
PASSAGE_PREFIX = "passage: "

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def passage_text(name: str, match_text: str) -> str:
    """Compose the deterministic text embedded for a skill."""
    return f"{name}. {match_text}".strip()


def normalize(mat: np.ndarray) -> np.ndarray:
    """L2-normalize rows; zero rows are left as zeros."""
    mat = np.asarray(mat, dtype=np.float32)
    norms = np.linalg.norm(mat, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return mat / norms


@runtime_checkable
class Embedder(Protocol):
    """Embeds text into L2-normalized vectors. Same instance is used for both sides."""

    signature: str
    dim: int

    def embed_passages(self, texts: Sequence[str]) -> np.ndarray: ...

    def embed_queries(self, texts: Sequence[str]) -> np.ndarray: ...


class VLLMEmbedder:
    """Embeds via vLLM in pooling mode using an e5 model (Constitution IV)."""

    def __init__(self, model: str = "intfloat/e5-small-v2", enforce_eager: bool = True, **llm_kwargs):
        from vllm import LLM  # imported lazily so non-vLLM paths/tests stay light

        self.model = model
        self.signature = f"{model}@pooling"
        self.dim = 0
        # On the CPU backend, gpu_memory_utilization is the fraction of CPU RAM reserved;
        # extra kwargs (e.g. gpu_memory_utilization=0.3) are forwarded for tuning.
        self._llm = LLM(model=model, runner="pooling", enforce_eager=enforce_eager, **llm_kwargs)

    def _embed(self, texts: Sequence[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, self.dim), dtype=np.float32)
        outputs = self._llm.embed(list(texts))
        embs = np.array([o.outputs.embedding for o in outputs], dtype=np.float32)
        if self.dim == 0:
            self.dim = int(embs.shape[1])
        return normalize(embs)

    def embed_passages(self, texts: Sequence[str]) -> np.ndarray:
        return self._embed([PASSAGE_PREFIX + t for t in texts])

    def embed_queries(self, texts: Sequence[str]) -> np.ndarray:
        return self._embed([QUERY_PREFIX + t for t in texts])


class HashingEmbedder:
    """Deterministic bag-of-words hashing embedder for offline/dev/testing ONLY.

    Uses a stable hash (md5) so results are identical across processes (FR-013, SC-005).
    Not semantic — do not use for production selection (Constitution IV mandates vLLM).
    """

    def __init__(self, dim: int = 256):
        self.dim = dim
        self.signature = f"hashing-bow@{dim}"

    def _embed_one(self, text: str) -> np.ndarray:
        vec = np.zeros(self.dim, dtype=np.float32)
        for tok in _TOKEN_RE.findall(text.lower()):
            bucket = int(hashlib.md5(tok.encode()).hexdigest(), 16) % self.dim
            vec[bucket] += 1.0
        return vec

    def _embed(self, texts: Sequence[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, self.dim), dtype=np.float32)
        return normalize(np.stack([self._embed_one(t) for t in texts]))

    def embed_passages(self, texts: Sequence[str]) -> np.ndarray:
        return self._embed(list(texts))

    def embed_queries(self, texts: Sequence[str]) -> np.ndarray:
        return self._embed(list(texts))


def make_embedder(name: str = "vllm", **kwargs) -> Embedder:
    """Factory: 'vllm' (default, production) or 'hashing' (offline dev/test)."""
    name = name.lower()
    if name == "vllm":
        return VLLMEmbedder(**kwargs)
    if name == "hashing":
        return HashingEmbedder(**kwargs)
    raise ValueError(f"unknown embedder: {name!r} (expected 'vllm' or 'hashing')")
