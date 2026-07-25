from __future__ import annotations

from pathlib import Path

from portfolio_capabilities import (
    EXPECTED_CAPABILITY_NAMES,
    CapabilityManifest,
    load_capability_manifests,
)
from portfolio_mcp.tools import EXPOSED_TOOL_NAMES
from portfolio_policy import ActionTier, classify_tool


CAPABILITY_ROOT = Path("capabilities")

TIER_RANK = {
    ActionTier.READ_ONLY: 1,
    ActionTier.DRAFT_ONLY: 2,
    ActionTier.APPROVAL_REQUIRED: 3,
    ActionTier.FORBIDDEN: 4,
}


def test_expected_capability_manifests_exist() -> None:
    manifests = load_capability_manifests()

    assert set(manifests) == EXPECTED_CAPABILITY_NAMES
    for name, manifest in manifests.items():
        assert isinstance(manifest, CapabilityManifest)
        assert manifest.name == name
        assert manifest.version
        assert manifest.description
        assert manifest.allowed_tools == tuple(sorted(set(manifest.allowed_tools)))
        assert manifest.context_sources
        assert manifest.response_schema
        assert manifest.token_budget.input_tokens > 0
        assert manifest.token_budget.output_tokens > 0
        assert manifest.token_budget.tool_calls >= 0
        assert manifest.eval_cases


def test_capability_skills_match_manifest_metadata() -> None:
    manifests = load_capability_manifests()

    for manifest in manifests.values():
        skill_path = CAPABILITY_ROOT / manifest.name / "SKILL.md"
        skill_text = skill_path.read_text()

        assert skill_text.startswith("---\n")
        assert f"name: {manifest.name}" in skill_text
        assert manifest.description in skill_text
        assert "## Allowed tools" in skill_text
        assert "## Context contract" in skill_text
        assert "## Response contract" in skill_text
        for tool_name in manifest.allowed_tools:
            assert f"`{tool_name}`" in skill_text


def test_manifest_allowed_tools_are_exposed_and_policy_classified() -> None:
    for manifest in load_capability_manifests().values():
        max_tier = ActionTier(manifest.max_action_tier)
        for tool_name in manifest.allowed_tools:
            assert tool_name in EXPOSED_TOOL_NAMES
            tier = classify_tool(tool_name)
            assert tier != ActionTier.FORBIDDEN
            assert TIER_RANK[tier] <= TIER_RANK[max_tier]


def test_read_only_capabilities_cannot_include_draft_or_approval_tools() -> None:
    read_only_capabilities = {
        "research",
        "technical_analysis",
        "fyers_data",
        "provider_readiness",
        "risk_review",
        "reporting",
    }

    manifests = load_capability_manifests()
    for name in read_only_capabilities:
        manifest = manifests[name]
        assert manifest.max_action_tier == ActionTier.READ_ONLY.value
        for tool_name in manifest.allowed_tools:
            assert classify_tool(tool_name) == ActionTier.READ_ONLY


def test_paper_execution_manifest_excludes_approval_and_fill_tools() -> None:
    manifest = load_capability_manifests()["paper_proposal_execution"]

    assert manifest.max_action_tier == ActionTier.DRAFT_ONLY.value
    assert "approve_paper_order_simulation" not in manifest.allowed_tools
    assert "simulate_approved_paper_fill" not in manifest.allowed_tools
    assert "get_approval_queue" in manifest.allowed_tools
    assert "get_audit_events" in manifest.allowed_tools


def test_safety_manifest_is_toolless_and_names_forbidden_tools() -> None:
    manifest = load_capability_manifests()["safety"]

    assert manifest.allowed_tools == ()
    assert manifest.max_action_tier == ActionTier.FORBIDDEN.value
    assert set(manifest.forbidden_tools) >= {
        "place_live_order",
        "enable_live_strategy",
        "get_broker_trading_token",
    }


def test_architecture_docs_list_every_capability_manifest() -> None:
    docs = Path("docs/architecture/capability-manifests.md").read_text()

    for capability_name in EXPECTED_CAPABILITY_NAMES:
        assert f"`{capability_name}`" in docs
