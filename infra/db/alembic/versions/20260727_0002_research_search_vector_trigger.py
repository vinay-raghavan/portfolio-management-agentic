"""Maintain research document full-text search fields."""

from __future__ import annotations

from alembic import op


revision = "20260727_0002"
down_revision = "20260725_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION research_documents_search_vector_refresh()
        RETURNS trigger AS $$
        BEGIN
            NEW.search_vector := to_tsvector('english',
                coalesce(NEW.title, '') || ' ' ||
                coalesce(NEW.normalized_symbol, '') || ' ' ||
                coalesce(NEW.content, '')
            );
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER research_documents_search_vector_refresh
        BEFORE INSERT OR UPDATE
        ON research_documents
        FOR EACH ROW
        EXECUTE FUNCTION research_documents_search_vector_refresh()
        """
    )
    op.execute(
        """
        UPDATE research_documents
        SET search_vector = to_tsvector('english',
            coalesce(title, '') || ' ' ||
            coalesce(normalized_symbol, '') || ' ' ||
            coalesce(content, '')
        )
        """
    )
    op.create_index(
        "ix_research_documents_tenant_status_published",
        "research_documents",
        ["tenant_id", "source_status", "published_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_research_documents_tenant_status_published",
        table_name="research_documents",
    )
    op.execute(
        "DROP TRIGGER IF EXISTS research_documents_search_vector_refresh ON research_documents"
    )
    op.execute("DROP FUNCTION IF EXISTS research_documents_search_vector_refresh()")
