from __future__ import annotations

import re
from pathlib import Path


REQUIRED_TABLES = {
    "tenants",
    "actor_identities",
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
}


TENANT_SCOPED_TABLES = REQUIRED_TABLES - {"tenants", "actor_identities"}


def test_postgres_env_defaults_are_documented_for_production_like_testing() -> None:
    env_example = Path(".env.example").read_text()

    assert "PORTFOLIO_DATABASE_URL=postgresql+psycopg://portfolio:portfolio-dev-password@localhost:5432/portfolio_agentic" in env_example
    assert "POSTGRES_USER=portfolio" in env_example
    assert "POSTGRES_PASSWORD=portfolio-dev-password" in env_example
    assert "POSTGRES_DB=portfolio_agentic" in env_example
    assert "REDIS_URL=redis://redis:6379/0" in env_example


def test_compose_has_postgres_redis_and_migration_job() -> None:
    compose = Path("docker-compose.yml").read_text()

    assert "postgres:" in compose
    assert "image: postgres:${POSTGRES_IMAGE_TAG:-16-alpine}" in compose
    assert "POSTGRES_USER: ${POSTGRES_USER:-portfolio}" in compose
    assert "POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-portfolio-dev-password}" in compose
    assert "POSTGRES_DB: ${POSTGRES_DB:-portfolio_agentic}" in compose
    assert "pg_isready -U $${POSTGRES_USER:-portfolio} -d $${POSTGRES_DB:-portfolio_agentic}" in compose
    assert "postgres-data:/var/lib/postgresql/data" in compose
    assert "redis:" in compose
    assert "image: redis:${REDIS_IMAGE_TAG:-7-alpine}" in compose
    assert "migrations:" in compose
    assert "uv run alembic -c infra/db/alembic.ini upgrade head" in compose
    assert "PORTFOLIO_DATABASE_URL: ${PORTFOLIO_DATABASE_URL:-postgresql+psycopg://portfolio:portfolio-dev-password@postgres:5432/portfolio_agentic}" in compose
    assert "REDIS_URL: ${REDIS_URL:-redis://redis:6379/0}" in compose
    assert "condition: service_healthy" in compose
    assert "condition: service_completed_successfully" in compose
    assert "postgres-data:" in compose
    assert "redis-data:" in compose


def test_alembic_config_and_environment_are_env_driven() -> None:
    alembic_ini = Path("infra/db/alembic.ini").read_text()
    env_py = Path("infra/db/alembic/env.py").read_text()

    assert "script_location = %(here)s/alembic" in alembic_ini
    assert "file_template = %%(year)d%%(month).2d%%(day).2d_%%(hour).2d%%(minute).2d_%%(rev)s_%%(slug)s" in alembic_ini
    assert "PORTFOLIO_DATABASE_URL" in env_py
    assert "DATABASE_URL" in env_py
    assert "pool.NullPool" in env_py
    assert "context.run_migrations()" in env_py


def test_initial_postgres_migration_defines_platform_tables_with_tenant_isolation() -> None:
    migration = Path("infra/db/alembic/versions/20260725_0001_initial_platform_schema.py").read_text()

    assert 'revision = "20260725_0001"' in migration
    assert "down_revision = None" in migration
    assert "CREATE EXTENSION IF NOT EXISTS pgcrypto" in migration

    for table in REQUIRED_TABLES:
        assert re.search(rf'op\.create_table\(\s*"{table}"', migration)

    for table in TENANT_SCOPED_TABLES:
        match = re.search(rf'op\.create_table\(\s*"{table}"', migration)
        assert match is not None
        start = match.start()
        next_table = migration.find("op.create_table(", start + 1)
        table_definition = migration[start : next_table if next_table != -1 else len(migration)]
        assert 'sa.Column("tenant_id"' in table_definition or "_tenant_id()" in table_definition
        assert f'"{table}"' in migration[migration.index("TENANT_SCOPED_TABLES") : migration.index("def _uuid_pk")]

    assert "ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY" in migration
    assert "CREATE POLICY tenant_isolation_{table_name}" in migration
    assert "for table_name in TENANT_SCOPED_TABLES" in migration

    assert "CREATE INDEX ix_research_documents_search_vector" in migration
    assert "CREATE INDEX ix_provider_snapshots_tenant_provider_account_as_of" in migration
    assert "CREATE INDEX ix_audit_events_tenant_created_at" in migration
    assert "CREATE INDEX ix_paper_execution_grants_tenant_status_expires" in migration
    assert "tsvector" in migration
    assert "jsonb" in migration.lower()
