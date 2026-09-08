"""Presupuesto corpus seed profile registration."""
from __future__ import annotations

from worker.gasto.seed_profiles import PROFILES


def test_presupuesto_corpus_profile_registered():
    assert "presupuesto_corpus" in PROFILES
    assert PROFILES["presupuesto_corpus"].endswith("presupuesto_corpus")
