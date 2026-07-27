from __future__ import annotations

import ast
import re
from pathlib import Path

from portfolio_domain import (
    DatabaseBackend,
    DatabaseRuntimeProfile,
    evaluate_database_runtime_readiness,
    load_database_runtime_profile,
)


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


def _literal_assignment(module: ast.Module, name: str) -> str | tuple[str, ...] | None:
    for node in module.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
            continue
        value = ast.literal_eval(node.value)
        if value is None or isinstance(value, str):
            return value
        if isinstance(value, tuple) and all(isinstance(item, str) for item in value):
            return value
    raise AssertionError(f"{name} assignment not found")


def _revision_modules() -> dict[str, tuple[Path, ast.Module]]:
    modules: dict[str, tuple[Path, ast.Module]] = {}
    for path in sorted(Path("infra/db/alembic/versions").glob("*.py")):
        module = ast.parse(path.read_text())
        revision = _literal_assignment(module, "revision")
        assert isinstance(revision, str), f"{path} must define string revision"
        assert revision not in modules, f"duplicate Alembic revision: {revision}"
        modules[revision] = (path, module)
    return modules


def test_postgres_env_defaults_are_documented_for_production_like_testing() -> None:
    env_example = Path(".env.example").read_text()

    assert "PORTFOLIO_STORAGE_BACKEND=postgres" in env_example
    assert "PORTFOLIO_DATABASE_URL=postgresql+psycopg://portfolio:portfolio-dev-password@localhost:5432/portfolio_agentic" in env_example
    assert "PORTFOLIO_TENANT_IDS=" in env_example
    assert "PORTFOLIO_TENANT_ID=11111111-1111-1111-1111-111111111111" in env_example
    assert "PAPER_EXECUTION_WORKER_ID=paper-execution-worker-1" in env_example
    assert "PAPER_EXECUTION_WORKER_MAX_ITEMS=100" in env_example
    assert "PAPER_EXECUTION_WORKER_IDLE_SLEEP_SECONDS=5" in env_example
    assert "PAPER_EXECUTION_WORKER_SCHEDULE_BACKOFF_SECONDS=30" in env_example
    assert "POSTGRES_USER=portfolio" in env_example
    assert "POSTGRES_PASSWORD=portfolio-dev-password" in env_example
    assert "POSTGRES_DB=portfolio_agentic" in env_example
    assert "REDIS_URL=redis://redis:6379/0" in env_example


def test_compose_has_postgres_redis_and_migration_job() -> None:
    compose = Path("docker-compose.yml").read_text()
    agent_dockerfile = Path("apps/agent-service/Dockerfile").read_text()

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
    assert "paper-execution-worker:" in compose
    assert "uv run python ../../scripts/process_paper_execution_queue.py --daemon" in compose
    assert "PORTFOLIO_TENANT_IDS: ${PORTFOLIO_TENANT_IDS:-}" in compose
    assert "PORTFOLIO_TENANT_ID: ${PORTFOLIO_TENANT_ID:-11111111-1111-1111-1111-111111111111}" in compose
    assert compose.count(
        "PORTFOLIO_TENANT_ID: ${PORTFOLIO_TENANT_ID:-11111111-1111-1111-1111-111111111111}"
    ) >= 3
    assert "PAPER_EXECUTION_WORKER_ID: ${PAPER_EXECUTION_WORKER_ID:-paper-execution-worker-1}" in compose
    assert "PAPER_EXECUTION_WORKER_SCHEDULE_BACKOFF_SECONDS: ${PAPER_EXECUTION_WORKER_SCHEDULE_BACKOFF_SECONDS:-30}" in compose
    assert "uv run alembic -c infra/db/alembic.ini upgrade head" in compose
    assert "COPY ./scripts/process_paper_execution_queue.py ./scripts/process_paper_execution_queue.py" in agent_dockerfile
    assert "PORTFOLIO_STORAGE_BACKEND: ${PORTFOLIO_STORAGE_BACKEND:-postgres}" in compose
    assert "PORTFOLIO_DATABASE_URL: ${PORTFOLIO_DATABASE_URL:-postgresql+psycopg://portfolio:portfolio-dev-password@postgres:5432/portfolio_agentic}" in compose
    assert "REDIS_URL: ${REDIS_URL:-redis://redis:6379/0}" in compose
    assert "condition: service_healthy" in compose
    assert "condition: service_completed_successfully" in compose
    assert "postgres-data:" in compose
    assert "redis-data:" in compose

    pyproject = Path("apps/agent-service/pyproject.toml").read_text()
    assert '"redis>=6.2,<9"' in pyproject


def test_alembic_config_and_environment_are_env_driven() -> None:
    alembic_ini = Path("infra/db/alembic.ini").read_text()
    env_py = Path("infra/db/alembic/env.py").read_text()

    assert "script_location = %(here)s/alembic" in alembic_ini
    assert "file_template = %%(year)d%%(month).2d%%(day).2d_%%(hour).2d%%(minute).2d_%%(rev)s_%%(slug)s" in alembic_ini
    assert "PORTFOLIO_DATABASE_URL" in env_py
    assert "DATABASE_URL" in env_py
    assert "pool.NullPool" in env_py
    assert "context.run_migrations()" in env_py


def test_alembic_revision_chain_has_single_head_and_no_orphans() -> None:
    revisions = _revision_modules()
    children_by_parent: dict[str, set[str]] = {revision: set() for revision in revisions}
    heads = set(revisions)
    roots = set()

    for revision, (path, module) in revisions.items():
        down_revision = _literal_assignment(module, "down_revision")
        parent_revisions = (
            ()
            if down_revision is None
            else (down_revision,)
            if isinstance(down_revision, str)
            else down_revision
        )
        if not parent_revisions:
            roots.add(revision)
        for parent in parent_revisions:
            assert parent in revisions, f"{path} references missing down_revision {parent}"
            children_by_parent[parent].add(revision)
            heads.discard(parent)

    assert roots == {"20260725_0001"}
    assert heads == {"20260727_0007"}
    assert all(
        len(children) <= 1 for children in children_by_parent.values()
    ), "linear production migration chain expected until an explicit merge migration exists"


def test_alembic_revisions_have_reversible_upgrade_contracts() -> None:
    for path, module in _revision_modules().values():
        functions = {
            node.name
            for node in module.body
            if isinstance(node, ast.FunctionDef)
        }
        content = path.read_text()

        assert {"upgrade", "downgrade"}.issubset(functions), f"{path} must be reversible"
        assert "from alembic import op" in content
        assert "pass" not in content


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


def test_database_runtime_profile_uses_postgres_as_production_like_backend() -> None:
    profile = load_database_runtime_profile(
        {
            "PORTFOLIO_DATABASE_URL": "postgresql+psycopg://portfolio:super-secret@db.internal:5432/portfolio_agentic",
            "REDIS_URL": "redis://:redis-secret@redis.internal:6379/0",
            "PAPER_LEDGER_DB_PATH": "/data/paper-ledger.db",
            "MARKET_DATA_DB_PATH": "/data/market-data.db",
            "PROVIDER_CONFIG_DB_PATH": "/data/provider-config.db",
        }
    )
    readiness = evaluate_database_runtime_readiness(
        profile,
        require_production_like=True,
    )

    assert isinstance(profile, DatabaseRuntimeProfile)
    assert profile.backend == DatabaseBackend.POSTGRES
    assert profile.production_like is True
    assert profile.migrations_required is True
    assert profile.alembic_config_path == "infra/db/alembic.ini"
    assert profile.redacted_database_url == (
        "postgresql+psycopg://portfolio:***@db.internal:5432/portfolio_agentic"
    )
    assert profile.redacted_redis_url == "redis://:***@redis.internal:6379/0"
    assert profile.sqlite_paths == {
        "paper_ledger": "/data/paper-ledger.db",
        "market_data": "/data/market-data.db",
        "provider_config": "/data/provider-config.db",
    }
    assert readiness.ready is True
    assert readiness.blocking_reasons == ()
    assert "super-secret" not in profile.to_dict().values()
    assert "redis-secret" not in profile.to_dict().values()


def test_database_runtime_profile_keeps_sqlite_as_explicit_offline_backend() -> None:
    profile = load_database_runtime_profile(
        {
            "PAPER_LEDGER_DB_PATH": "data/paper-ledger.db",
            "MARKET_DATA_DB_PATH": "data/market-data.db",
            "PROVIDER_CONFIG_DB_PATH": "data/provider-config.db",
        }
    )
    readiness = evaluate_database_runtime_readiness(
        profile,
        require_production_like=True,
    )

    assert profile.backend == DatabaseBackend.SQLITE
    assert profile.production_like is False
    assert profile.migrations_required is False
    assert profile.database_url is None
    assert profile.redacted_database_url is None
    assert profile.sqlite_paths == {
        "paper_ledger": "data/paper-ledger.db",
        "market_data": "data/market-data.db",
        "provider_config": "data/provider-config.db",
    }
    assert readiness.ready is False
    assert readiness.blocking_reasons == ("postgres_required_for_production_like_testing",)


def test_database_runtime_profile_fails_closed_on_missing_postgres_url() -> None:
    profile = load_database_runtime_profile({"PORTFOLIO_STORAGE_BACKEND": "postgres"})
    readiness = evaluate_database_runtime_readiness(
        profile,
        require_production_like=True,
    )

    assert profile.backend == DatabaseBackend.POSTGRES
    assert profile.production_like is True
    assert profile.migrations_required is True
    assert readiness.ready is False
    assert readiness.blocking_reasons == ("postgres_database_url_missing",)
