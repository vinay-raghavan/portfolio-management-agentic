from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


EXPECTED_CAPABILITY_NAMES = {
    "research",
    "technical_analysis",
    "fyers_data",
    "pre_market_briefing",
    "provider_readiness",
    "risk_review",
    "paper_proposal_execution",
    "reporting",
    "safety",
}


@dataclass(frozen=True)
class TokenBudget:
    input_tokens: int
    output_tokens: int
    tool_calls: int

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> TokenBudget:
        return cls(
            input_tokens=int(payload["input_tokens"]),
            output_tokens=int(payload["output_tokens"]),
            tool_calls=int(payload["tool_calls"]),
        )


@dataclass(frozen=True)
class CapabilityManifest:
    name: str
    version: str
    description: str
    max_action_tier: str
    allowed_tools: tuple[str, ...]
    context_sources: tuple[str, ...]
    response_schema: str
    token_budget: TokenBudget
    eval_cases: tuple[str, ...]
    forbidden_tools: tuple[str, ...]

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> CapabilityManifest:
        return cls(
            name=str(payload["name"]),
            version=str(payload["version"]),
            description=str(payload["description"]),
            max_action_tier=str(payload["max_action_tier"]),
            allowed_tools=tuple(sorted(set(payload.get("allowed_tools", [])))),
            context_sources=tuple(payload.get("context_sources", [])),
            response_schema=str(payload["response_schema"]),
            token_budget=TokenBudget.from_payload(payload["token_budget"]),
            eval_cases=tuple(payload.get("eval_cases", [])),
            forbidden_tools=tuple(payload.get("forbidden_tools", [])),
        )


def load_capability_manifests(
    root: Path | None = None,
) -> dict[str, CapabilityManifest]:
    """Load repository capability manifests.

    Manifests are intentionally static JSON so routing, skills, CI, and future
    MCP registration can share one auditable capability contract.
    """
    manifest_root = root or _repo_root() / "capabilities"
    manifests: dict[str, CapabilityManifest] = {}
    for manifest_path in sorted(manifest_root.glob("*/manifest.json")):
        payload = json.loads(manifest_path.read_text())
        manifest = CapabilityManifest.from_payload(payload)
        manifests[manifest.name] = manifest
    return manifests


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]
