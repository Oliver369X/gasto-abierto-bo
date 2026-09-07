"""A4 — seed profiles CLI: demo / history / deep / cross / real."""
from __future__ import annotations

import importlib
import sys
from typing import Callable

PROFILES: dict[str, str] = {
    "demo": "worker.gasto.seeds.demo",
    "history": "worker.gasto.seeds.history",
    "deep": "worker.gasto.seeds.deep",
    "cross": "worker.gasto.seeds.cross",
    "real": "worker.gasto.seeds.real",
}


def _load_main(module_name: str) -> Callable[[], None]:
    mod = importlib.import_module(module_name)
    fn = getattr(mod, "main", None)
    if not callable(fn):
        raise RuntimeError(f"{module_name} has no main()")
    return fn


def run_seed_cli(profile: str) -> dict:
    key = (profile or "").strip().lower()
    if key not in PROFILES:
        raise SystemExit(
            f"Unknown profile {profile!r}. Choose one of: {', '.join(sorted(PROFILES))}"
        )
    module_name = PROFILES[key]
    main = _load_main(module_name)
    main()
    return {"ok": True, "profile": key, "module": module_name}


def main(argv: list[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    profile = args[0] if args else "demo"
    print(run_seed_cli(profile))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
