"""Add tenant-scoped model usage telemetry events."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260727_0005"
down_revision = "20260727_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "model_usage_events",
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
        sa.Column("request_id", sa.Text(), nullable=False),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("model", sa.Text(), nullable=False),
        sa.Column("route", sa.Text(), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False),
        sa.Column("output_tokens", sa.Integer(), nullable=False),
        sa.Column("tool_calls", sa.Integer(), nullable=False),
        sa.Column("queue_wait_ms", sa.Integer(), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("retries", sa.Integer(), nullable=False),
        sa.Column("allowed", sa.Boolean(), nullable=False),
        sa.Column(
            "violations",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("prompt_budget_tokens", sa.Integer(), nullable=True),
        sa.Column("output_budget_tokens", sa.Integer(), nullable=True),
        sa.Column("tool_call_budget", sa.Integer(), nullable=True),
        sa.Column("context_window_tokens", sa.Integer(), nullable=False),
        sa.Column("max_request_input_tokens", sa.Integer(), nullable=False),
        sa.Column("prompt_utilization", sa.Float(), nullable=True),
        sa.Column("output_utilization", sa.Float(), nullable=True),
        sa.Column("tool_call_utilization", sa.Float(), nullable=True),
        sa.Column("context_utilization", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint(
            "tenant_id",
            "request_id",
            name="uq_model_usage_events_tenant_request",
        ),
        sa.CheckConstraint("prompt_tokens >= 0", name="ck_model_usage_prompt_tokens_nonnegative"),
        sa.CheckConstraint("output_tokens >= 0", name="ck_model_usage_output_tokens_nonnegative"),
        sa.CheckConstraint("tool_calls >= 0", name="ck_model_usage_tool_calls_nonnegative"),
        sa.CheckConstraint("queue_wait_ms >= 0", name="ck_model_usage_queue_wait_nonnegative"),
        sa.CheckConstraint("latency_ms >= 0", name="ck_model_usage_latency_nonnegative"),
        sa.CheckConstraint("retries >= 0", name="ck_model_usage_retries_nonnegative"),
    )
    op.create_index(
        "ix_model_usage_events_tenant_created_at",
        "model_usage_events",
        ["tenant_id", "created_at"],
    )
    op.create_index(
        "ix_model_usage_events_tenant_provider_model_route_created",
        "model_usage_events",
        ["tenant_id", "provider", "model", "route", "created_at"],
    )
    _enable_tenant_rls("model_usage_events")


def downgrade() -> None:
    _disable_tenant_rls("model_usage_events")
    op.drop_index(
        "ix_model_usage_events_tenant_provider_model_route_created",
        table_name="model_usage_events",
    )
    op.drop_index(
        "ix_model_usage_events_tenant_created_at",
        table_name="model_usage_events",
    )
    op.drop_table("model_usage_events")


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
