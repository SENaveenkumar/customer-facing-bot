from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

FORBIDDEN = [
    re.compile(r"\bmutation\b", re.I),
    re.compile(r"\bsubscription\b", re.I),
    re.compile(r"\b__schema\b", re.I),
    re.compile(r"\b__type\b", re.I),
]
OP_NAME = re.compile(r"\b(query|mutation)\s+(\w+)", re.I)


@dataclass(frozen=True)
class PersistedOperation:
    name: str
    document: str
    hash: str
    kind: str  # "read" | "write"


def _normalize(doc: str) -> str:
    return " ".join(doc.split())


def _hash(doc: str) -> str:
    return hashlib.sha256(_normalize(doc).encode()).hexdigest()


def _extract_name(doc: str, filename: str) -> str:
    m = OP_NAME.search(doc)
    if m:
        return m.group(2)
    return filename.replace(".graphql", "")


def _assert_read_only(doc: str) -> None:
    for pat in FORBIDDEN:
        if pat.search(doc):
            raise ValueError(f"Operation rejected: forbidden pattern {pat.pattern}")


class OperationRegistry:
    def __init__(self) -> None:
        self._by_name: dict[str, PersistedOperation] = {}
        self._by_hash: dict[str, PersistedOperation] = {}

    @classmethod
    def load(cls, project_root: Path) -> OperationRegistry:
        reg = cls()
        reg._load_dir(project_root / "operations" / "reads", "read")
        reg._load_dir(project_root / "operations" / "writes", "write")
        return reg

    def _load_dir(self, directory: Path, kind: str) -> None:
        if not directory.is_dir():
            return
        for path in sorted(directory.glob("*.graphql")):
            doc = path.read_text(encoding="utf-8")
            name = _extract_name(doc, path.name)
            op = PersistedOperation(name=name, document=doc, hash=_hash(doc), kind=kind)
            self._by_name[name] = op
            self._by_hash[op.hash] = op

    def get_read(self, name: str) -> PersistedOperation:
        op = self._by_name.get(name)
        if not op:
            allowed = ", ".join(self.list_read_names())
            raise ValueError(f'Unknown read operation "{name}". Allowed: {allowed}')
        if op.kind != "read":
            raise ValueError(f'Operation "{name}" is not a read operation')
        _assert_read_only(op.document)
        return op

    def get_write(self, name: str) -> PersistedOperation:
        op = self._by_name.get(name)
        if not op:
            raise ValueError(f'Unknown write operation "{name}"')
        if op.kind != "write":
            raise ValueError(f'Operation "{name}" is not a write operation')
        return op

    def list_read_names(self) -> list[str]:
        return sorted(n for n, o in self._by_name.items() if o.kind == "read")
