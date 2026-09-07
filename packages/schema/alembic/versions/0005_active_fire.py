"""Active fire detections (FIRMS) table."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0005_active_fire"
down_revision = "0004_fire_ledger"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "active_fire_detection",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("acq_date", sa.Date(), nullable=True),
        sa.Column("latitude", sa.Numeric(10, 6), nullable=True),
        sa.Column("longitude", sa.Numeric(10, 6), nullable=True),
        sa.Column("brightness", sa.Numeric(12, 2), nullable=True),
        sa.Column("frp", sa.Numeric(12, 2), nullable=True),
        sa.Column("confidence", sa.String(32), nullable=True),
        sa.Column("satellite", sa.String(64), nullable=True),
        sa.Column("department", sa.String(128), nullable=True),
        sa.Column("municipality", sa.String(128), nullable=True),
        sa.Column("territory_id", sa.Integer(), sa.ForeignKey("territory.id"), nullable=True),
        sa.Column("source_id", sa.String(64), nullable=False, server_default="firms"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_active_fire_detection_year", "active_fire_detection", ["year"])
    op.create_index("ix_active_fire_year_dept", "active_fire_detection", ["year", "department"])


def downgrade() -> None:
    op.drop_index("ix_active_fire_year_dept", table_name="active_fire_detection")
    op.drop_index("ix_active_fire_detection_year", table_name="active_fire_detection")
    op.drop_table("active_fire_detection")
