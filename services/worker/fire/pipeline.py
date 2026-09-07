"""Orchestrate AURA Incendios pipeline phases."""
from __future__ import annotations

from typing import Any, Callable

PhaseFn = Callable[..., dict[str, Any]]

PHASES: dict[str, str] = {
    "f1": "worker.fire.phases.f01_purge",
    "f2": "worker.fire.phases.f02_aircraft",
    "f3": "worker.fire.phases.f03_corpus",
    "f4": "worker.fire.phases.f04_reclassify",
    "f5": "worker.fire.phases.f05_sicoes_backfill",
    "f6": "worker.fire.phases.f06_budget_cycles",
    "f7": "worker.fire.phases.f07_declarations",
    "f8": "worker.fire.phases.f08_firms",
    "f9": "worker.fire.phases.f09_events",
    "f10": "worker.fire.phases.f10_capability",
    "f11": "worker.fire.phases.f11_territorial",
    "f12": "worker.fire.phases.f12_links",
    "f13": "worker.fire.phases.f13_alerts",
}


def _load(name: str) -> PhaseFn:
    import importlib

    mod_path = PHASES[name]
    mod = importlib.import_module(mod_path)
    return getattr(mod, "run")


def run_phase(name: str, **kwargs: Any) -> dict[str, Any]:
    key = name.lower().strip()
    if key not in PHASES:
        raise ValueError(f"unknown phase {name!r}; expected one of {sorted(PHASES)}")
    return _load(key)(**kwargs)


def run_all(**kwargs: Any) -> dict[str, Any]:
    results = {}
    for name in sorted(PHASES, key=lambda x: int(x[1:]) if x[1:].isdigit() else 99):
        results[name] = run_phase(name, **kwargs)
    return {"status": "ok", "phases": results}
