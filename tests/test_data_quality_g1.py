"""G1–G10 gates for gasto abierto data quality."""
from __future__ import annotations

from decimal import Decimal

from common.claims import add_claim
from common.data_quality import classify_origin, is_public_row
from common.fire.ledger import amount_for_public_kpi  # noqa: F401 — ensure import path ok


def test_classify_seed_synthetic():
    q = classify_origin(source_id="seed")
    assert q["is_synthetic"] is True
    assert q["source_quality"] == "SYNTHETIC"
    assert is_public_row(type("R", (), q)()) is False


def test_classify_sicoes_mirror_not_official():
    q = classify_origin(source_id="sicoes", source_note="sociedatos/bo-convocatorias")
    assert q["is_synthetic"] is False
    assert q["is_official"] is False
    assert q["data_origin"] == "civic_mirror"
    assert is_public_row(type("R", (), q)()) is True


def test_classify_ocds_official_unverified():
    q = classify_origin(source_id="agetic", source_note="datos.gob.bo ocds")
    assert q["is_official"] is True
    assert q["source_quality"] == "OFFICIAL_UNVERIFIED"


def test_deep_cuce_synthetic():
    q = classify_origin(source_id="sicoes", cuce="GA-DEEP-001")
    assert q["is_synthetic"] is True
    assert q["source_quality"] == "SYNTHETIC"


def test_placeholder_cannot_be_public_official():
    """Gate: no PLACEHOLDER/SYNTHETIC with is_official=true from classifier."""
    for sid, note, cuce in [
        ("seed", None, None),
        ("sicoes", "fixture", None),
        ("agetic", None, "GA-DEEP-99"),
    ]:
        q = classify_origin(source_id=sid, source_note=note, cuce=cuce)
        if q["source_quality"] in ("SYNTHETIC", "PLACEHOLDER"):
            assert q["is_official"] is False


def test_add_claim_creates_conflict(monkeypatch):
    """Unit-level: conflicting values yield open conflict without deleting prior claim."""
    from schema.models import Claim, ClaimConflict, ClaimEvidence, ReconciliationResult

    class FakeSession:
        def __init__(self):
            self.added = []
            self._id = 1
            self.claims = []

        def add(self, obj):
            if getattr(obj, "id", None) is None and hasattr(obj, "id"):
                pass
            self.added.append(obj)
            if isinstance(obj, Claim):
                obj.id = self._id
                self._id += 1
                self.claims.append(obj)
            if isinstance(obj, ClaimConflict):
                obj.id = self._id
                self._id += 1
            if isinstance(obj, ClaimEvidence):
                obj.id = self._id
                self._id += 1
            if isinstance(obj, ReconciliationResult):
                obj.id = self._id
                self._id += 1

        def flush(self):
            return None

        def scalars(self, stmt):
            class R:
                def __init__(self, rows):
                    self._rows = rows

                def all(self):
                    return self._rows

                def first(self):
                    return self._rows[0] if self._rows else None

            # Very naive: return prior claims for same field
            return R([c for c in self.claims if c.field == "amount"][:-1])

    session = FakeSession()
    c1 = add_claim(
        session,
        field="amount",
        entity_type="contract",
        entity_id=1,
        source_id="sicoes",
        value_num=Decimal("100"),
        detect_conflict=True,
    )
    c2 = add_claim(
        session,
        field="amount",
        entity_type="contract",
        entity_id=1,
        source_id="agetic",
        value_num=Decimal("200"),
        detect_conflict=True,
    )
    assert c1.id != c2.id
    conflicts = [x for x in session.added if isinstance(x, ClaimConflict)]
    assert len(conflicts) >= 1
    assert conflicts[-1].status == "open"
    # Both claims retained
    assert len([x for x in session.added if isinstance(x, Claim)]) >= 2
