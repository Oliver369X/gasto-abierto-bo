"""Fire domain CLI — wraps pipeline + verify."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "packages"), str(ROOT / "services"), str(ROOT)]


def register(parser: argparse.ArgumentParser) -> None:
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_phase = sub.add_parser("pipeline", help="Run fire phase(s)")
    p_phase.add_argument("--phase", required=True, help="f1..f13 or all")
    p_phase.add_argument("--no-artifact", action="store_true")
    p_phase.set_defaults(handler=_cmd_pipeline)

    # Alias: `fire --phase f1` via top-level convenience on domain parser
    # Also support: python -m scripts.cli fire run --phase f1
    p_run = sub.add_parser("run", help="Alias of pipeline")
    p_run.add_argument("--phase", required=True)
    p_run.add_argument("--no-artifact", action="store_true")
    p_run.set_defaults(handler=_cmd_pipeline)

    p_verify = sub.add_parser("verify", help="Verify Plan 2 gates")
    p_verify.set_defaults(handler=_cmd_verify)


def _cmd_pipeline(args: argparse.Namespace) -> int:
    from worker.fire.pipeline import PHASES, run_all, run_phase

    kwargs = {"write_artifact": not getattr(args, "no_artifact", False)}
    phase = args.phase.lower().strip()
    if phase == "all":
        result = run_all(**kwargs)
    elif phase in PHASES:
        result = run_phase(phase, **kwargs)
    else:
        key = phase if phase in PHASES else phase.lstrip("0")
        if key.startswith("f0") and key[1:].lstrip("0"):
            key = "f" + str(int(key[1:]))
        if key not in PHASES:
            print(f"unknown phase {args.phase!r}; expected {sorted(PHASES)} or all", file=sys.stderr)
            return 2
        result = run_phase(key, **kwargs)

    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    status = result.get("status") if isinstance(result, dict) else None
    if status in ("error", "failed"):
        return 1
    return 0


def _cmd_verify(args: argparse.Namespace) -> int:
    from worker.fire.verification.plan2 import main as verify_main

    return int(verify_main())
