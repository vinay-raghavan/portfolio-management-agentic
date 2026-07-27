"""Add tenant-scoped provider profile metadata stores."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260727_0009"
down_revision = "20260727_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "provider_configuration_profiles",
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
        sa.Column("profile_id", sa.Text(), nullable=False),
        sa.Column("provider_id", sa.Text(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("source_label", sa.Text(), nullable=False),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.Column(
            "recorded_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "profile_id",
            name="uq_provider_configuration_profiles_tenant_profile",
        ),
    )
    op.create_index(
        "ix_provider_configuration_profiles_tenant_provider_kind",
        "provider_configuration_profiles",
        ["tenant_id", "provider_id", "kind"],
    )
    op.create_index(
        "ix_provider_configuration_profiles_tenant_updated_at",
        "provider_configuration_profiles",
        ["tenant_id", "updated_at"],
    )

    op.create_table(
        "provider_import_jobs",
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
        sa.Column("job_id", sa.Text(), nullable=False),
        sa.Column("profile_id", sa.Text(), nullable=False),
        sa.Column("provider_id", sa.Text(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("source_label", sa.Text(), nullable=False),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("completed_at", sa.Text(), nullable=False),
        sa.Column(
            "recorded_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "status in ('completed', 'needs_attention', 'skipped')",
            name="ck_provider_import_jobs_status",
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "job_id",
            name="uq_provider_import_jobs_tenant_job",
        ),
    )
    op.create_index(
        "ix_provider_import_jobs_tenant_provider_completed",
        "provider_import_jobs",
        ["tenant_id", "provider_id", "completed_at"],
    )
    op.create_index(
        "ix_provider_import_jobs_tenant_status_completed",
        "provider_import_jobs",
        ["tenant_id", "status", "completed_at"],
    )
    _enable_tenant_rls("provider_configuration_profiles")
    _enable_tenant_rls("provider_import_jobs")


def downgrade() -> None:
    _disable_tenant_rls("provider_import_jobs")
    _disable_tenant_rls("provider_configuration_profiles")
    op.drop_index(
        "ix_provider_import_jobs_tenant_status_completed",
        table_name="provider_import_jobs",
    )
    op.drop_index(
        "ix_provider_import_jobs_tenant_provider_completed",
        table_name="provider_import_jobs",
    )
    op.drop_table("provider_import_jobs")
    op.drop_index(
        "ix_provider_configuration_profiles_tenant_updated_at",
        table_name="provider_configuration_profiles",
    )
    op.drop_index(
        "ix_provider_configuration_profiles_tenant_provider_kind",
        table_name="provider_configuration_profiles",
    )
    op.drop_table("provider_configuration_profiles")


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
