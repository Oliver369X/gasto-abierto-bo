"""G1: data quality columns + G3 completeness stubs on core tables.

Backfills run in autocommit batches to avoid OOM on ~1.5M contracts.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0008_data_quality"
down_revision = "0007_fire_geo_capability"
branch_labels = None
depends_on = None

TABLES = (
    "contract",
    "budget_line",
    "supplier",
    "entity",
    "audit_report",
    "discrepancy",
    "alert",
)


def upgrade() -> None:
    for table in TABLES:
        op.add_column(table, sa.Column("is_synthetic", sa.Boolean(), server_default=sa.text("false"), nullable=False))
        op.add_column(table, sa.Column("is_official", sa.Boolean(), server_default=sa.text("false"), nullable=False))
        op.add_column(table, sa.Column("is_inferred", sa.Boolean(), server_default=sa.text("false"), nullable=False))
        op.add_column(table, sa.Column("source_quality", sa.String(32), nullable=True))
        op.add_column(table, sa.Column("evidence_status", sa.String(32), nullable=True))
        op.add_column(table, sa.Column("confidence_score", sa.Numeric(4, 3), nullable=True))
        op.add_column(table, sa.Column("data_origin", sa.String(64), nullable=True))
        op.add_column(table, sa.Column("source_note", sa.String(512), nullable=True))

    op.add_column("entity", sa.Column("entity_master_id", sa.Integer(), nullable=True))
    op.add_column("supplier", sa.Column("supplier_master_id", sa.Integer(), nullable=True))
    op.create_index("ix_entity_master_id", "entity", ["entity_master_id"])
    op.create_index("ix_supplier_master_id", "supplier", ["supplier_master_id"])

    op.add_column(
        "contract",
        sa.Column("completeness_level", sa.Integer(), server_default=sa.text("0"), nullable=False),
    )
    for col in (
        "has_reference_price",
        "has_award",
        "has_awarded_amount",
        "has_supplier",
        "has_nit",
        "has_contract_doc",
        "has_modifications",
    ):
        op.add_column(
            "contract",
            sa.Column(col, sa.Boolean(), server_default=sa.text("false"), nullable=False),
        )
    op.add_column("contract", sa.Column("reference_price", sa.Numeric(18, 2), nullable=True))

    for col in (
        "budget_initial",
        "budget_modification",
        "budget_current",
        "commitment",
        "accrual",
        "payment",
    ):
        op.add_column("budget_line", sa.Column(col, sa.Numeric(18, 2), nullable=True))
    op.add_column("budget_line", sa.Column("budget_phase", sa.String(32), nullable=True))
    op.add_column("alert", sa.Column("legitimate_causes", sa.JSON(), nullable=True))

    op.create_index("ix_contract_source_quality", "contract", ["source_quality"])
    op.create_index("ix_contract_is_synthetic", "contract", ["is_synthetic"])
    op.create_index("ix_budget_source_quality", "budget_line", ["source_quality"])

    # Heavy updates outside the DDL transaction
    with op.get_context().autocommit_block():
        op.execute(
            """
            UPDATE budget_line SET
              budget_initial = initial_amount,
              budget_modification = modified_amount,
              budget_current = current_amount,
              payment = executed_amount,
              budget_phase = 'mapped'
            WHERE is_current IS TRUE
            """
        )
        # Default civic_mirror for bulk SICOES (single pass)
        op.execute(
            """
            UPDATE contract SET
              is_synthetic = FALSE,
              is_official = FALSE,
              is_inferred = FALSE,
              source_quality = 'OFFICIAL_UNVERIFIED',
              evidence_status = 'partial',
              confidence_score = 0.55,
              data_origin = 'civic_mirror'
            WHERE source_id = 'sicoes'
            """
        )
        op.execute(
            """
            UPDATE contract SET
              is_synthetic = TRUE,
              is_official = FALSE,
              source_quality = 'SYNTHETIC',
              evidence_status = 'none',
              confidence_score = 0,
              data_origin = 'seed'
            WHERE source_id = 'seed' OR cuce LIKE 'GA-DEEP-%'
            """
        )
        op.execute(
            """
            UPDATE contract SET
              is_synthetic = FALSE,
              is_official = TRUE,
              is_inferred = FALSE,
              source_quality = 'OFFICIAL_UNVERIFIED',
              evidence_status = 'linked',
              confidence_score = 0.7,
              data_origin = 'ocds'
            WHERE source_id = 'agetic' AND (cuce IS NULL OR cuce NOT LIKE 'GA-DEEP-%')
            """
        )
        op.execute(
            """
            UPDATE contract SET
              source_quality = 'INFERRED',
              data_origin = 'inferred',
              is_inferred = TRUE,
              confidence_score = 0.3,
              evidence_status = 'none'
            WHERE source_quality IS NULL
            """
        )
        # Completeness only where useful (amount or supplier present) — avoid full-table rewrite
        op.execute(
            """
            UPDATE contract SET
              has_awarded_amount = TRUE,
              completeness_level = GREATEST(completeness_level, 1)
            WHERE amount IS NOT NULL AND amount > 0
            """
        )
        op.execute(
            """
            UPDATE contract SET
              has_supplier = TRUE,
              completeness_level = LEAST(5, completeness_level + 1)
            WHERE supplier_id IS NOT NULL
            """
        )
        op.execute(
            """
            UPDATE contract SET
              has_award = TRUE
            WHERE has_awarded_amount OR has_supplier
            """
        )

        op.execute(
            """
            UPDATE budget_line SET
              is_synthetic = TRUE,
              source_quality = 'SYNTHETIC',
              data_origin = 'seed',
              evidence_status = 'none',
              confidence_score = 0
            WHERE source_id = 'seed'
            """
        )
        op.execute(
            """
            UPDATE budget_line SET
              is_synthetic = FALSE,
              is_official = FALSE,
              source_quality = 'PARTIAL',
              data_origin = 'civic_mirror',
              evidence_status = 'partial',
              confidence_score = 0.5
            WHERE source_id = 'presupuesto_abierto'
            """
        )
        op.execute(
            """
            UPDATE budget_line SET
              source_quality = 'INFERRED',
              data_origin = 'inferred',
              is_inferred = TRUE
            WHERE source_quality IS NULL
            """
        )

        for table in ("supplier", "entity", "audit_report", "discrepancy", "alert"):
            op.execute(
                f"""
                UPDATE {table} SET
                  source_quality = 'OFFICIAL_UNVERIFIED',
                  data_origin = 'civic_mirror',
                  evidence_status = 'partial',
                  confidence_score = 0.5
                WHERE source_quality IS NULL
                """
            )
        for table in ("supplier", "entity", "alert"):
            op.execute(
                f"""
                UPDATE {table} SET
                  is_synthetic = TRUE,
                  source_quality = 'SYNTHETIC',
                  data_origin = 'seed',
                  confidence_score = 0
                WHERE source_id = 'seed'
                """
            )


def downgrade() -> None:
    op.drop_column("alert", "legitimate_causes")
    for col in (
        "budget_phase",
        "payment",
        "accrual",
        "commitment",
        "budget_current",
        "budget_modification",
        "budget_initial",
    ):
        op.drop_column("budget_line", col)
    for col in (
        "reference_price",
        "has_modifications",
        "has_contract_doc",
        "has_nit",
        "has_supplier",
        "has_awarded_amount",
        "has_award",
        "has_reference_price",
        "completeness_level",
    ):
        op.drop_column("contract", col)
    op.drop_index("ix_supplier_master_id", table_name="supplier")
    op.drop_index("ix_entity_master_id", table_name="entity")
    op.drop_column("supplier", "supplier_master_id")
    op.drop_column("entity", "entity_master_id")
    op.drop_index("ix_budget_source_quality", table_name="budget_line")
    op.drop_index("ix_contract_is_synthetic", table_name="contract")
    op.drop_index("ix_contract_source_quality", table_name="contract")
    for table in TABLES:
        for col in (
            "source_note",
            "data_origin",
            "confidence_score",
            "evidence_status",
            "source_quality",
            "is_inferred",
            "is_official",
            "is_synthetic",
        ):
            op.drop_column(table, col)
