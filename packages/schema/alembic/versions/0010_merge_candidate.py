"""G4 merge candidates — fuzzy pairs without auto-merge."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0010_merge_candidate"
down_revision = "0009_evidence_masters"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "merge_candidate",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("left_type", sa.String(64), nullable=False),
        sa.Column("left_id", sa.Integer(), nullable=False),
        sa.Column("right_id", sa.Integer(), nullable=False),
        sa.Column("score", sa.Numeric(6, 2), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint(
            "left_type",
            "left_id",
            "right_id",
            name="uq_merge_candidate_pair",
        ),
    )
    op.create_index("ix_merge_candidate_status", "merge_candidate", ["status"])
    op.create_index("ix_merge_candidate_left", "merge_candidate", ["left_type", "left_id"])


def downgrade() -> None:
    op.drop_index("ix_merge_candidate_left", table_name="merge_candidate")
    op.drop_index("ix_merge_candidate_status", table_name="merge_candidate")
    op.drop_table("merge_candidate")
