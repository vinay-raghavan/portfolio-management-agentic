"""Add tenant-scoped paper ledger stores."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260727_0010"
down_revision = "20260727_0009"
branch_labels = None
depends_on = None


PAPER_LEDGER_TABLES = (
    "paper_strategy_drafts",
    "paper_backtest_requests",
    "paper_orders",
    "paper_positions",
    "paper_fills",
    "paper_approval_requests",
    "paper_audit_events",
)


def upgrade() -> None:
    op.create_table(
        "paper_strategy_drafts",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        _tenant_column(),
        sa.Column("strategy_id", sa.Text(), nullable=False),
        sa.Column("symbol", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        _payload_column(),
        sa.Column("created_at", sa.Text(), nullable=False),
        _recorded_at_column(),
        sa.UniqueConstraint(
            "tenant_id",
            "strategy_id",
            name="uq_paper_strategy_drafts_tenant_strategy",
        ),
    )
    op.create_index(
        "ix_paper_strategy_drafts_tenant_symbol",
        "paper_strategy_drafts",
        ["tenant_id", "symbol"],
    )
    op.create_index(
        "ix_paper_strategy_drafts_tenant_created",
        "paper_strategy_drafts",
        ["tenant_id", "created_at"],
    )

    op.create_table(
        "paper_backtest_requests",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        _tenant_column(),
        sa.Column("request_id", sa.Text(), nullable=False),
        sa.Column("symbol", sa.Text(), nullable=False),
        sa.Column("setup", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        _payload_column(),
        sa.Column("start_date", sa.Text(), nullable=False),
        sa.Column("end_date", sa.Text(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        _recorded_at_column(),
        sa.UniqueConstraint(
            "tenant_id",
            "request_id",
            name="uq_paper_backtest_requests_tenant_request",
        ),
    )
    op.create_index(
        "ix_paper_backtest_requests_tenant_symbol_dates",
        "paper_backtest_requests",
        ["tenant_id", "symbol", "start_date", "end_date"],
    )
    op.create_index(
        "ix_paper_backtest_requests_tenant_status_created",
        "paper_backtest_requests",
        ["tenant_id", "status", "created_at"],
    )

    op.create_table(
        "paper_orders",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        _tenant_column(),
        sa.Column("order_id", sa.Text(), nullable=False),
        sa.Column("strategy_id", sa.Text(), nullable=False),
        sa.Column("symbol", sa.Text(), nullable=False),
        sa.Column("side", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        _payload_column(),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("filled_quantity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "fill_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        _recorded_at_column(),
        sa.UniqueConstraint(
            "tenant_id",
            "order_id",
            name="uq_paper_orders_tenant_order",
        ),
    )
    op.create_index(
        "ix_paper_orders_tenant_status_created",
        "paper_orders",
        ["tenant_id", "status", "created_at"],
    )
    op.create_index(
        "ix_paper_orders_tenant_symbol",
        "paper_orders",
        ["tenant_id", "symbol"],
    )

    op.create_table(
        "paper_positions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        _tenant_column(),
        sa.Column("symbol", sa.Text(), nullable=False),
        sa.Column("quantity", sa.Numeric(), nullable=False),
        _payload_column(),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="50"),
        _recorded_at_column(),
        sa.UniqueConstraint(
            "tenant_id",
            "symbol",
            name="uq_paper_positions_tenant_symbol",
        ),
    )
    op.create_index(
        "ix_paper_positions_tenant_sort_symbol",
        "paper_positions",
        ["tenant_id", "sort_order", "symbol"],
    )

    op.create_table(
        "paper_fills",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        _tenant_column(),
        sa.Column("fill_id", sa.Text(), nullable=False),
        sa.Column("order_id", sa.Text(), nullable=False),
        sa.Column("symbol", sa.Text(), nullable=False),
        sa.Column("side", sa.Text(), nullable=False),
        _payload_column(),
        sa.Column("filled_at", sa.Text(), nullable=False),
        _recorded_at_column(),
        sa.UniqueConstraint(
            "tenant_id",
            "fill_id",
            name="uq_paper_fills_tenant_fill",
        ),
    )
    op.create_index(
        "ix_paper_fills_tenant_order",
        "paper_fills",
        ["tenant_id", "order_id"],
    )
    op.create_index(
        "ix_paper_fills_tenant_symbol_filled",
        "paper_fills",
        ["tenant_id", "symbol", "filled_at"],
    )

    op.create_table(
        "paper_approval_requests",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        _tenant_column(),
        sa.Column("approval_id", sa.Text(), nullable=False),
        sa.Column("related_id", sa.Text(), nullable=False),
        sa.Column("action_type", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        _payload_column(),
        sa.Column("requested_at", sa.Text(), nullable=False),
        _recorded_at_column(),
        sa.UniqueConstraint(
            "tenant_id",
            "approval_id",
            name="uq_paper_approval_requests_tenant_approval",
        ),
    )
    op.create_index(
        "ix_paper_approval_requests_tenant_status_requested",
        "paper_approval_requests",
        ["tenant_id", "status", "requested_at"],
    )
    op.create_index(
        "ix_paper_approval_requests_tenant_related",
        "paper_approval_requests",
        ["tenant_id", "related_id"],
    )

    op.create_table(
        "paper_audit_events",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        _tenant_column(),
        sa.Column("event_id", sa.Text(), nullable=False),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("entity_id", sa.Text(), nullable=False),
        sa.Column("actor", sa.Text(), nullable=False),
        _payload_column(),
        sa.Column("created_at", sa.Text(), nullable=False),
        _recorded_at_column(),
        sa.UniqueConstraint(
            "tenant_id",
            "event_id",
            name="uq_paper_audit_events_tenant_event",
        ),
    )
    op.create_index(
        "ix_paper_audit_events_tenant_entity",
        "paper_audit_events",
        ["tenant_id", "entity_id"],
    )
    op.create_index(
        "ix_paper_audit_events_tenant_created",
        "paper_audit_events",
        ["tenant_id", "created_at"],
    )

    for table_name in PAPER_LEDGER_TABLES:
        _enable_tenant_rls(table_name)


def downgrade() -> None:
    for table_name in reversed(PAPER_LEDGER_TABLES):
        _disable_tenant_rls(table_name)

    op.drop_index("ix_paper_audit_events_tenant_created", table_name="paper_audit_events")
    op.drop_index("ix_paper_audit_events_tenant_entity", table_name="paper_audit_events")
    op.drop_table("paper_audit_events")
    op.drop_index(
        "ix_paper_approval_requests_tenant_related",
        table_name="paper_approval_requests",
    )
    op.drop_index(
        "ix_paper_approval_requests_tenant_status_requested",
        table_name="paper_approval_requests",
    )
    op.drop_table("paper_approval_requests")
    op.drop_index("ix_paper_fills_tenant_symbol_filled", table_name="paper_fills")
    op.drop_index("ix_paper_fills_tenant_order", table_name="paper_fills")
    op.drop_table("paper_fills")
    op.drop_index("ix_paper_positions_tenant_sort_symbol", table_name="paper_positions")
    op.drop_table("paper_positions")
    op.drop_index("ix_paper_orders_tenant_symbol", table_name="paper_orders")
    op.drop_index("ix_paper_orders_tenant_status_created", table_name="paper_orders")
    op.drop_table("paper_orders")
    op.drop_index(
        "ix_paper_backtest_requests_tenant_status_created",
        table_name="paper_backtest_requests",
    )
    op.drop_index(
        "ix_paper_backtest_requests_tenant_symbol_dates",
        table_name="paper_backtest_requests",
    )
    op.drop_table("paper_backtest_requests")
    op.drop_index(
        "ix_paper_strategy_drafts_tenant_created",
        table_name="paper_strategy_drafts",
    )
    op.drop_index(
        "ix_paper_strategy_drafts_tenant_symbol",
        table_name="paper_strategy_drafts",
    )
    op.drop_table("paper_strategy_drafts")


def _tenant_column() -> sa.Column:
    return sa.Column(
        "tenant_id",
        postgresql.UUID(as_uuid=True),
        sa.ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )


def _payload_column() -> sa.Column:
    return sa.Column(
        "payload",
        postgresql.JSONB(astext_type=sa.Text()),
        nullable=False,
        server_default=sa.text("'{}'::jsonb"),
    )


def _recorded_at_column() -> sa.Column:
    return sa.Column(
        "recorded_at",
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("now()"),
    )


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
