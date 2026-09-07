"""F8–F10: fire geo clusters, burned area, capability assets, event links."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0007_fire_geo_capability"
down_revision = "0006_fire_attribution"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("fire_event", sa.Column("code", sa.String(128), nullable=True))
    op.add_column("fire_event", sa.Column("confidence", sa.Numeric(4, 3), nullable=True))
    op.add_column("fire_event", sa.Column("hectares_reported", sa.Numeric(18, 2), nullable=True))
    op.add_column("fire_event", sa.Column("sources", sa.JSON(), nullable=True))
    op.create_index("ix_fire_event_code", "fire_event", ["code"], unique=True)

    op.create_table(
        "fire_cluster",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("fire_event_id", sa.Integer(), sa.ForeignKey("fire_event.id"), nullable=True),
        sa.Column("territory_id", sa.Integer(), sa.ForeignKey("territory.id"), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("centroid_lat", sa.Numeric(10, 6), nullable=True),
        sa.Column("centroid_lon", sa.Numeric(10, 6), nullable=True),
        sa.Column("detection_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_frp", sa.Numeric(12, 2), nullable=True),
        sa.Column("meta", sa.JSON(), nullable=True),
        sa.Column("source_id", sa.String(64), nullable=False, server_default="firms"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_fire_cluster_year", "fire_cluster", ["year"])

    op.create_table(
        "burned_area",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("fire_event_id", sa.Integer(), sa.ForeignKey("fire_event.id"), nullable=True),
        sa.Column("territory_id", sa.Integer(), sa.ForeignKey("territory.id"), nullable=True),
        sa.Column("hectares", sa.Numeric(18, 2), nullable=False),
        sa.Column("method", sa.String(64), nullable=False, server_default="reported"),
        sa.Column("source_id", sa.String(64), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_burned_area_year", "burned_area", ["year"])

    op.create_table(
        "fire_capability_asset",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("asset_type", sa.String(64), nullable=False),
        sa.Column("name", sa.String(512), nullable=False),
        sa.Column("ownership", sa.String(32), nullable=False, server_default="unknown"),
        sa.Column("entity_id", sa.Integer(), sa.ForeignKey("entity.id"), nullable=True),
        sa.Column("territory_id", sa.Integer(), sa.ForeignKey("territory.id"), nullable=True),
        sa.Column("quantity", sa.Numeric(12, 2), nullable=True),
        sa.Column("acquired_via", sa.String(64), nullable=True),
        sa.Column("fire_expenditure_id", sa.Integer(), sa.ForeignKey("fire_expenditure.id"), nullable=True),
        sa.Column("is_preventive", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("evidence", sa.JSON(), nullable=True),
        sa.Column("source_id", sa.String(64), nullable=False, server_default="seed_fire"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_fire_capability_year_type", "fire_capability_asset", ["year", "asset_type"])

    op.create_table(
        "fire_link",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("from_type", sa.String(64), nullable=False),
        sa.Column("from_id", sa.Integer(), nullable=False),
        sa.Column("to_type", sa.String(64), nullable=False),
        sa.Column("to_id", sa.Integer(), nullable=False),
        sa.Column(
            "strength",
            sa.String(32),
            nullable=False,
            server_default="POSIBLE",
        ),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("evidence", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_fire_link_from", "fire_link", ["from_type", "from_id"])
    op.create_index("ix_fire_link_to", "fire_link", ["to_type", "to_id"])

    op.add_column(
        "active_fire_detection",
        sa.Column("cluster_id", sa.Integer(), sa.ForeignKey("fire_cluster.id"), nullable=True),
    )
    op.add_column(
        "emergency_declaration",
        sa.Column("valid_from", sa.Date(), nullable=True),
    )
    op.add_column(
        "emergency_declaration",
        sa.Column("valid_to", sa.Date(), nullable=True),
    )
    op.add_column(
        "emergency_declaration",
        sa.Column("authority", sa.String(256), nullable=True),
    )
    op.add_column(
        "emergency_declaration",
        sa.Column("full_text", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("emergency_declaration", "full_text")
    op.drop_column("emergency_declaration", "authority")
    op.drop_column("emergency_declaration", "valid_to")
    op.drop_column("emergency_declaration", "valid_from")
    op.drop_column("active_fire_detection", "cluster_id")
    op.drop_index("ix_fire_link_to", table_name="fire_link")
    op.drop_index("ix_fire_link_from", table_name="fire_link")
    op.drop_table("fire_link")
    op.drop_index("ix_fire_capability_year_type", table_name="fire_capability_asset")
    op.drop_table("fire_capability_asset")
    op.drop_index("ix_burned_area_year", table_name="burned_area")
    op.drop_table("burned_area")
    op.drop_index("ix_fire_cluster_year", table_name="fire_cluster")
    op.drop_table("fire_cluster")
    op.drop_index("ix_fire_event_code", table_name="fire_event")
    op.drop_column("fire_event", "sources")
    op.drop_column("fire_event", "hectares_reported")
    op.drop_column("fire_event", "confidence")
    op.drop_column("fire_event", "code")
