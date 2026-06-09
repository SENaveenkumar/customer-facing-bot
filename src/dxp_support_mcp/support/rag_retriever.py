from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dxp_support_mcp.config import AppConfig

_FRONTMATTER = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)", re.DOTALL)
_TAG_LIST = re.compile(r"\[(.*?)\]")


@dataclass(frozen=True)
class KnowledgeChunk:
    id: str
    title: str
    tags: tuple[str, ...]
    related: tuple[str, ...]
    content: str
    category: str
    path: str

    def score(
        self,
        question: str | None,
        context_tags: set[str],
        question_words: set[str],
    ) -> float:
        score = 0.0
        tag_set = {t.lower() for t in self.tags}

        overlap = tag_set & context_tags
        score += len(overlap) * 3.0

        if question:
            q = question.lower()
            if self.id.lower() in q or self.title.lower() in q:
                score += 8.0
            for tag in tag_set:
                if tag in q:
                    score += 2.0

        title_words = set(re.findall(r"[a-z0-9]+", self.title.lower()))
        content_words = set(re.findall(r"[a-z0-9]+", self.content.lower()[:800]))
        score += len(question_words & title_words) * 2.5
        score += len(question_words & content_words) * 0.5

        if "contract-status-" in self.id and any(
            t.startswith("contract-status-") for t in context_tags
        ):
            status_slug = self.id.replace("contract-status-", "")
            if f"contract-status-{status_slug}" in context_tags:
                score += 10.0

        if self.category == "errors" and "error" in context_tags:
            score += 2.0
        if self.category == "faq" and not question:
            score -= 1.0

        return score


class KnowledgeIndex:
    def __init__(self, config: AppConfig) -> None:
        self._config = config
        self._dir = config.knowledge_dir
        self._db_dir = config.rag_vector_db_dir
        self._manifest_path = self._db_dir / "knowledge_manifest.json"
        self._chunks: list[KnowledgeChunk] | None = None
        self._chunk_by_id: dict[str, KnowledgeChunk] = {}
        self._vector = _VectorStore(config.rag_embedding_model, self._db_dir)

    def reload(self) -> None:
        self._chunks = None

    def chunks(self) -> list[KnowledgeChunk]:
        if self._chunks is None:
            self._chunks = self._load_all()
            self._chunk_by_id = {chunk.id: chunk for chunk in self._chunks}
        return self._chunks

    def retrieve(
        self,
        question: str | None,
        context_tags: set[str],
        top_k: int = 5,
    ) -> list[KnowledgeChunk]:
        all_chunks = self.chunks()
        if not all_chunks:
            return []

        self._ensure_vector_index()

        words = set(re.findall(r"[a-z0-9]+", (question or "").lower()))
        words -= {
            "a",
            "an",
            "the",
            "is",
            "why",
            "what",
            "how",
            "this",
            "my",
            "for",
            "to",
        }

        candidate_chunks = all_chunks
        if question and self._vector.enabled:
            vector_ids = self._vector.search(
                question,
                top_n=max(top_k, self._config.rag_vector_top_n),
            )
            if vector_ids:
                candidate_chunks = [
                    self._chunk_by_id[cid]
                    for cid in vector_ids
                    if cid in self._chunk_by_id
                ]

        ranked = sorted(
            candidate_chunks,
            key=lambda c: c.score(question, context_tags, words),
            reverse=True,
        )
        return ranked[:top_k]

    def _load_all(self) -> list[KnowledgeChunk]:
        if not self._dir.is_dir():
            return []

        loaded: list[KnowledgeChunk] = []
        for path in sorted(self._dir.rglob("*.md")):
            chunk = _parse_chunk(path)
            if chunk:
                loaded.append(chunk)
        return loaded

    def _ensure_vector_index(self) -> None:
        chunks = self.chunks()
        if not chunks or not self._vector.enabled:
            return

        signature = _build_knowledge_signature(self._dir)
        cached_signature = self._read_manifest_signature()
        if cached_signature == signature and self._vector.collection_exists("knowledge"):
            return

        self._vector.rebuild("knowledge", chunks)
        self._write_manifest_signature(signature)

    def _read_manifest_signature(self) -> str | None:
        if not self._manifest_path.exists():
            return None
        try:
            body = json.loads(self._manifest_path.read_text(encoding="utf-8"))
            return str(body.get("signature") or "")
        except Exception:
            return None

    def _write_manifest_signature(self, signature: str) -> None:
        self._db_dir.mkdir(parents=True, exist_ok=True)
        self._manifest_path.write_text(
            json.dumps({"signature": signature}, indent=2),
            encoding="utf-8",
        )


class _VectorStore:
    def __init__(self, embedding_model: str, db_dir: Path) -> None:
        self.enabled = False
        self._client = None
        self._embedding_fn = None
        self._embedding_model = embedding_model
        self._db_dir = db_dir
        self._init()

    def _init(self) -> None:
        try:
            import chromadb
            from chromadb.utils.embedding_functions import (
                SentenceTransformerEmbeddingFunction,
            )

            self._db_dir.mkdir(parents=True, exist_ok=True)
            self._client = chromadb.PersistentClient(path=str(self._db_dir))
            self._embedding_fn = SentenceTransformerEmbeddingFunction(
                model_name=self._embedding_model
            )
            self.enabled = True
        except Exception:
            self.enabled = False

    def collection_exists(self, collection_name: str) -> bool:
        if not self.enabled or self._client is None:
            return False
        return any(c.name == collection_name for c in self._client.list_collections())

    def rebuild(self, collection_name: str, chunks: list[KnowledgeChunk]) -> None:
        if not self.enabled or self._client is None or self._embedding_fn is None:
            return
        if self.collection_exists(collection_name):
            self._client.delete_collection(collection_name)
        collection = self._client.get_or_create_collection(
            collection_name,
            embedding_function=self._embedding_fn,
        )
        collection.add(
            ids=[chunk.id for chunk in chunks],
            documents=[f"{chunk.title}\n\n{chunk.content}" for chunk in chunks],
            metadatas=[
                {
                    "title": chunk.title,
                    "category": chunk.category,
                    "path": chunk.path,
                    "tags": ",".join(chunk.tags),
                }
                for chunk in chunks
            ],
        )

    def search(self, query: str, top_n: int) -> list[str]:
        if not self.enabled or self._client is None or self._embedding_fn is None:
            return []
        collection = self._client.get_or_create_collection(
            "knowledge",
            embedding_function=self._embedding_fn,
        )
        result = collection.query(query_texts=[query], n_results=max(1, top_n))
        ids: list[str] = []
        for candidate_ids in result.get("ids") or []:
            for chunk_id in candidate_ids or []:
                if chunk_id:
                    ids.append(str(chunk_id))
        return ids


def _build_knowledge_signature(knowledge_dir: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(knowledge_dir.rglob("*.md")):
        stat = path.stat()
        digest.update(str(path.relative_to(knowledge_dir)).encode("utf-8"))
        digest.update(str(int(stat.st_mtime)).encode("utf-8"))
        digest.update(str(stat.st_size).encode("utf-8"))
    return digest.hexdigest()


def _parse_chunk(path: Path) -> KnowledgeChunk | None:
    text = path.read_text(encoding="utf-8")
    match = _FRONTMATTER.match(text)
    if not match:
        return None

    meta_raw, body = match.group(1), match.group(2).strip()
    meta = _parse_frontmatter(meta_raw)
    chunk_id = meta.get("id") or path.stem
    title = meta.get("title") or chunk_id
    tags = _parse_tag_list(meta.get("tags", ""))
    related = _parse_tag_list(meta.get("related", ""))
    category = path.parent.name

    return KnowledgeChunk(
        id=chunk_id,
        title=title,
        tags=tags,
        related=related,
        content=body,
        category=category,
        path=str(path),
    )


def _parse_frontmatter(raw: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in raw.splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        out[key.strip()] = value.strip()
    return out


def _parse_tag_list(raw: str) -> tuple[str, ...]:
    if not raw:
        return ()
    match = _TAG_LIST.search(raw)
    if not match:
        return (raw.strip(),) if raw.strip() else ()
    inner = match.group(1)
    parts = [p.strip().strip("'\"") for p in inner.split(",") if p.strip()]
    return tuple(p.lower() for p in parts)


def context_tags_from_contract(context: dict[str, Any]) -> set[str]:
    tags: set[str] = {"contract"}

    status = context.get("status")
    if status:
        tags.add(status.lower())
        tags.add(f"contract-status-{status.lower()}")

    error_reason = context.get("errorReason")
    if error_reason:
        tags.add("error")
        tags.add("reason")
        slug = re.sub(r"[^a-z0-9]+", "-", str(error_reason).lower()).strip("-")
        tags.add(slug)
        tags.add(f"contract-reason-{slug}")

    status_change_reason = context.get("statusChangeReason")
    if status_change_reason:
        tags.add("reason")
        slug = re.sub(r"[^a-z0-9]+", "-", str(status_change_reason).lower()).strip("-")
        tags.add(slug)
        tags.add(f"contract-reason-{slug}")

    contract_type = context.get("type")
    if contract_type:
        tags.add(str(contract_type).lower())
        if str(contract_type).upper() == "TRIAL":
            tags.add("trial")

    approval_status = context.get("approvalStatus")
    if approval_status:
        tags.add("approval")
        tags.add(str(approval_status).lower())
        tags.add(f"approval-status-{str(approval_status).lower()}")

    renewal_status = context.get("renewalStatus")
    if renewal_status:
        tags.add("renewal")
        slug = re.sub(r"[^a-z0-9]+", "-", str(renewal_status).lower()).strip("-")
        tags.add(f"renewal-status-{slug}")

    for blocker in context.get("blockers") or []:
        tags.add(str(blocker).lower())

    if "trial_contract" in (context.get("blockers") or []):
        tags.add("renewal")
        tags.add("business-rules")
    if "amendment" in str(context.get("blockers")):
        tags.add("amendment")
        tags.add("business-rules")
    if context.get("approvalStatus") == "PENDING":
        tags.add("discount")
        tags.add("pricing")

    return tags
