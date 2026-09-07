"""Partial unique on current contracts for SCD2."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0002_contract_scd2_unique"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("uq_contract_cuce_source", "contract", type_="unique")
    op.create_index(
        "uq_contract_cuce_source_current",
        "contract",
        ["cuce", "source_id"],
        unique=True,
        postgresql_where=sa.text("is_current IS TRUE AND cuce IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_contract_cuce_source_current", table_name="contract")
    op.create_unique_constraint("uq_contract_cuce_source", "contract", ["cuce", "source_id"])
