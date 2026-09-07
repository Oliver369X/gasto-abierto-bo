"""F1: fire expenditure attribution ranges and ledger buckets."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0006_fire_attribution"
down_revision = "0005_active_fire"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("fire_expenditure", sa.Column("amount_total", sa.Numeric(18, 2), nullable=True))
    op.add_column(
        "fire_expenditure", sa.Column("amount_attributed_low", sa.Numeric(18, 2), nullable=True)
    )
    op.add_column(
        "fire_expenditure", sa.Column("amount_attributed_base", sa.Numeric(18, 2), nullable=True)
    )
    op.add_column(
        "fire_expenditure", sa.Column("amount_attributed_high", sa.Numeric(18, 2), nullable=True)
    )
    op.add_column(
        "fire_expenditure",
        sa.Column("allocation_method", sa.String(32), nullable=False, server_default="none"),
    )
    op.add_column(
        "fire_expenditure",
        sa.Column("allocation_confidence", sa.Numeric(4, 3), nullable=False, server_default="0"),
    )
    op.add_column(
        "fire_expenditure",
        sa.Column("ledger_bucket", sa.String(32), nullable=False, server_default="probable"),
    )
    op.add_column(
        "fire_expenditure",
        sa.Column("is_synthetic", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "fire_expenditure", sa.Column("recovery_status", sa.String(64), nullable=True)
    )
    op.add_column(
        "fire_expenditure", sa.Column("link_strength", sa.String(32), nullable=True)
    )
    op.create_index(
        "ix_fire_expenditure_ledger_bucket", "fire_expenditure", ["ledger_bucket"]
    )
    op.create_index("ix_fire_expenditure_synthetic", "fire_expenditure", ["is_synthetic"])


def downgrade() -> None:
    op.drop_index("ix_fire_expenditure_synthetic", table_name="fire_expenditure")
    op.drop_index("ix_fire_expenditure_ledger_bucket", table_name="fire_expenditure")
    for col in (
        "link_strength",
        "recovery_status",
        "is_synthetic",
        "ledger_bucket",
        "allocation_confidence",
        "allocation_method",
        "amount_attributed_high",
        "amount_attributed_base",
        "amount_attributed_low",
        "amount_total",
    ):
        op.drop_column("fire_expenditure", col)
