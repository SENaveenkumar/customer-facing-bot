from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

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
    def __init__(self, knowledge_dir: Path) -> None:
        self._dir = knowledge_dir
        self._chunks: list[KnowledgeChunk] | None = None

    def reload(self) -> None:
        self._chunks = None

    def chunks(self) -> list[KnowledgeChunk]:
        if self._chunks is None:
            self._chunks = self._load_all()
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

        words = set(re.findall(r"[a-z0-9]+", (question or "").lower()))
        words -= {"a", "an", "the", "is", "why", "what", "how", "this", "my", "for", "to"}

        ranked = sorted(
            all_chunks,
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
