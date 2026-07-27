"""Add tenant-scoped market-data and screener stores."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260727_0007"
down_revision = "20260727_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "market_data_snapshots",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("provider_id", sa.Text(), nullable=False),
        sa.Column("symbol", sa.Text(), nullable=False),
        sa.Column("as_of", sa.Text(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "recorded_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "provider_id",
            "symbol",
            "as_of",
            name="uq_market_data_snapshots_tenant_provider_symbol_as_of",
        ),
    )
    op.create_index(
        "ix_market_data_snapshots_tenant_symbol_as_of",
        "market_data_snapshots",
        ["tenant_id", "symbol", "as_of"],
    )
    op.create_index(
        "ix_market_data_snapshots_tenant_provider_as_of",
        "market_data_snapshots",
        ["tenant_id", "provider_id", "as_of"],
    )

    op.create_table(
        "screener_runs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("run_id", sa.Text(), nullable=False),
        sa.Column("universe_id", sa.Text(), nullable=False),
        sa.Column("preset", sa.Text(), nullable=False),
        sa.Column("mode", sa.Text(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "recorded_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint("mode = 'read_only'", name="ck_screener_runs_read_only"),
        sa.UniqueConstraint("tenant_id", "run_id", name="uq_screener_runs_tenant_run_id"),
    )
    op.create_index(
        "ix_screener_runs_tenant_universe_preset",
        "screener_runs",
        ["tenant_id", "universe_id", "preset"],
    )
    _enable_tenant_rls("market_data_snapshots")
    _enable_tenant_rls("screener_runs")


def downgrade() -> None:
    _disable_tenant_rls("screener_runs")
    _disable_tenant_rls("market_data_snapshots")
    op.drop_index(
        "ix_screener_runs_tenant_universe_preset",
        table_name="screener_runs",
    )
    op.drop_table("screener_runs")
    op.drop_index(
        "ix_market_data_snapshots_tenant_provider_as_of",
        table_name="market_data_snapshots",
    )
    op.drop_index(
        "ix_market_data_snapshots_tenant_symbol_as_of",
        table_name="market_data_snapshots",
    )
    op.drop_table("market_data_snapshots")


def _enable_tenant_rls(table_name: str) -> None:
    tenant_setting = "nullif(current_setting('app.tenant_id', true), '')::uuid"
    op.execute(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY")
    op.execute(
        f"""
        CREATE POLICY tenant_isolation_{table_name}
        ON {table_name}
        USING (tenant_id = {tenant_setting})
        WITH CHECK (tenant_id = {tenant_setting})
        """
    )


def _disable_tenant_rls(table_name: str) -> None:
    op.execute(f"DROP POLICY IF EXISTS tenant_isolation_{table_name} ON {table_name}")
    op.execute(f"ALTER TABLE {table_name} DISABLE ROW LEVEL SECURITY")
