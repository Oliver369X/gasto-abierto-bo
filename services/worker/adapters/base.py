from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any, Protocol


@dataclass
class Cursor:
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class RawItem:
    uri: str
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class StagingRecord:
    record_type: str  # contract | budget | audit | entity | document
    data: dict[str, Any] = field(default_factory=dict)


class SourceAdapter(Protocol):
    source_id: str

    def discover(self, cursor: Cursor) -> list[RawItem]: ...

    def fetch(self, item: RawItem) -> bytes: ...

    def parse(self, raw: bytes) -> list[StagingRecord]: ...
