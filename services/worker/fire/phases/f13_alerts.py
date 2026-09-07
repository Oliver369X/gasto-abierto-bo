"""F13: materialize fire-specific alert rules."""
from __future__ import annotations

from worker.alerts_fire import run_fire_alert_rules
from worker.fire.artifacts import write_json
from worker.fire.context import get_session


def run(session=None, *, write_artifact: bool = True) -> dict:
    own = session is None
    session = session or get_session()
    try:
        alerts = run_fire_alert_rules(session)
        session.commit()
        payload = {"status": "ok", "alerts": len(alerts),
                   "rules": sorted({alert.rule_id for alert in alerts})}
        if write_artifact:
            write_json("f13_alerts.json", payload)
        return payload
    except Exception:
        session.rollback()
        raise
    finally:
        if own:
            session.close()
