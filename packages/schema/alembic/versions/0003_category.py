"""Add category columns for gasto classification."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0003_category"
down_revision = "0002_contract_scd2_unique"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("contract", sa.Column("category", sa.String(32), nullable=True))
    op.create_index("ix_contract_category", "contract", ["category"])
    op.add_column("budget_line", sa.Column("category", sa.String(32), nullable=True))
    op.create_index("ix_budget_line_category", "budget_line", ["category"])


def downgrade() -> None:
    op.drop_index("ix_budget_line_category", table_name="budget_line")
    op.drop_column("budget_line", "category")
    op.drop_index("ix_contract_category", table_name="contract")
    op.drop_column("contract", "category")
