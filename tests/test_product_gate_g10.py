"""G10 product checklist — Plan Maestro Gasto Abierto."""

CHECKLIST = [
    ("G1", "Sintéticos separados de totales públicos (?quality=public)"),
    ("G1", "UI no trata ausencia de monto como Bs 0"),
    ("G2", "raw_artifact versionado + claim/claim_evidence"),
    ("G2", "GET /v1/contracts/{id}/claims y /evidence"),
    ("G3", "completeness_* en contract + GET /v1/coverage/sicoes"),
    ("G3", "enrich_sicoes_cuce soft-fail + PROXY_URL"),
    ("G4", "supplier_master + aliases + bridge NIT"),
    ("G5", "public_entity_master + entity_alias + bridge"),
    ("G6", "budget phases (initial/current/payment) sin sumar como independientes"),
    ("G7", "audit_finding estructurado"),
    ("G8", "claim_conflict + reconciliation_result (sin borrar)"),
    ("G9", "alertas solo sobre no-sintéticos + causas legítimas"),
    ("G10", "GET /v1/product-gate con umbrales reales de densidad"),
]


def test_checklist_complete():
    assert len(CHECKLIST) >= 13
    phases = {c[0] for c in CHECKLIST}
    assert phases >= {"G1", "G2", "G3", "G4", "G5", "G6", "G7", "G8", "G9", "G10"}


def test_product_gate_requires_evidence_density():
    assert any("claim" in c[1].lower() or "evidencia" in c[1].lower() for c in CHECKLIST)
    assert any("umbrales reales" in c[1].lower() for c in CHECKLIST)
