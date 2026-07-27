"""Add tenant-scoped provider context stores."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260727_0008"
down_revision = "20260727_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "provider_universe_members",
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
        sa.Column("universe_id", sa.Text(), nullable=False),
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
            "universe_id",
            "as_of",
            name="uq_provider_universe_members_tenant_provider_universe_as_of",
        ),
    )
    op.create_index(
        "ix_provider_universe_members_tenant_universe_as_of",
        "provider_universe_members",
        ["tenant_id", "universe_id", "as_of"],
    )
    op.create_index(
        "ix_provider_universe_members_tenant_provider_as_of",
        "provider_universe_members",
        ["tenant_id", "provider_id", "as_of"],
    )

    op.create_table(
        "provider_factor_snapshots",
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
        sa.Column("kind", sa.Text(), nullable=False),
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
        sa.CheckConstraint(
            "kind in ('fundamentals', 'sentiment', 'volatility', 'macro')",
            name="ck_provider_factor_snapshots_kind",
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "kind",
            "provider_id",
            "symbol",
            "as_of",
            name="uq_provider_factor_snapshots_tenant_kind_provider_symbol_as_of",
        ),
    )
    op.create_index(
        "ix_provider_factor_snapshots_tenant_symbol_kind_as_of",
        "provider_factor_snapshots",
        ["tenant_id", "symbol", "kind", "as_of"],
    )
    op.create_index(
        "ix_provider_factor_snapshots_tenant_provider_kind_as_of",
        "provider_factor_snapshots",
        ["tenant_id", "provider_id", "kind", "as_of"],
    )
    _enable_tenant_rls("provider_universe_members")
    _enable_tenant_rls("provider_factor_snapshots")


def downgrade() -> None:
    _disable_tenant_rls("provider_factor_snapshots")
    _disable_tenant_rls("provider_universe_members")
    op.drop_index(
        "ix_provider_factor_snapshots_tenant_provider_kind_as_of",
        table_name="provider_factor_snapshots",
    )
    op.drop_index(
        "ix_provider_factor_snapshots_tenant_symbol_kind_as_of",
        table_name="provider_factor_snapshots",
    )
    op.drop_table("provider_factor_snapshots")
    op.drop_index(
        "ix_provider_universe_members_tenant_provider_as_of",
        table_name="provider_universe_members",
    )
    op.drop_index(
        "ix_provider_universe_members_tenant_universe_as_of",
        table_name="provider_universe_members",
    )
    op.drop_table("provider_universe_members")


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
