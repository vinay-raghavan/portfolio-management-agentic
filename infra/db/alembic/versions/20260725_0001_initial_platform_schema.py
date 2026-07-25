"""Initial tenant-scoped platform schema."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260725_0001"
down_revision = None
branch_labels = None
depends_on = None


TENANT_SCOPED_TABLES = (
    "agent_sessions",
    "fyers_connections",
    "provider_refresh_jobs",
    "provider_snapshot_envelopes",
    "broker_account_snapshots",
    "research_sources",
    "research_documents",
    "paper_execution_policy_ceilings",
    "paper_batch_requests",
    "paper_execution_grants",
    "paper_ledger_entries",
    "audit_events",
)


def _uuid_pk() -> sa.Column:
    return sa.Column(
        "id",
        postgresql.UUID(as_uuid=True),
        primary_key=True,
        server_default=sa.text("gen_random_uuid()"),
    )


def _tenant_id(nullable: bool = False) -> sa.Column:
    return sa.Column(
        "tenant_id",
        postgresql.UUID(as_uuid=True),
        sa.ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=nullable,
    )


def _actor_ref(name: str = "actor_identity_id", nullable: bool = True) -> sa.Column:
    return sa.Column(
        name,
        postgresql.UUID(as_uuid=True),
        sa.ForeignKey("actor_identities.id", ondelete="SET NULL" if nullable else "RESTRICT"),
        nullable=nullable,
    )


def _jsonb(name: str, nullable: bool = False, default: str = "'{}'::jsonb") -> sa.Column:
    return sa.Column(name, postgresql.JSONB(astext_type=sa.Text()), nullable=nullable, server_default=sa.text(default))


def _created_at() -> sa.Column:
    return sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))


def _updated_at() -> sa.Column:
    return sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))


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


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    op.create_table(
        "tenants",
        _uuid_pk(),
        sa.Column("slug", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'active'")),
        _jsonb("settings"),
        _created_at(),
        _updated_at(),
        sa.CheckConstraint("status in ('active', 'suspended', 'deleted')", name="ck_tenants_status"),
        sa.UniqueConstraint("slug", name="uq_tenants_slug"),
    )

    op.create_table(
        "actor_identities",
        _uuid_pk(),
        sa.Column("issuer", sa.Text(), nullable=False),
        sa.Column("subject", sa.Text(), nullable=False),
        sa.Column("email_hash", sa.Text(), nullable=True),
        sa.Column("display_name", sa.Text(), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        _created_at(),
        _updated_at(),
        sa.UniqueConstraint("issuer", "subject", name="uq_actor_identities_issuer_subject"),
    )

    op.create_table(
        "agent_sessions",
        _uuid_pk(),
        _tenant_id(),
        _actor_ref(nullable=False),
        sa.Column("request_id", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column("object_refs", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("idle_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("absolute_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        _created_at(),
        _updated_at(),
    )

    op.create_table(
        "fyers_connections",
        _uuid_pk(),
        _tenant_id(),
        _actor_ref("connected_by_actor_id", nullable=True),
        sa.Column("provider", sa.Text(), nullable=False, server_default=sa.text("'fyers'")),
        sa.Column("fyers_user_hash", sa.Text(), nullable=True),
        sa.Column("credential_ref", sa.Text(), nullable=True),
        sa.Column("scopes", postgresql.ARRAY(sa.Text()), nullable=False, server_default=sa.text("ARRAY[]::text[]")),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'disconnected'")),
        sa.Column("daily_auth_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_health_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("disconnected_at", sa.DateTime(timezone=True), nullable=True),
        _jsonb("metadata"),
        _created_at(),
        _updated_at(),
        sa.CheckConstraint(
            "provider = 'fyers' and status in ('connected', 'reconnect_required', 'disconnected', 'error')",
            name="ck_fyers_connections_status",
        ),
    )

    op.create_table(
        "provider_refresh_jobs",
        _uuid_pk(),
        _tenant_id(),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("connection_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("fyers_connections.id", ondelete="SET NULL"), nullable=True),
        sa.Column("job_type", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'queued'")),
        sa.Column("requested_by", sa.Text(), nullable=False, server_default=sa.text("'scheduler'")),
        sa.Column("normalized_query_or_symbol", sa.Text(), nullable=True),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        _jsonb("error", nullable=True),
        _created_at(),
        _updated_at(),
        sa.CheckConstraint("status in ('queued', 'running', 'succeeded', 'failed', 'cancelled')", name="ck_provider_refresh_jobs_status"),
    )

    op.create_table(
        "provider_snapshot_envelopes",
        _uuid_pk(),
        _tenant_id(),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("connection_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("fyers_connections.id", ondelete="SET NULL"), nullable=True),
        sa.Column("account_ref", sa.Text(), nullable=True),
        sa.Column("snapshot_type", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("as_of", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        _jsonb("payload"),
        _jsonb("provenance"),
        _created_at(),
        sa.CheckConstraint("status in ('fresh', 'stale', 'unavailable')", name="ck_provider_snapshot_envelopes_status"),
    )

    op.create_table(
        "broker_account_snapshots",
        _uuid_pk(),
        _tenant_id(),
        sa.Column("provider_snapshot_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("provider_snapshot_envelopes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("account_ref", sa.Text(), nullable=True),
        sa.Column("as_of", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        _jsonb("holdings", default="'[]'::jsonb"),
        _jsonb("positions", default="'[]'::jsonb"),
        _jsonb("funds"),
        _jsonb("orders", default="'[]'::jsonb"),
        _jsonb("trades", default="'[]'::jsonb"),
        _jsonb("provenance"),
        _created_at(),
        sa.CheckConstraint("status in ('fresh', 'stale', 'unavailable')", name="ck_broker_account_snapshots_status"),
    )

    op.create_table(
        "research_sources",
        _uuid_pk(),
        _tenant_id(),
        sa.Column("source_key", sa.Text(), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("source_type", sa.Text(), nullable=False),
        sa.Column("base_domain", sa.Text(), nullable=False),
        sa.Column("refresh_policy", sa.Text(), nullable=False, server_default=sa.text("'daily'")),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'enabled'")),
        _jsonb("license_metadata"),
        _created_at(),
        _updated_at(),
        sa.UniqueConstraint("tenant_id", "source_key", name="uq_research_sources_tenant_source_key"),
        sa.CheckConstraint("status in ('enabled', 'paused', 'quarantined')", name="ck_research_sources_status"),
    )

    op.create_table(
        "research_documents",
        _uuid_pk(),
        _tenant_id(),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("research_sources.id", ondelete="CASCADE"), nullable=False),
        sa.Column("document_key", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("normalized_symbol", sa.Text(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("checksum", sa.Text(), nullable=False),
        sa.Column("source_status", sa.Text(), nullable=False, server_default=sa.text("'available'")),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("search_vector", postgresql.TSVECTOR(), nullable=False, server_default=sa.text("''::tsvector")),
        _jsonb("provenance"),
        _jsonb("license_metadata"),
        _created_at(),
        _updated_at(),
        sa.UniqueConstraint("tenant_id", "source_id", "document_key", "checksum", name="uq_research_documents_tenant_version"),
        sa.CheckConstraint("source_status in ('available', 'quarantined', 'removed')", name="ck_research_documents_source_status"),
    )

    op.create_table(
        "paper_execution_policy_ceilings",
        _uuid_pk(),
        _tenant_id(),
        _actor_ref("created_by_actor_id", nullable=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'disabled'")),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        _jsonb("permitted_strategies", default="'[]'::jsonb"),
        _jsonb("permitted_universes", default="'[]'::jsonb"),
        _jsonb("permitted_sides", default="'[]'::jsonb"),
        _jsonb("permitted_order_types", default="'[]'::jsonb"),
        _jsonb("limits"),
        _jsonb("freshness_requirements"),
        sa.Column("self_approval_permitted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        _created_at(),
        _updated_at(),
        sa.CheckConstraint("status in ('disabled', 'enabled', 'revoked')", name="ck_paper_policy_ceilings_status"),
    )

    op.create_table(
        "paper_batch_requests",
        _uuid_pk(),
        _tenant_id(),
        _actor_ref("requested_by_actor_id", nullable=True),
        sa.Column("strategy_key", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'proposed'")),
        _jsonb("orders", default="'[]'::jsonb"),
        _jsonb("context_refs", default="'[]'::jsonb"),
        _jsonb("risk_summary"),
        _created_at(),
        _updated_at(),
        sa.CheckConstraint("status in ('proposed', 'approved', 'rejected', 'executed', 'expired', 'cancelled')", name="ck_paper_batch_requests_status"),
    )

    op.create_table(
        "paper_execution_grants",
        _uuid_pk(),
        _tenant_id(),
        sa.Column("batch_request_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("paper_batch_requests.id", ondelete="CASCADE"), nullable=False),
        sa.Column("policy_ceiling_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("paper_execution_policy_ceilings.id", ondelete="RESTRICT"), nullable=False),
        _actor_ref("approved_by_actor_id", nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'active'")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        _jsonb("scope"),
        _jsonb("reserved_capacity"),
        _jsonb("consumed_capacity"),
        _created_at(),
        _updated_at(),
        sa.CheckConstraint("status in ('active', 'consumed', 'expired', 'revoked')", name="ck_paper_execution_grants_status"),
    )

    op.create_table(
        "paper_ledger_entries",
        _uuid_pk(),
        _tenant_id(),
        sa.Column("grant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("paper_execution_grants.id", ondelete="SET NULL"), nullable=True),
        sa.Column("batch_request_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("paper_batch_requests.id", ondelete="SET NULL"), nullable=True),
        sa.Column("idempotency_key", sa.Text(), nullable=False),
        sa.Column("entry_type", sa.Text(), nullable=False),
        sa.Column("symbol", sa.Text(), nullable=True),
        sa.Column("side", sa.Text(), nullable=True),
        sa.Column("quantity", sa.Numeric(20, 8), nullable=True),
        sa.Column("price", sa.Numeric(20, 8), nullable=True),
        sa.Column("notional", sa.Numeric(20, 8), nullable=True),
        sa.Column("status", sa.Text(), nullable=False),
        _jsonb("decision"),
        _jsonb("fill"),
        _jsonb("exposure_after"),
        _created_at(),
        sa.UniqueConstraint("tenant_id", "idempotency_key", name="uq_paper_ledger_entries_tenant_idempotency_key"),
        sa.CheckConstraint("status in ('accepted', 'rejected', 'simulated', 'cancelled')", name="ck_paper_ledger_entries_status"),
    )

    op.create_table(
        "audit_events",
        _uuid_pk(),
        _tenant_id(),
        _actor_ref(nullable=True),
        sa.Column("request_id", sa.Text(), nullable=True),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("object_type", sa.Text(), nullable=False),
        sa.Column("object_id", postgresql.UUID(as_uuid=True), nullable=True),
        _jsonb("payload"),
        _jsonb("redaction_summary"),
        _created_at(),
    )

    for table_name in TENANT_SCOPED_TABLES:
        _enable_tenant_rls(table_name)

    op.create_index("ix_agent_sessions_tenant_actor_expires", "agent_sessions", ["tenant_id", "actor_identity_id", "absolute_expires_at"])
    op.create_index("ix_fyers_connections_tenant_status", "fyers_connections", ["tenant_id", "status"])
    op.create_index("ix_provider_refresh_jobs_tenant_status", "provider_refresh_jobs", ["tenant_id", "status", "scheduled_for"])
    op.execute(
        "CREATE INDEX ix_provider_snapshots_tenant_provider_account_as_of "
        "ON provider_snapshot_envelopes (tenant_id, provider, account_ref, as_of DESC)"
    )
    op.create_index("ix_broker_account_snapshots_tenant_as_of", "broker_account_snapshots", ["tenant_id", sa.text("as_of DESC")])
    op.execute("CREATE INDEX ix_research_documents_search_vector ON research_documents USING GIN (search_vector)")
    op.create_index("ix_research_documents_tenant_symbol_published", "research_documents", ["tenant_id", "normalized_symbol", sa.text("published_at DESC")])
    op.create_index("ix_paper_batch_requests_tenant_status", "paper_batch_requests", ["tenant_id", "status", "created_at"])
    op.execute(
        "CREATE INDEX ix_paper_execution_grants_tenant_status_expires "
        "ON paper_execution_grants (tenant_id, status, expires_at)"
    )
    op.create_index("ix_paper_ledger_entries_tenant_created_at", "paper_ledger_entries", ["tenant_id", sa.text("created_at DESC")])
    op.execute("CREATE INDEX ix_audit_events_tenant_created_at ON audit_events (tenant_id, created_at DESC)")


def downgrade() -> None:
    op.drop_index("ix_audit_events_tenant_created_at", table_name="audit_events")
    op.drop_index("ix_paper_ledger_entries_tenant_created_at", table_name="paper_ledger_entries")
    op.drop_index("ix_paper_execution_grants_tenant_status_expires", table_name="paper_execution_grants")
    op.drop_index("ix_paper_batch_requests_tenant_status", table_name="paper_batch_requests")
    op.drop_index("ix_research_documents_tenant_symbol_published", table_name="research_documents")
    op.drop_index("ix_research_documents_search_vector", table_name="research_documents")
    op.drop_index("ix_broker_account_snapshots_tenant_as_of", table_name="broker_account_snapshots")
    op.drop_index("ix_provider_snapshots_tenant_provider_account_as_of", table_name="provider_snapshot_envelopes")
    op.drop_index("ix_provider_refresh_jobs_tenant_status", table_name="provider_refresh_jobs")
    op.drop_index("ix_fyers_connections_tenant_status", table_name="fyers_connections")
    op.drop_index("ix_agent_sessions_tenant_actor_expires", table_name="agent_sessions")

    for table_name in reversed(TENANT_SCOPED_TABLES):
        _disable_tenant_rls(table_name)

    for table_name in reversed(
        (
            "audit_events",
            "paper_ledger_entries",
            "paper_execution_grants",
            "paper_batch_requests",
            "paper_execution_policy_ceilings",
            "research_documents",
            "research_sources",
            "broker_account_snapshots",
            "provider_snapshot_envelopes",
            "provider_refresh_jobs",
            "fyers_connections",
            "agent_sessions",
            "actor_identities",
            "tenants",
        )
    ):
        op.drop_table(table_name)
