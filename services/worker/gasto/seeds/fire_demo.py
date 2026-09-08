#!/usr/bin/env python3
"""Offline AURA Incendios demo data (ledger, expedientes, territorios).

  docker compose run --rm --entrypoint python api -m scripts.cli gasto seed --profile fire_demo
  docker compose run --rm --entrypoint python api -m scripts.cli gasto seed --profile fire_demo --force
"""
from __future__ import annotations

from worker.gasto.seeds.fire_demo_impl import main

__all__ = ["main"]
