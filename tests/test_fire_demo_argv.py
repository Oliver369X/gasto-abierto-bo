"""fire_demo must not leak parent CLI argv (publish / gasto seed)."""
from __future__ import annotations

import inspect
import sys
from unittest.mock import patch

from worker.gasto.seed_profiles import run_seed_cli


def test_fire_demo_main_accepts_force_kwarg():
    from worker.gasto.seeds.fire_demo import main

    sig = inspect.signature(main)
    assert "force" in sig.parameters


def test_seed_profiles_passes_force_without_argv_mutation():
    calls: list[dict] = []

    def fake_main(force: bool = False) -> None:
        calls.append({"force": force})
        assert sys.argv[1:] != ["seed", "--profile", "fire_demo", "--force"]

    with patch("worker.gasto.seed_profiles._load_main", return_value=fake_main):
        with patch("worker.gasto.seeds._helpers.run_with_timeout", side_effect=lambda fn, **_: fn()):
            run_seed_cli("fire_demo", extra_argv=["--force"])
    assert calls == [{"force": True}]


def test_seed_profiles_no_force_flag():
    calls: list[dict] = []

    def fake_main(force: bool = False) -> None:
        calls.append({"force": force})

    saved = list(sys.argv)
    sys.argv = ["gasto", "seed", "--profile", "fire_demo"]
    try:
        with patch("worker.gasto.seed_profiles._load_main", return_value=fake_main):
            with patch("worker.gasto.seeds._helpers.run_with_timeout", side_effect=lambda fn, **_: fn()):
                run_seed_cli("fire_demo")
    finally:
        sys.argv = saved
    assert calls == [{"force": False}]
