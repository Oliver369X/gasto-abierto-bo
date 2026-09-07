"""G2–G8: evidence/claims, masters, audit findings, reconciliation."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0009_evidence_masters"
down_revision = "0008_data_quality"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "source_registry",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(64), nullable=False, unique=True),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("kind", sa.String(64), nullable=False, server_default="portal"),
        sa.Column("base_url", sa.String(2048), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "raw_artifact",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("url_original", sa.String(2048), nullable=False),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("mime", sa.String(128), nullable=True),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("etag", sa.String(256), nullable=True),
        sa.Column("last_modified", sa.String(128), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column("crawler_version", sa.String(64), nullable=True),
        sa.Column("minio_key", sa.String(512), nullable=True),
        sa.Column("source_id", sa.String(64), nullable=False, server_default="unknown"),
        sa.Column("ingestion_run_id", sa.Integer(), sa.ForeignKey("ingestion_run.id"), nullable=True),
        sa.Column("meta", sa.JSON(), nullable=True),
    )
    op.create_index("ix_raw_artifact_sha256", "raw_artifact", ["sha256"])

    op.add_column(
        "document",
        sa.Column("raw_artifact_id", sa.Integer(), sa.ForeignKey("raw_artifact.id"), nullable=True),
    )

    op.create_table(
        "document_page",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("document.id"), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("text_extracted", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_document_page_document_id", "document_page", ["document_id"])

    op.create_table(
        "extraction_run",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("method", sa.String(64), nullable=False),
        sa.Column("version", sa.String(32), nullable=False, server_default="1"),
        sa.Column("raw_artifact_id", sa.Integer(), sa.ForeignKey("raw_artifact.id"), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("meta", sa.JSON(), nullable=True),
    )

    op.create_table(
        "claim",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("field", sa.String(64), nullable=False),
        sa.Column("value_text", sa.Text(), nullable=True),
        sa.Column("value_num", sa.Numeric(18, 2), nullable=True),
        sa.Column("entity_type", sa.String(64), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=True),
        sa.Column("source_id", sa.String(64), nullable=False),
        sa.Column("extraction_run_id", sa.Integer(), sa.ForeignKey("extraction_run.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_claim_entity", "claim", ["entity_type", "entity_id", "field"])

    op.create_table(
        "claim_evidence",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("claim_id", sa.Integer(), sa.ForeignKey("claim.id"), nullable=False),
        sa.Column("raw_artifact_id", sa.Integer(), sa.ForeignKey("raw_artifact.id"), nullable=True),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("document.id"), nullable=True),
        sa.Column("document_page_id", sa.Integer(), sa.ForeignKey("document_page.id"), nullable=True),
        sa.Column("quote", sa.Text(), nullable=True),
        sa.Column("page", sa.Integer(), nullable=True),
        sa.Column("url", sa.String(2048), nullable=True),
        sa.Column("sha256", sa.String(64), nullable=True),
        sa.Column("evidence", sa.JSON(), nullable=True),
    )
    op.create_index("ix_claim_evidence_claim_id", "claim_evidence", ["claim_id"])

    op.create_table(
        "claim_conflict",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("entity_type", sa.String(64), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("field", sa.String(64), nullable=False),
        sa.Column("claim_ids", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="open"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "reconciliation_result",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("claim_conflict_id", sa.Integer(), sa.ForeignKey("claim_conflict.id"), nullable=False),
        sa.Column("canonical_value", sa.Text(), nullable=True),
        sa.Column("conflict_status", sa.String(32), nullable=False, server_default="unresolved"),
        sa.Column("resolution_method", sa.String(64), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "supplier_master",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("canonical_name", sa.String(512), nullable=False),
        sa.Column("nit", sa.String(32), nullable=True, unique=True),
        sa.Column("legal_form", sa.String(128), nullable=True),
        sa.Column("address", sa.String(512), nullable=True),
        sa.Column("department", sa.String(128), nullable=True),
        sa.Column("municipality", sa.String(128), nullable=True),
        sa.Column("first_seen", sa.Date(), nullable=True),
        sa.Column("last_seen", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_supplier_master_canonical_name", "supplier_master", ["canonical_name"])
    op.create_index("ix_supplier_master_nit", "supplier_master", ["nit"])

    op.create_table(
        "supplier_alias",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("supplier_master_id", sa.Integer(), sa.ForeignKey("supplier_master.id"), nullable=False),
        sa.Column("alias", sa.String(512), nullable=False),
        sa.Column("source_id", sa.String(64), nullable=True),
    )
    op.create_index("ix_supplier_alias_alias", "supplier_alias", ["alias"])

    op.create_table(
        "supplier_identifier",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("supplier_master_id", sa.Integer(), sa.ForeignKey("supplier_master.id"), nullable=False),
        sa.Column("id_type", sa.String(32), nullable=False, server_default="nit"),
        sa.Column("id_value", sa.String(64), nullable=False),
        sa.Column("source_id", sa.String(64), nullable=True),
    )
    op.create_index("ix_supplier_identifier_id_value", "supplier_identifier", ["id_value"])

    op.create_table(
        "supplier_relation",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("from_master_id", sa.Integer(), sa.ForeignKey("supplier_master.id"), nullable=False),
        sa.Column("to_master_id", sa.Integer(), sa.ForeignKey("supplier_master.id"), nullable=False),
        sa.Column("relation_type", sa.String(64), nullable=False, server_default="related"),
    )
    op.create_table(
        "supplier_source",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("supplier_master_id", sa.Integer(), sa.ForeignKey("supplier_master.id"), nullable=False),
        sa.Column("source_id", sa.String(64), nullable=False),
        sa.Column("external_ref", sa.String(256), nullable=True),
    )

    op.create_table(
        "public_entity_master",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("canonical_name", sa.String(512), nullable=False),
        sa.Column("level", sa.String(64), nullable=True),
        sa.Column("institution_type", sa.String(128), nullable=True),
        sa.Column("department", sa.String(128), nullable=True),
        sa.Column("municipality", sa.String(128), nullable=True),
        sa.Column("parent_id", sa.Integer(), sa.ForeignKey("public_entity_master.id"), nullable=True),
        sa.Column("predecessor_id", sa.Integer(), sa.ForeignKey("public_entity_master.id"), nullable=True),
        sa.Column("successor_id", sa.Integer(), sa.ForeignKey("public_entity_master.id"), nullable=True),
        sa.Column("valid_from", sa.Date(), nullable=True),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_public_entity_master_canonical_name", "public_entity_master", ["canonical_name"])

    op.create_table(
        "entity_alias",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("entity_master_id", sa.Integer(), sa.ForeignKey("public_entity_master.id"), nullable=False),
        sa.Column("alias", sa.String(512), nullable=False),
        sa.Column("source_id", sa.String(64), nullable=True),
    )
    op.create_index("ix_entity_alias_alias", "entity_alias", ["alias"])

    op.create_table(
        "audit_finding",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("audit_report_id", sa.Integer(), sa.ForeignKey("audit_report.id"), nullable=False),
        sa.Column("title", sa.String(1024), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("severity", sa.String(32), nullable=True),
        sa.Column("entity_id", sa.Integer(), sa.ForeignKey("entity.id"), nullable=True),
        sa.Column("contract_id", sa.Integer(), sa.ForeignKey("contract.id"), nullable=True),
        sa.Column("supplier_id", sa.Integer(), sa.ForeignKey("supplier.id"), nullable=True),
        sa.Column("amount", sa.Numeric(18, 2), nullable=True),
        sa.Column("evidence", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_audit_finding_audit_report_id", "audit_finding", ["audit_report_id"])

    op.create_table(
        "audit_recommendation",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("audit_finding_id", sa.Integer(), sa.ForeignKey("audit_finding.id"), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("status", sa.String(32), nullable=True),
    )
    op.create_table(
        "audit_amount",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("audit_finding_id", sa.Integer(), sa.ForeignKey("audit_finding.id"), nullable=False),
        sa.Column("amount_type", sa.String(64), nullable=False, server_default="observed"),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("currency", sa.String(8), server_default="BOB"),
    )

    # Seed source registry
    op.execute(
        """
        INSERT INTO source_registry (code, name, kind, base_url) VALUES
        ('sicoes', 'SICOES', 'portal', 'https://www.sicoes.gob.bo'),
        ('agetic', 'AGETIC / datos.gob.bo', 'ocds', 'https://datos.gob.bo'),
        ('cge', 'Contraloría General del Estado', 'audit', 'https://www.contraloria.gob.bo'),
        ('presupuesto_abierto', 'Presupuesto Abierto', 'budget', NULL),
        ('seed', 'Fixtures / seed', 'fixture', NULL)
        ON CONFLICT (code) DO NOTHING
        """
    )

    # Bridge suppliers with NIT → supplier_master
    op.execute(
        """
        INSERT INTO supplier_master (canonical_name, nit, first_seen, last_seen)
        SELECT DISTINCT ON (nit) canonical_name, nit, CURRENT_DATE, CURRENT_DATE
        FROM supplier
        WHERE nit IS NOT NULL AND nit <> ''
        ORDER BY nit, id
        ON CONFLICT (nit) DO NOTHING
        """
    )
    op.execute(
        """
        UPDATE supplier s SET supplier_master_id = m.id
        FROM supplier_master m
        WHERE s.nit IS NOT NULL AND s.nit = m.nit
        """
    )
    op.execute(
        """
        INSERT INTO supplier_alias (supplier_master_id, alias, source_id)
        SELECT m.id, s.name, s.source_id
        FROM supplier s
        JOIN supplier_master m ON s.supplier_master_id = m.id
        WHERE s.name IS NOT NULL
        """
    )

    # Bridge entities → public_entity_master by canonical_name
    op.execute(
        """
        INSERT INTO public_entity_master (canonical_name, level, department)
        SELECT DISTINCT ON (canonical_name)
          canonical_name,
          level,
          department
        FROM entity
        ORDER BY canonical_name, id
        """
    )
    op.execute(
        """
        UPDATE entity e SET entity_master_id = m.id
        FROM public_entity_master m
        WHERE e.canonical_name = m.canonical_name
        """
    )
    op.execute(
        """
        INSERT INTO entity_alias (entity_master_id, alias, source_id)
        SELECT m.id, e.name, e.source_id
        FROM entity e
        JOIN public_entity_master m ON e.entity_master_id = m.id
        WHERE e.name IS NOT NULL
        """
    )


def downgrade() -> None:
    for table in (
        "audit_amount",
        "audit_recommendation",
        "audit_finding",
        "entity_alias",
        "public_entity_master",
        "supplier_source",
        "supplier_relation",
        "supplier_identifier",
        "supplier_alias",
        "supplier_master",
        "reconciliation_result",
        "claim_conflict",
        "claim_evidence",
        "claim",
        "extraction_run",
        "document_page",
    ):
        op.drop_table(table)
    op.drop_column("document", "raw_artifact_id")
    op.drop_table("raw_artifact")
    op.drop_table("source_registry")
