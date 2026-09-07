from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import sessionmaker

from common.fuzzy import canonicalize_name
from schema.models import AdminLevel, Alert, Base, Contract, Entity, Supplier
from worker.alerts import run_alert_rules


def test_alert_rules_generate_named_alerts():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    now = datetime.now(timezone.utc)
    e = Entity(
        name="GAM Demo",
        canonical_name=canonicalize_name("GAM Demo"),
        level=AdminLevel.municipal,
        source_id="test",
    )
    s = Supplier(
        name="Proveedor Concentrado SRL",
        canonical_name=canonicalize_name("Proveedor Concentrado SRL"),
        source_id="test",
    )
    session.add_all([e, s])
    session.flush()
    for i, amt in enumerate([Decimal("1000000"), Decimal("500000"), Decimal("200000")]):
        session.add(
            Contract(
                cuce=f"T-{i}",
                entity_id=e.id,
                supplier_id=s.id,
                object_description=f"obra {i}",
                modality="Adjudicación Directa",
                amount=amt,
                contract_date=date(2026, 4, 1 + i * 5),
                source_id="test",
                valid_from=now,
                is_current=True,
            )
        )
    session.commit()
    alerts = run_alert_rules(session)
    session.commit()
    assert len(alerts) >= 2
    blob = " ".join(a.title + " " + a.explanation for a in alerts)
    assert "Proveedor Concentrado" in blob
    assert all(a.explanation for a in alerts)
    n = session.scalar(select(func.count()).select_from(Alert))
    assert n >= 2
