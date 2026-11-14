"""Memory interface for RAG over the knowledge base.

The MVP ships an in-memory keyword-overlap store so it runs without an embeddings
backend. Swap `InMemoryStore` for a pgvector / Bedrock Titan embeddings backend in
production (see ROADMAP) — the interface stays the same.
"""

from abc import ABC, abstractmethod


class MemoryStore(ABC):
    @abstractmethod
    async def add(self, text: str, metadata: dict | None = None) -> None: ...

    @abstractmethod
    async def search(self, query: str, k: int = 4) -> list[dict]: ...


class InMemoryStore(MemoryStore):
    """Token-overlap ranking over an in-process document list."""

    def __init__(self) -> None:
        self._docs: list[dict] = []

    async def add(self, text: str, metadata: dict | None = None) -> None:
        self._docs.append(
            {"text": text, "meta": metadata or {}, "tokens": set(text.lower().split())}
        )

    async def search(self, query: str, k: int = 4) -> list[dict]:
        q = set(query.lower().split())
        scored = []
        for d in self._docs:
            overlap = len(q & d["tokens"])
            if overlap:
                scored.append((overlap, d))
        scored.sort(key=lambda x: -x[0])
        return [{"text": d["text"], "meta": d["meta"], "score": s} for s, d in scored[:k]]
