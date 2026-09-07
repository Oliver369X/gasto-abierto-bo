"""Initial schema for Gasto Abierto Bolivia."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ingestion_run",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_id", sa.String(64), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(32), server_default="running"),
        sa.Column("records_in", sa.Integer(), server_default="0"),
        sa.Column("records_out", sa.Integer(), server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("meta", sa.JSON(), server_default="{}"),
    )
    op.create_index("ix_ingestion_run_source_id", "ingestion_run", ["source_id"])

    op.create_table(
        "entity",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(512), nullable=False),
        sa.Column("canonical_name", sa.String(512), nullable=False),
        sa.Column("level", sa.String(32), nullable=False),
        sa.Column("aliases", sa.JSON(), server_default="[]"),
        sa.Column("nit", sa.String(32), nullable=True),
        sa.Column("department", sa.String(128), nullable=True),
        sa.Column("source_id", sa.String(64), nullable=False, server_default="seed"),
        sa.Column("ingestion_run_id", sa.Integer(), sa.ForeignKey("ingestion_run.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_entity_canonical_name", "entity", ["canonical_name"])
    op.create_index("ix_entity_nit", "entity", ["nit"])

    op.create_table(
        "supplier",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(512), nullable=False),
        sa.Column("canonical_name", sa.String(512), nullable=False),
        sa.Column("nit", sa.String(32), nullable=True),
        sa.Column("aliases", sa.JSON(), server_default="[]"),
        sa.Column("source_id", sa.String(64), nullable=False, server_default="seed"),
        sa.Column("ingestion_run_id", sa.Integer(), sa.ForeignKey("ingestion_run.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_supplier_canonical_name", "supplier", ["canonical_name"])
    op.create_index("ix_supplier_nit", "supplier", ["nit"])

    op.create_table(
        "budget_line",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("entity_id", sa.Integer(), sa.ForeignKey("entity.id"), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("program_project", sa.String(512), nullable=True),
        sa.Column("budget_item", sa.String(128), nullable=True),
        sa.Column("initial_amount", sa.Numeric(18, 2), nullable=True),
        sa.Column("modified_amount", sa.Numeric(18, 2), nullable=True),
        sa.Column("current_amount", sa.Numeric(18, 2), nullable=True),
        sa.Column("executed_amount", sa.Numeric(18, 2), nullable=True),
        sa.Column("currency", sa.String(8), server_default="BOB"),
        sa.Column("as_of", sa.Date(), nullable=True),
        sa.Column("source_id", sa.String(64), nullable=False),
        sa.Column("ingestion_run_id", sa.Integer(), sa.ForeignKey("ingestion_run.id"), nullable=True),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_index("ix_budget_line_current", "budget_line", ["entity_id", "year", "is_current"])

    op.create_table(
        "contract",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("cuce", sa.String(64), nullable=True),
        sa.Column("entity_id", sa.Integer(), sa.ForeignKey("entity.id"), nullable=False),
        sa.Column("supplier_id", sa.Integer(), sa.ForeignKey("supplier.id"), nullable=True),
        sa.Column("object_description", sa.Text(), nullable=True),
        sa.Column("modality", sa.String(128), nullable=True),
        sa.Column("amount", sa.Numeric(18, 2), nullable=True),
        sa.Column("currency", sa.String(8), server_default="BOB"),
        sa.Column("contract_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(64), nullable=True),
        sa.Column("documents", sa.JSON(), server_default="[]"),
        sa.Column("source_id", sa.String(64), nullable=False),
        sa.Column("ingestion_run_id", sa.Integer(), sa.ForeignKey("ingestion_run.id"), nullable=True),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("cuce", "source_id", name="uq_contract_cuce_source"),
    )
    op.create_index("ix_contract_cuce", "contract", ["cuce"])

    op.create_table(
        "audit_report",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("entity_id", sa.Integer(), sa.ForeignKey("entity.id"), nullable=True),
        sa.Column("title", sa.String(1024), nullable=False),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("url", sa.String(2048), nullable=False),
        sa.Column("findings_summary", sa.Text(), nullable=True),
        sa.Column("source_id", sa.String(64), nullable=False, server_default="cge"),
        sa.Column("ingestion_run_id", sa.Integer(), sa.ForeignKey("ingestion_run.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "document",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("url", sa.String(2048), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=True),
        sa.Column("mime", sa.String(128), nullable=True),
        sa.Column("minio_key", sa.String(512), nullable=True),
        sa.Column("source_id", sa.String(64), nullable=False),
        sa.Column("ingestion_run_id", sa.Integer(), sa.ForeignKey("ingestion_run.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_document_sha256", "document", ["sha256"])

    op.create_table(
        "discrepancy",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("concept", sa.String(256), nullable=False),
        sa.Column("entity_id", sa.Integer(), sa.ForeignKey("entity.id"), nullable=True),
        sa.Column("amount_a", sa.Numeric(18, 2), nullable=True),
        sa.Column("amount_b", sa.Numeric(18, 2), nullable=True),
        sa.Column("source_a", sa.String(64), nullable=False),
        sa.Column("source_b", sa.String(64), nullable=False),
        sa.Column("ref_a", sa.String(256), nullable=True),
        sa.Column("ref_b", sa.String(256), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "alert",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("rule_id", sa.String(64), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False, server_default="medium"),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("entity_id", sa.Integer(), sa.ForeignKey("entity.id"), nullable=True),
        sa.Column("contract_id", sa.Integer(), sa.ForeignKey("contract.id"), nullable=True),
        sa.Column("supplier_id", sa.Integer(), sa.ForeignKey("supplier.id"), nullable=True),
        sa.Column("evidence", sa.JSON(), server_default="{}"),
        sa.Column("source_id", sa.String(64), nullable=False, server_default="rules"),
        sa.Column("ingestion_run_id", sa.Integer(), sa.ForeignKey("ingestion_run.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_alert_rule_id", "alert", ["rule_id"])


def downgrade() -> None:
    op.drop_table("alert")
    op.drop_table("discrepancy")
    op.drop_table("document")
    op.drop_table("audit_report")
    op.drop_table("contract")
    op.drop_table("budget_line")
    op.drop_table("supplier")
    op.drop_table("entity")
    op.drop_table("ingestion_run")
