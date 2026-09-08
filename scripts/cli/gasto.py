"""Gasto domain CLI subcommands."""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def register(parser: argparse.ArgumentParser) -> None:
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_ingest = sub.add_parser("ingest", help="Ingestar fuente (sync o enqueue)")
    p_ingest.add_argument("--source", choices=_SOURCES)
    p_ingest.add_argument("--all", action="store_true")
    p_ingest.add_argument("--sync", action="store_true")
    p_ingest.add_argument("--enqueue", action="store_true")
    p_ingest.add_argument("--live", action="store_true")
    p_ingest.set_defaults(handler=_cmd_ingest)

    p_seed = sub.add_parser("seed", help="Seed por profile")
    p_seed.add_argument(
        "--profile",
        required=True,
        choices=["demo", "history", "deep", "cross", "real", "publish", "fire_demo"],
    )
    p_seed.add_argument(
        "--force",
        action="store_true",
        help="Re-seed destructive profiles (fire_demo) even if data exists",
    )
    p_seed.set_defaults(handler=_cmd_seed)

    p_harden = sub.add_parser("harden", help="Backfill masters/claims/findings")
    p_harden.set_defaults(handler=_cmd_harden)

    p_verify = sub.add_parser("verify", help="Smoke DoD master plan")
    p_verify.set_defaults(handler=_cmd_verify)

    p_fetch = sub.add_parser("fetch-open-data", help="Descargar datasets open-data (datos.gob.bo/OCP)")
    p_fetch.add_argument("--force", action="store_true")
    p_fetch.add_argument("--list-only", action="store_true")
    p_fetch.set_defaults(handler=_cmd_fetch)

    p_pa = sub.add_parser(
        "fetch-presupuesto",
        help="Descargar CSV/Parquet oficiales de Presupuesto Abierto",
    )
    p_pa.add_argument("--force", action="store_true")
    p_pa.add_argument("--list-only", action="store_true")
    p_pa.set_defaults(handler=_cmd_fetch_presupuesto)

    p_enrich = sub.add_parser("enrich-sicoes", help="Cola enrich SICOES por CUCE")
    p_enrich.add_argument("--limit", type=int, default=100)
    p_enrich.add_argument("--year-from", type=int, default=2024)
    p_enrich.add_argument("--dry-run", action="store_true")
    p_enrich.set_defaults(handler=_cmd_enrich)

    p_stats = sub.add_parser("refresh-stats", help="Refrescar stats_snapshot")
    p_stats.set_defaults(handler=_cmd_refresh_stats)

    p_raw = sub.add_parser("raw-backfill", help="Backfill RAW MinIO sample")
    p_raw.add_argument("--limit", type=int, default=50)
    p_raw.set_defaults(handler=_cmd_raw_backfill)


_SOURCES = [
    "agetic",
    "sicoes",
    "presupuesto_abierto",
    "cge",
    "gad_scz",
    "gam_scz",
]


def _cmd_ingest(args: argparse.Namespace) -> int:
    from worker.gasto.ingest_cli import enqueue, sync_ingest

    if not args.source and not args.all:
        print("Provide --source or --all", file=sys.stderr)
        return 2
    if args.enqueue:
        asyncio.run(enqueue(args.source, args.all))
        return 0
    if not args.sync:
        print("Use --sync or --enqueue", file=sys.stderr)
        return 2
    live = args.live or os.getenv("LIVE_SCRAPE") == "1"
    targets = _SOURCES if args.all else [args.source]
    for sid in targets:
        print(sync_ingest(sid, live=live))
    return 0


def _cmd_seed(args: argparse.Namespace) -> int:
    from worker.gasto.seed_profiles import run_seed_cli

    extra = ["--force"] if getattr(args, "force", False) else []
    result = run_seed_cli(args.profile, extra_argv=extra)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0 if result.get("ok", True) else 1


def _cmd_harden(args: argparse.Namespace) -> int:
    # Prefer worker module; fall back to legacy script path during transition
    try:
        from worker.gasto.harden import main as harden_main

        harden_main()
        return 0
    except ImportError:
        from scripts.harden_master_plan import main as harden_main

        harden_main()
        return 0


def _cmd_verify(args: argparse.Namespace) -> int:
    try:
        from worker.gasto.verify import main as verify_main

        return int(verify_main())
    except ImportError:
        from scripts.verify_master_plan import main as verify_main

        return int(verify_main())


def _cmd_fetch(args: argparse.Namespace) -> int:
    from common.fetch_open_data import fetch_packages, list_urls

    if args.list_only:
        for u in list_urls():
            print(u)
        return 0
    dest = ROOT / "tests" / "fixtures" / "real"
    paths = fetch_packages(dest, force=args.force)
    print(json.dumps({"wrote": [str(p) for p in paths]}, indent=2))
    return 0


def _cmd_fetch_presupuesto(args: argparse.Namespace) -> int:
    from common.fetch_presupuesto_abierto import fetch_presupuesto, list_download_urls

    if args.list_only:
        urls = list_download_urls(discover=True)
        for u in urls:
            print(u)
        if not urls:
            print("No URLs — configure PRESUPUESTO_ABIERTO_DOWNLOAD_URLS", file=sys.stderr)
            return 1
        return 0
    dest = ROOT / "tests" / "fixtures" / "real" / "presupuesto_abierto"
    live = os.getenv("LIVE_SCRAPE") == "1"
    paths = fetch_presupuesto(dest, force=args.force, live=live)
    print(json.dumps({"wrote": [str(p) for p in paths]}, indent=2, ensure_ascii=False))
    return 0


def _cmd_enrich(args: argparse.Namespace) -> int:
    from worker.gasto.enrich_queue import run_cli

    result = run_cli(
        limit=args.limit,
        year_from=args.year_from,
        dry_run=args.dry_run,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    if result.get("blocked") == "no_proxy" and not args.dry_run:
        return 0  # soft skip, not hard fail
    return 0 if result.get("ok", True) else 1


def _cmd_refresh_stats(args: argparse.Namespace) -> int:
    from worker.gasto.stats_snapshot import refresh_stats

    print(json.dumps(refresh_stats(), indent=2, default=str))
    return 0


def _cmd_raw_backfill(args: argparse.Namespace) -> int:
    from worker.gasto.raw_backfill import run_backfill

    print(json.dumps(run_backfill(limit=args.limit), indent=2, default=str))
    return 0
