"""Add durable paper execution work-item queue."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260727_0004"
down_revision = "20260727_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "paper_execution_work_items",
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
        sa.Column(
            "batch_request_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("paper_batch_requests.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "grant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("paper_execution_grants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("order_id", sa.Text(), nullable=False),
        sa.Column(
            "requested_by_actor_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("actor_identities.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("idempotency_key", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'queued'")),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "decision",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("claimed_by", sa.Text(), nullable=True),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint(
            "tenant_id",
            "idempotency_key",
            name="uq_paper_execution_work_items_tenant_idempotency_key",
        ),
        sa.CheckConstraint(
            "status in ('queued', 'claimed', 'completed', 'failed', 'cancelled')",
            name="ck_paper_execution_work_items_status",
        ),
    )
    op.create_index(
        "ix_paper_execution_work_items_tenant_status_available",
        "paper_execution_work_items",
        ["tenant_id", "status", "available_at", "created_at"],
    )
    op.create_index(
        "ix_paper_execution_work_items_tenant_grant_status",
        "paper_execution_work_items",
        ["tenant_id", "grant_id", "status"],
    )
    _enable_tenant_rls("paper_execution_work_items")


def downgrade() -> None:
    _disable_tenant_rls("paper_execution_work_items")
    op.drop_index(
        "ix_paper_execution_work_items_tenant_grant_status",
        table_name="paper_execution_work_items",
    )
    op.drop_index(
        "ix_paper_execution_work_items_tenant_status_available",
        table_name="paper_execution_work_items",
    )
    op.drop_table("paper_execution_work_items")


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
