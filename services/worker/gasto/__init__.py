"""Gasto worker package — seeds, enrich queue, verify, harden helpers."""

__all__ = [
    "PROFILES",
    "enqueue_prioritized",
    "run_batch",
    "run_cli",
    "run_seed_cli",
]


def __getattr__(name: str):
    if name in ("enqueue_prioritized", "run_batch", "run_cli"):
        from worker.gasto.enrich_queue import enqueue_prioritized, run_batch, run_cli

        return {
            "enqueue_prioritized": enqueue_prioritized,
            "run_batch": run_batch,
            "run_cli": run_cli,
        }[name]
    if name in ("PROFILES", "run_seed_cli"):
        from worker.gasto.seed_profiles import PROFILES, run_seed_cli

        return {"PROFILES": PROFILES, "run_seed_cli": run_seed_cli}[name]
    raise AttributeError(name)
