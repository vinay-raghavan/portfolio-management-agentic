from __future__ import annotations

from scripts.process_paper_execution_queue import parse_tenant_ids


def test_worker_cli_parses_unique_comma_separated_tenant_ids() -> None:
    assert parse_tenant_ids(" tenant-a, tenant-b,,tenant-a ") == (
        "tenant-a",
        "tenant-b",
    )


def test_worker_cli_falls_back_to_single_tenant_id() -> None:
    assert parse_tenant_ids("", fallback_tenant_id=" tenant-single ") == (
        "tenant-single",
    )

