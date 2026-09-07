"""B7 — fuzzy merge candidates (score>=90); never auto-merge."""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from common.fuzzy import best_match, canonicalize_name
from schema.models import MergeCandidate, Supplier, SupplierMaster


def find_candidates(
    session: Session,
    *,
    left_type: str = "supplier_master",
    score_cutoff: int = 90,
    limit: int = 500,
) -> dict[str, Any]:
    """Write MergeCandidate rows for near-duplicate masters/suppliers without merging."""
    created = 0
    if left_type == "supplier_master":
        masters = list(session.scalars(select(SupplierMaster).limit(limit * 2)).all())
        names = {m.id: m.canonical_name or "" for m in masters}
        name_list = list(names.values())
        id_by_name = {canonicalize_name(n): i for i, n in names.items()}
        seen_pairs: set[tuple[int, int]] = set()
        for mid, name in names.items():
            match = best_match(name, [n for n in name_list if n != name], score_cutoff=score_cutoff)
            if not match:
                continue
            other_name, score = match
            other_id = id_by_name.get(canonicalize_name(other_name))
            if not other_id or other_id == mid:
                continue
            left_id, right_id = sorted((mid, other_id))
            pair = (left_id, right_id)
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)
            if float(score) < score_cutoff:
                continue
            existing = session.scalars(
                select(MergeCandidate).where(
                    MergeCandidate.left_type == left_type,
                    MergeCandidate.left_id == left_id,
                    MergeCandidate.right_id == right_id,
                )
            ).first()
            if existing:
                continue
            session.add(
                MergeCandidate(
                    left_type=left_type,
                    left_id=left_id,
                    right_id=right_id,
                    score=Decimal(str(round(float(score), 2))),
                    status="pending",
                )
            )
            created += 1
            if created >= limit:
                break
    elif left_type == "supplier":
        suppliers = list(session.scalars(select(Supplier).limit(limit * 2)).all())
        names = {s.id: s.name for s in suppliers}
        name_list = list(names.values())
        id_by_name = {canonicalize_name(n): i for i, n in names.items()}
        seen_pairs: set[tuple[int, int]] = set()
        for sid, name in names.items():
            match = best_match(name, [n for n in name_list if n != name], score_cutoff=score_cutoff)
            if not match:
                continue
            other_name, score = match
            other_id = id_by_name.get(canonicalize_name(other_name))
            if not other_id or other_id == sid or float(score) < score_cutoff:
                continue
            left_id, right_id = sorted((sid, other_id))
            if (left_id, right_id) in seen_pairs:
                continue
            seen_pairs.add((left_id, right_id))
            existing = session.scalars(
                select(MergeCandidate).where(
                    MergeCandidate.left_type == left_type,
                    MergeCandidate.left_id == left_id,
                    MergeCandidate.right_id == right_id,
                )
            ).first()
            if existing:
                continue
            session.add(
                MergeCandidate(
                    left_type=left_type,
                    left_id=left_id,
                    right_id=right_id,
                    score=Decimal(str(round(float(score), 2))),
                    status="pending",
                )
            )
            created += 1
            if created >= limit:
                break
    session.flush()
    return {"ok": True, "created": created, "left_type": left_type, "score_cutoff": score_cutoff}
