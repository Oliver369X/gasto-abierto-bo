"""Staging seed profile registration."""
from __future__ import annotations

from worker.gasto.seed_profiles import PROFILES


def test_staging_profile_registered():
    assert "staging" in PROFILES
    assert PROFILES["staging"].endswith("staging")
