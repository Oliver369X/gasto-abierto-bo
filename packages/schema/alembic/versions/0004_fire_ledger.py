"""AURA Incendios fire ledger tables."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0004_fire_ledger"
down_revision = "0003_category"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "territory",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("slug", sa.String(128), nullable=False),
        sa.Column("level", sa.String(32), nullable=False),
        sa.Column("parent_id", sa.Integer(), sa.ForeignKey("territory.id"), nullable=True),
        sa.Column("ine_code", sa.String(32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_territory_slug", "territory", ["slug"], unique=True)

    op.create_table(
        "fire_season",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("quality_grade", sa.String(8), server_default="D"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("year", name="uq_fire_season_year"),
    )
    op.create_index("ix_fire_season_year", "fire_season", ["year"])

    op.create_table(
        "fire_event",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("season_id", sa.Integer(), sa.ForeignKey("fire_season.id"), nullable=False),
        sa.Column("territory_id", sa.Integer(), sa.ForeignKey("territory.id"), nullable=True),
        sa.Column("name", sa.String(512), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("meta", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "fire_classification_run",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(32), server_default="running"),
        sa.Column("method", sa.String(64), server_default="exact_keyword"),
        sa.Column("records_in", sa.Integer(), server_default="0"),
        sa.Column("records_out", sa.Integer(), server_default="0"),
        sa.Column("meta", sa.JSON(), nullable=True),
    )

    op.create_table(
        "fire_expenditure",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("season_id", sa.Integer(), sa.ForeignKey("fire_season.id"), nullable=True),
        sa.Column("fire_event_id", sa.Integer(), sa.ForeignKey("fire_event.id"), nullable=True),
        sa.Column("title", sa.String(1024), nullable=False),
        sa.Column("object_description", sa.Text(), nullable=True),
        sa.Column("attribution", sa.String(32), nullable=False),
        sa.Column("confidence_score", sa.Numeric(4, 3), nullable=False, server_default="0.500"),
        sa.Column("classification_method", sa.String(64), nullable=False, server_default="exact_keyword"),
        sa.Column("cycle", sa.String(32), nullable=False),
        sa.Column("paying_entity_id", sa.Integer(), sa.ForeignKey("entity.id"), nullable=True),
        sa.Column("beneficiary_territory_id", sa.Integer(), sa.ForeignKey("territory.id"), nullable=True),
        sa.Column("supplier_id", sa.Integer(), sa.ForeignKey("supplier.id"), nullable=True),
        sa.Column("contract_id", sa.Integer(), sa.ForeignKey("contract.id"), nullable=True),
        sa.Column("budget_line_id", sa.Integer(), sa.ForeignKey("budget_line.id"), nullable=True),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("document.id"), nullable=True),
        sa.Column(
            "classification_run_id",
            sa.Integer(),
            sa.ForeignKey("fire_classification_run.id"),
            nullable=True,
        ),
        sa.Column("amount_contract", sa.Numeric(18, 2), nullable=True),
        sa.Column("amount_attributed", sa.Numeric(18, 2), nullable=True),
        sa.Column("currency", sa.String(8), server_default="BOB"),
        sa.Column("quality_grade", sa.String(8), server_default="D"),
        sa.Column("cuce", sa.String(64), nullable=True),
        sa.Column("evidence", sa.JSON(), nullable=True),
        sa.Column("source_id", sa.String(64), nullable=False, server_default="seed_fire"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("code", name="uq_fire_expenditure_code"),
    )
    op.create_index("ix_fire_expenditure_code", "fire_expenditure", ["code"])
    op.create_index("ix_fire_expenditure_year", "fire_expenditure", ["year"])
    op.create_index("ix_fire_expenditure_cuce", "fire_expenditure", ["cuce"])
    op.create_index("ix_fire_expenditure_year_attr", "fire_expenditure", ["year", "attribution"])

    op.create_table(
        "emergency_declaration",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(1024), nullable=False),
        sa.Column("decree_number", sa.String(128), nullable=True),
        sa.Column("event_type", sa.String(64), nullable=False, server_default="incendio_forestal"),
        sa.Column("entity_id", sa.Integer(), sa.ForeignKey("entity.id"), nullable=True),
        sa.Column("territory_id", sa.Integer(), sa.ForeignKey("territory.id"), nullable=True),
        sa.Column("promulgated_at", sa.Date(), nullable=True),
        sa.Column("published_at", sa.Date(), nullable=True),
        sa.Column("url", sa.String(2048), nullable=True),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("document.id"), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("source_id", sa.String(64), nullable=False, server_default="gaceta"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "operational_output",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("season_id", sa.Integer(), sa.ForeignKey("fire_season.id"), nullable=True),
        sa.Column("entity_id", sa.Integer(), sa.ForeignKey("entity.id"), nullable=True),
        sa.Column("territory_id", sa.Integer(), sa.ForeignKey("territory.id"), nullable=True),
        sa.Column("metric_key", sa.String(128), nullable=False),
        sa.Column("metric_label", sa.String(256), nullable=False),
        sa.Column("value_numeric", sa.Numeric(18, 2), nullable=True),
        sa.Column("value_text", sa.String(512), nullable=True),
        sa.Column("unit", sa.String(64), nullable=True),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("document.id"), nullable=True),
        sa.Column("evidence_page", sa.Integer(), nullable=True),
        sa.Column("evidence_quote", sa.Text(), nullable=True),
        sa.Column("source_id", sa.String(64), nullable=False, server_default="mindef"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_operational_output_year", "operational_output", ["year"])
    op.create_index("ix_operational_output_metric_key", "operational_output", ["metric_key"])

    op.create_table(
        "donation_aid",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("donor_name", sa.String(512), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("amount", sa.Numeric(18, 2), nullable=True),
        sa.Column("currency", sa.String(8), server_default="BOB"),
        sa.Column("in_kind", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("territory_id", sa.Integer(), sa.ForeignKey("territory.id"), nullable=True),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("document.id"), nullable=True),
        sa.Column("evidence", sa.JSON(), nullable=True),
        sa.Column("source_id", sa.String(64), nullable=False, server_default="seed_fire"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_donation_aid_year", "donation_aid", ["year"])


def downgrade() -> None:
    op.drop_index("ix_donation_aid_year", table_name="donation_aid")
    op.drop_table("donation_aid")
    op.drop_index("ix_operational_output_metric_key", table_name="operational_output")
    op.drop_index("ix_operational_output_year", table_name="operational_output")
    op.drop_table("operational_output")
    op.drop_table("emergency_declaration")
    op.drop_index("ix_fire_expenditure_year_attr", table_name="fire_expenditure")
    op.drop_index("ix_fire_expenditure_cuce", table_name="fire_expenditure")
    op.drop_index("ix_fire_expenditure_year", table_name="fire_expenditure")
    op.drop_index("ix_fire_expenditure_code", table_name="fire_expenditure")
    op.drop_table("fire_expenditure")
    op.drop_table("fire_classification_run")
    op.drop_table("fire_event")
    op.drop_index("ix_fire_season_year", table_name="fire_season")
    op.drop_table("fire_season")
    op.drop_index("ix_territory_slug", table_name="territory")
    op.drop_table("territory")
