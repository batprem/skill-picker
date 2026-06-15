"""Selection service: ties the pool, embedder, and index together.

Enforces the two constitution guardrails at the orchestration layer:
- select() returns metadata + scores only; full text comes from load() (Principle II)
- all vectors share one embedding signature; stale/mismatched vectors are re-embedded
  before serving (Principle IV)
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from .embedding import Embedder, passage_text
from .index import Index
from .models import Skill, SelectionQuery, SelectionResult
from .pool import SkillPool, VectorCache


def _source_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


class SelectionService:
    def __init__(self, pool: SkillPool, embedder: Embedder, cache: VectorCache | None = None):
        self.pool = pool
        self.embedder = embedder
        self.cache = cache if cache is not None else VectorCache(pool.dir)
        self.index = Index()

    @property
    def embedding_signature(self) -> str:
        return self.embedder.signature

    def pool_size(self) -> int:
        return len(self.pool.list_metadata())

    def _sync(self) -> None:
        """Make the cache + index consistent with the current pool.

        Embeds any skill whose cached vector is missing, stale, or signature-mismatched;
        drops cache entries for removed skills. Keeps selection consistent with the pool
        within the next cycle (FR-011, SC-004).
        """
        metadata = self.pool.list_metadata()
        entries: list[tuple] = []
        to_embed: list[tuple[str, str, str, str]] = []  # (id, name, passage, source_hash)
        changed = False

        for m in metadata:
            ptext = passage_text(m.name, m.match_text)
            shash = _source_hash(ptext)
            vec = self.cache.get(m.id, shash, self.embedder.signature)
            if vec is None:
                to_embed.append((m.id, m.name, ptext, shash))
            else:
                entries.append((m.id, m.name, vec))

        if to_embed:
            vectors = self.embedder.embed_passages([t[2] for t in to_embed])
            for (sid, name, _ptext, shash), vec in zip(to_embed, vectors):
                self.cache.put(sid, vec, shash, self.embedder.signature)
                entries.append((sid, name, vec))
            changed = True

        live_ids = {m.id for m in metadata}
        for stale_id in [cid for cid in self.cache.ids() if cid not in live_ids]:
            self.cache.delete(stale_id)
            changed = True

        if changed:
            self.cache.save()

        self.index.build(entries)

    def select(self, query: str, k: int = 5, threshold: float = 0.0) -> SelectionResult:
        q = SelectionQuery(query=query, k=k, threshold=threshold)
        self._sync()
        if len(self.index) == 0:
            return SelectionResult(query=q.query, candidates=[])
        qvec = self.embedder.embed_queries([q.query])[0]
        candidates = self.index.select(qvec, q.k, q.threshold)
        return SelectionResult(query=q.query, candidates=candidates)

    def load(self, skill_id: str) -> Skill:
        """Return one skill's full record — the only path that yields full_description."""
        return self.pool.get(skill_id)

    def reindex(self) -> int:
        """Force re-embed of stale/mismatched skills and rebuild the index.

        Returns the resulting pool size.
        """
        self._sync()
        return len(self.index)


def build_service(
    pool_dir: str | Path = "data/skills",
    embedder_name: str = "vllm",
    **embedder_kwargs,
) -> SelectionService:
    """Convenience constructor used by the CLI and API."""
    from .embedding import make_embedder

    pool = SkillPool(pool_dir)
    embedder = make_embedder(embedder_name, **embedder_kwargs)
    return SelectionService(pool, embedder)
